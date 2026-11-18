from pathlib import Path

from django import forms

from .models import (
    ApplicationDocument,
    ApplicationQuotation,
    GuaranteeApplication,
    required_document_kinds,
    required_quotation_count,
)

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def validate_upload(upload):
    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise forms.ValidationError("Choose a PDF, JPG, or PNG file.")
    if upload.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError("Files must be 5 MB or smaller.")
    header = upload.read(8)
    upload.seek(0)
    signatures = {
        ".pdf": header.startswith(b"%PDF-"),
        ".jpg": header.startswith(b"\xff\xd8\xff"),
        ".jpeg": header.startswith(b"\xff\xd8\xff"),
        ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    if not signatures[extension]:
        raise forms.ValidationError("The file contents do not match its file type.")
    return upload


class GuaranteeApplicationForm(forms.ModelForm):
    class Meta:
        model = GuaranteeApplication
        fields = (
            "program",
            "assistance_type",
            "patient_name",
            "hospital",
            "city",
            "diagnosis",
            "amount_requested",
        )
        widgets = {
            "amount_requested": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def clean_amount_requested(self):
        amount = self.cleaned_data["amount_requested"]
        if amount <= 0:
            raise forms.ValidationError("Enter an amount greater than zero.")
        return amount

    def clean_patient_name(self):
        return self.cleaned_data["patient_name"].strip()


class DocumentUploadForm(forms.Form):
    file = forms.FileField(validators=[validate_upload])


class ApplicationQuotationForm(forms.ModelForm):
    class Meta:
        model = ApplicationQuotation
        fields = ("supplier", "items", "status", "amount", "file")
        widgets = {
            "amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        if cleaned_data.get("status") == ApplicationQuotation.Status.RECEIVED:
            if amount is None or amount <= 0:
                self.add_error("amount", "Enter the received quotation amount.")
        elif amount is not None and amount < 0:
            self.add_error("amount", "The amount cannot be negative.")
        return cleaned_data

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        return validate_upload(upload) if upload else upload


class DocumentReviewForm(forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ("review_status", "review_note")

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("review_status") == ApplicationDocument.ReviewStatus.REJECTED
            and not cleaned_data.get("review_note", "").strip()
        ):
            self.add_error("review_note", "Give a reason when rejecting a document.")
        return cleaned_data


class ApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = GuaranteeApplication
        fields = ("status", "admin_note")

    def __init__(self, *args, **kwargs):
        self.application = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = (
            (GuaranteeApplication.Status.UNDER_REVIEW, "Under review"),
            (GuaranteeApplication.Status.APPROVED, "Approved"),
            (GuaranteeApplication.Status.REJECTED, "Rejected"),
        )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        note = cleaned_data.get("admin_note", "").strip()

        if status == GuaranteeApplication.Status.REJECTED and not note:
            self.add_error("admin_note", "Add a reason before rejecting an application.")

        if status == GuaranteeApplication.Status.APPROVED and self.application:
            required_kinds = required_document_kinds(self.application.assistance_type)
            documents = {
                document.kind: document
                for document in self.application.documents.all()
            }
            missing = [
                kind for kind in required_kinds
                if kind not in documents
                or documents[kind].review_status != ApplicationDocument.ReviewStatus.ACCEPTED
            ]
            unreviewed = [
                document for document in documents.values()
                if document.review_status != ApplicationDocument.ReviewStatus.ACCEPTED
            ]
            if missing or unreviewed:
                self.add_error(
                    "status",
                    "Accept every uploaded document and all required documents before approval.",
                )

            required_quotes = required_quotation_count(self.application.assistance_type)
            received_quotes = self.application.quotations.filter(
                status=ApplicationQuotation.Status.RECEIVED
            ).count()
            if received_quotes < required_quotes:
                self.add_error(
                    "status",
                    f"Record at least {required_quotes} received quotation(s) before approval.",
                )
        return cleaned_data
