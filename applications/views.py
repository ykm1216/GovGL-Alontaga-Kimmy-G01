from functools import wraps
from pathlib import PurePosixPath

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import CustomUser

from .forms import (
    ApplicationQuotationForm,
    ApplicationReviewForm,
    DocumentReviewForm,
    DocumentUploadForm,
    GuaranteeApplicationForm,
)
from .models import (
    ApplicationDocument,
    ApplicationQuotation,
    GuaranteeApplication,
    required_document_kinds,
    required_quotation_count,
)


def role_required(role):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, "You do not have access to that page.")
                return redirect("dashboard")
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


patient_required = role_required(CustomUser.Role.PATIENT)
admin_required = role_required(CustomUser.Role.ADMIN)


def owned_application(user, application_id):
    return get_object_or_404(GuaranteeApplication, pk=application_id, user=user)


def can_download(user, application):
    """Owners can always download their files. Admins can only download files
    from applications that were submitted, never from a patient's draft."""
    if application.user_id == user.pk:
        return True
    return (
        user.role == CustomUser.Role.ADMIN
        and application.status != GuaranteeApplication.Status.DRAFT
    )


@patient_required
def application_list_view(request):
    applications = GuaranteeApplication.objects.filter(user=request.user)
    return render(request, "applications/list.html", {"applications": applications})


@patient_required
def application_create_view(request):
    if request.method == "POST":
        form = GuaranteeApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            messages.success(request, "Your application draft was created.")
            return redirect("application_detail", application_id=application.pk)
    else:
        form = GuaranteeApplicationForm()

    return render(request, "applications/form.html", {"form": form, "is_new": True})


@patient_required
def application_detail_view(request, application_id):
    application = owned_application(request.user, application_id)
    required_kinds = required_document_kinds(application.assistance_type)
    documents = {document.kind: document for document in application.documents.all()}
    checklist = [
        {
            "kind": kind,
            "label": ApplicationDocument.Kind(kind).label,
            "required": kind in required_kinds,
            "document": documents.get(kind),
        }
        for kind, _ in ApplicationDocument.Kind.choices
    ]
    context = {
        "application": application,
        "checklist": checklist,
        "document_upload_form": DocumentUploadForm(),
        "quotation_form": ApplicationQuotationForm(),
        "required_quotes": required_quotation_count(application.assistance_type),
        "received_quotes": application.quotations.filter(
            status=ApplicationQuotation.Status.RECEIVED
        ).count(),
    }
    return render(request, "applications/detail.html", context)


@login_required
def document_download_view(request, document_id):
    document = get_object_or_404(
        ApplicationDocument.objects.select_related("application"),
        pk=document_id,
    )
    if not can_download(request.user, document.application):
        raise Http404
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=PurePosixPath(document.file.name).name,
    )


@login_required
def quotation_download_view(request, quotation_id):
    quotation = get_object_or_404(
        ApplicationQuotation.objects.select_related("application"),
        pk=quotation_id,
    )
    if not can_download(request.user, quotation.application):
        raise Http404
    if not quotation.file:
        raise Http404
    return FileResponse(
        quotation.file.open("rb"),
        as_attachment=True,
        filename=PurePosixPath(quotation.file.name).name,
    )


@patient_required
def application_edit_view(request, application_id):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "Only draft applications can be edited.")
        return redirect("application_detail", application_id=application.pk)

    if request.method == "POST":
        form = GuaranteeApplicationForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, "Your application draft was updated.")
            return redirect("application_detail", application_id=application.pk)
    else:
        form = GuaranteeApplicationForm(instance=application)

    return render(
        request,
        "applications/form.html",
        {"form": form, "application": application, "is_new": False},
    )


@require_POST
@patient_required
def application_delete_view(request, application_id):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "Only draft applications can be deleted.")
        return redirect("application_detail", application_id=application.pk)

    for document in application.documents.all():
        document.file.delete(save=False)
    for quotation in application.quotations.all():
        if quotation.file:
            quotation.file.delete(save=False)
    application.delete()
    messages.success(request, "The draft application was deleted.")
    return redirect("application_list")


@require_POST
@patient_required
def document_upload_view(request, application_id, kind):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "Documents can only be changed on draft applications.")
        return redirect("application_detail", application_id=application.pk)
    if kind not in ApplicationDocument.Kind.values:
        raise Http404("Unknown document type.")

    form = DocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        document = ApplicationDocument.objects.filter(
            application=application,
            kind=kind,
        ).first()
        if document:
            document.file.delete(save=False)
            document.file = form.cleaned_data["file"]
        else:
            document = ApplicationDocument(
                application=application,
                kind=kind,
                file=form.cleaned_data["file"],
            )
        document.review_status = ApplicationDocument.ReviewStatus.PENDING
        document.review_note = ""
        document.reviewed_by = None
        document.save()
        messages.success(request, "The document was uploaded.")
    else:
        for error in form.errors.get("file", []):
            messages.error(request, error)
    return redirect("application_detail", application_id=application.pk)


@require_POST
@patient_required
def document_delete_view(request, application_id, document_id):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "Documents can only be changed on draft applications.")
        return redirect("application_detail", application_id=application.pk)
    document = get_object_or_404(ApplicationDocument, pk=document_id, application=application)
    document.file.delete(save=False)
    document.delete()
    messages.success(request, "The document was removed.")
    return redirect("application_detail", application_id=application.pk)


