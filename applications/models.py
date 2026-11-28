import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def _random_upload_path(folder, filename):
    """Store uploads under a random name so personal details in the original
    filename are never part of the storage path."""
    extension = Path(filename).suffix.lower()
    return f"{folder}/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}"


def document_upload_path(instance, filename):
    return _random_upload_path("applications", filename)


def quotation_upload_path(instance, filename):
    return _random_upload_path("quotations", filename)


class GuaranteeApplication(models.Model):
    class Program(models.TextChoices):
        PCSO = "PCSO", "PCSO Medical Assistance Program"
        DSWD = "DSWD", "DSWD Assistance to Individuals in Crisis Situations"
        DOH = "DOH", "DOH Medical Assistance"
        SENATE = "SENATE", "Senate Guarantee Letter"
        OP = "OP", "Office for Facilitation of Presidential Assistance"

    class AssistanceType(models.TextChoices):
        CHEMOTHERAPY = "CHEMOTHERAPY", "Chemotherapy drugs and immunotherapy"
        RADIATION = "RADIATION", "Radiation therapy"
        IMPLANTS = "IMPLANTS", "Implants and devices"
        HOSPITAL_BILL = "HOSPITAL_BILL", "Hospital bill"
        MEDICINES = "MEDICINES", "Medicines and treatment"
        OTHER = "OTHER", "Other medical assistance"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guarantee_applications",
    )
    program = models.CharField(max_length=20, choices=Program.choices)
    assistance_type = models.CharField(max_length=30, choices=AssistanceType.choices)
    patient_name = models.CharField(max_length=150)
    hospital = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    diagnosis = models.CharField(max_length=250)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    admin_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_guarantee_applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount_requested__gt=0),
                name="application_amount_positive",
            ),
        ]

    def __str__(self):
        return f"Application #{self.pk} - {self.patient_name}"


class ApplicationDocument(models.Model):
    class Kind(models.TextChoices):
        MAP_FORM = "MAP_FORM", "MAP application form"
        PATIENT_ID = "PATIENT_ID", "Valid ID of the patient"
        CLINICAL_ABSTRACT = "CLINICAL_ABSTRACT", "Clinical abstract"
        PRESCRIPTION = "PRESCRIPTION", "Updated original prescription"
        TREATMENT_PROTOCOL = "TREATMENT_PROTOCOL", "Treatment protocol"
        AUTHORIZATION = "AUTHORIZATION", "Authorization letter"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    application = models.ForeignKey(
        GuaranteeApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    file = models.FileField(upload_to=document_upload_path)
    review_status = models.CharField(
        max_length=12,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    review_note = models.CharField(max_length=300, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_application_documents",
    )
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("application", "kind"),
                name="unique_application_document_kind",
            )
        ]
        ordering = ("kind",)

    def __str__(self):
        return f"{self.get_kind_display()} for application #{self.application_id}"


class ApplicationQuotation(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        RECEIVED = "RECEIVED", "Received"

    application = models.ForeignKey(
        GuaranteeApplication,
        on_delete=models.CASCADE,
        related_name="quotations",
    )
    supplier = models.CharField(max_length=200)
    items = models.CharField(max_length=300)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    file = models.FileField(upload_to=quotation_upload_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__isnull=True) | models.Q(amount__gte=0),
                name="quotation_amount_not_negative",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="RECEIVED")
                    # NULL > 0 is "unknown" in SQL, which a CHECK lets through,
                    # so the amount must be explicitly non-null as well.
                    | models.Q(amount__isnull=False, amount__gt=0)
                ),
                name="received_quotation_has_amount",
            ),
        ]

    def __str__(self):
        return f"{self.supplier} quote for application #{self.application_id}"


REQUIRED_DOCUMENTS = {
    GuaranteeApplication.AssistanceType.CHEMOTHERAPY: (
        ApplicationDocument.Kind.MAP_FORM,
        ApplicationDocument.Kind.PATIENT_ID,
        ApplicationDocument.Kind.CLINICAL_ABSTRACT,
        ApplicationDocument.Kind.PRESCRIPTION,
        ApplicationDocument.Kind.TREATMENT_PROTOCOL,
    ),
    GuaranteeApplication.AssistanceType.RADIATION: (
        ApplicationDocument.Kind.MAP_FORM,
        ApplicationDocument.Kind.PATIENT_ID,
        ApplicationDocument.Kind.CLINICAL_ABSTRACT,
        ApplicationDocument.Kind.PRESCRIPTION,
    ),
    GuaranteeApplication.AssistanceType.IMPLANTS: (
        ApplicationDocument.Kind.MAP_FORM,
        ApplicationDocument.Kind.PATIENT_ID,
        ApplicationDocument.Kind.CLINICAL_ABSTRACT,
        ApplicationDocument.Kind.PRESCRIPTION,
    ),
}

BASE_REQUIRED_DOCUMENTS = (
    ApplicationDocument.Kind.PATIENT_ID,
    ApplicationDocument.Kind.CLINICAL_ABSTRACT,
    ApplicationDocument.Kind.PRESCRIPTION,
)

REQUIRED_QUOTATIONS = {
    GuaranteeApplication.AssistanceType.CHEMOTHERAPY: 1,
    GuaranteeApplication.AssistanceType.RADIATION: 1,
    GuaranteeApplication.AssistanceType.IMPLANTS: 3,
}


def required_document_kinds(assistance_type):
    return REQUIRED_DOCUMENTS.get(assistance_type, BASE_REQUIRED_DOCUMENTS)


def required_quotation_count(assistance_type):
    return REQUIRED_QUOTATIONS.get(assistance_type, 0)