@require_POST
@patient_required
def quotation_create_view(request, application_id):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "Quotations can only be changed on draft applications.")
        return redirect("application_detail", application_id=application.pk)

    form = ApplicationQuotationForm(request.POST, request.FILES)
    if form.is_valid():
        quotation = form.save(commit=False)
        quotation.application = application
        quotation.save()
        messages.success(request, "The quotation was recorded.")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect("application_detail", application_id=application.pk)


@require_POST
@patient_required
def quotation_delete_view(request, application_id, quotation_id):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "Quotations can only be changed on draft applications.")
        return redirect("application_detail", application_id=application.pk)
    quotation = get_object_or_404(
        ApplicationQuotation,
        pk=quotation_id,
        application=application,
    )
    if quotation.file:
        quotation.file.delete(save=False)
    quotation.delete()
    messages.success(request, "The quotation was removed.")
    return redirect("application_detail", application_id=application.pk)


@require_POST
@patient_required
def application_submit_view(request, application_id):
    application = owned_application(request.user, application_id)
    if application.status != GuaranteeApplication.Status.DRAFT:
        messages.error(request, "This application has already been submitted.")
        return redirect("application_detail", application_id=application.pk)

    uploaded_kinds = set(application.documents.values_list("kind", flat=True))
    missing = [
        ApplicationDocument.Kind(kind).label
        for kind in required_document_kinds(application.assistance_type)
        if kind not in uploaded_kinds
    ]
    required_quotes = required_quotation_count(application.assistance_type)
    received_quotes = application.quotations.filter(
        status=ApplicationQuotation.Status.RECEIVED
    ).count()

    if missing or received_quotes < required_quotes:
        if missing:
            messages.error(request, "Upload required documents: " + ", ".join(missing) + ".")
        if received_quotes < required_quotes:
            messages.error(
                request,
                f"Record at least {required_quotes} received quotation(s); "
                f"{received_quotes} recorded.",
            )
        return redirect("application_detail", application_id=application.pk)

    application.status = GuaranteeApplication.Status.SUBMITTED
    application.submitted_at = timezone.now()
    application.save(update_fields=("status", "submitted_at", "updated_at"))
    messages.success(request, "Your application was submitted for review.")
    return redirect("application_detail", application_id=application.pk)


@admin_required
def review_list_view(request):
    applications = GuaranteeApplication.objects.filter(
        status__in=(
            GuaranteeApplication.Status.SUBMITTED,
            GuaranteeApplication.Status.UNDER_REVIEW,
        )
    ).select_related("user")
    return render(request, "applications/review_list.html", {"applications": applications})


@admin_required
def review_detail_view(request, application_id):
    application = get_object_or_404(GuaranteeApplication, pk=application_id)
    if application.status not in (
        GuaranteeApplication.Status.SUBMITTED,
        GuaranteeApplication.Status.UNDER_REVIEW,
    ):
        messages.error(request, "Only submitted applications can be reviewed.")
        return redirect("review_list")

    review_form = ApplicationReviewForm(instance=application)
    checklist = [
        {
            "document": document,
            "form": DocumentReviewForm(instance=document),
            "required": document.kind in required_document_kinds(application.assistance_type),
        }
        for document in application.documents.all()
    ]
    return render(
        request,
        "applications/review_detail.html",
        {
            "application": application,
            "checklist": checklist,
            "review_form": review_form,
        },
    )


@require_POST
@admin_required
def document_review_view(request, application_id, document_id):
    application = get_object_or_404(GuaranteeApplication, pk=application_id)
    if application.status not in (
        GuaranteeApplication.Status.SUBMITTED,
        GuaranteeApplication.Status.UNDER_REVIEW,
    ):
        messages.error(request, "This application is no longer open for review.")
        return redirect("review_list")

    document = get_object_or_404(ApplicationDocument, pk=document_id, application=application)
    form = DocumentReviewForm(request.POST, instance=document)
    if form.is_valid():
        reviewed_document = form.save(commit=False)
        reviewed_document.reviewed_by = request.user
        reviewed_document.save()
        messages.success(request, "The document review was saved.")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect("review_detail", application_id=application.pk)


@require_POST
@admin_required
def application_review_view(request, application_id):
    application = get_object_or_404(GuaranteeApplication, pk=application_id)
    if application.status not in (
        GuaranteeApplication.Status.SUBMITTED,
        GuaranteeApplication.Status.UNDER_REVIEW,
    ):
        messages.error(request, "This application is no longer open for review.")
        return redirect("review_list")

    form = ApplicationReviewForm(request.POST, instance=application)
    if form.is_valid():
        reviewed_application = form.save(commit=False)
        reviewed_application.reviewed_by = request.user
        reviewed_application.reviewed_at = timezone.now()
        reviewed_application.save()
        messages.success(request, "The application decision was saved.")
        if reviewed_application.status in (
            GuaranteeApplication.Status.APPROVED,
            GuaranteeApplication.Status.REJECTED,
        ):
            return redirect("review_list")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
    return redirect("review_detail", application_id=application.pk)
