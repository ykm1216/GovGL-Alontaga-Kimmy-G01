from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser

from .forms import DocumentUploadForm
from .models import (
    ApplicationDocument,
    ApplicationQuotation,
    GuaranteeApplication,
    required_document_kinds,
)


def create_application(user, **overrides):
    values = {
        "program": GuaranteeApplication.Program.PCSO,
        "assistance_type": GuaranteeApplication.AssistanceType.CHEMOTHERAPY,
        "patient_name": "Jamie Cruz",
        "hospital": "City General Hospital",
        "city": "Cebu City",
        "diagnosis": "Cancer",
        "amount_requested": "85000.00",
    }
    values.update(overrides)
    return GuaranteeApplication.objects.create(user=user, **values)


class ApplicationWorkflowTests(TestCase):
    def setUp(self):
        self.patient = CustomUser.objects.create_user(
            username="patient",
            password="Test-password-123",
            email="patient@example.com",
            role=CustomUser.Role.PATIENT,
        )
        self.other_patient = CustomUser.objects.create_user(
            username="other",
            password="Test-password-123",
            email="other@example.com",
            role=CustomUser.Role.PATIENT,
        )
        self.client.force_login(self.patient)

    def test_patient_can_create_edit_and_delete_own_draft(self):
        response = self.client.post(
            reverse("application_create"),
            {
                "program": GuaranteeApplication.Program.PCSO,
                "assistance_type": GuaranteeApplication.AssistanceType.CHEMOTHERAPY,
                "patient_name": "Jamie Cruz",
                "hospital": "City General Hospital",
                "city": "Cebu City",
                "diagnosis": "Cancer",
                "amount_requested": "85000.00",
            },
        )
        application = GuaranteeApplication.objects.get(user=self.patient)
        self.assertRedirects(
            response,
            reverse("application_detail", args=(application.pk,)),
        )

        response = self.client.post(
            reverse("application_edit", args=(application.pk,)),
            {
                "program": GuaranteeApplication.Program.PCSO,
                "assistance_type": GuaranteeApplication.AssistanceType.CHEMOTHERAPY,
                "patient_name": "Jamie Cruz",
                "hospital": "Updated Hospital",
                "city": "Cebu City",
                "diagnosis": "Cancer",
                "amount_requested": "90000.00",
            },
        )
        application.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("application_detail", args=(application.pk,)),
        )
        self.assertEqual(application.hospital, "Updated Hospital")

        response = self.client.post(reverse("application_delete", args=(application.pk,)))
        self.assertRedirects(response, reverse("application_list"))
        self.assertFalse(GuaranteeApplication.objects.filter(pk=application.pk).exists())

    def test_patient_cannot_view_another_users_application(self):
        application = create_application(self.other_patient)
        response = self.client.get(reverse("application_detail", args=(application.pk,)))
        self.assertEqual(response.status_code, 404)

    def test_uploaded_documents_download_only_for_the_owner_or_admin(self):
        application = create_application(self.patient)
        document_url = reverse(
            "document_upload",
            args=(application.pk, ApplicationDocument.Kind.PATIENT_ID),
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                document_url,
                {"file": SimpleUploadedFile("patient-id.pdf", b"%PDF-1.4\ndocument")},
            )
            self.assertRedirects(
                response,
                reverse("application_detail", args=(application.pk,)),
            )
            document = ApplicationDocument.objects.get(application=application)
            download_url = reverse("document_download", args=(document.pk,))

            download = self.client.get(download_url)
            self.assertEqual(b"".join(download.streaming_content), b"%PDF-1.4\ndocument")
            download.close()

            self.client.force_login(self.other_patient)
            self.assertEqual(self.client.get(download_url).status_code, 404)

            admin = CustomUser.objects.create_user(
                username="reviewer",
                password="Test-password-123",
                email="reviewer@example.com",
                role=CustomUser.Role.ADMIN,
            )
            self.client.force_login(admin)
            # Admins cannot open files on a patient's unsubmitted draft.
            self.assertEqual(self.client.get(download_url).status_code, 404)

            application.status = GuaranteeApplication.Status.SUBMITTED
            application.save(update_fields=("status",))
            admin_download = self.client.get(download_url)
            self.assertEqual(admin_download.status_code, 200)
            admin_download.close()

    def test_patient_cannot_open_administrator_review_queue(self):
        response = self.client.get(reverse("review_list"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_submission_requires_documents_and_received_quotations(self):
        application = create_application(self.patient)
        submit_url = reverse("application_submit", args=(application.pk,))

        response = self.client.post(submit_url)
        self.assertRedirects(
            response,
            reverse("application_detail", args=(application.pk,)),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, GuaranteeApplication.Status.DRAFT)

        for kind in required_document_kinds(application.assistance_type):
            ApplicationDocument.objects.create(
                application=application,
                kind=kind,
                file="example.pdf",
            )
        ApplicationQuotation.objects.create(
            application=application,
            supplier="Local supplier",
            items="Treatment",
            status=ApplicationQuotation.Status.RECEIVED,
            amount="78000.00",
        )

        response = self.client.post(submit_url)
        self.assertRedirects(
            response,
            reverse("application_detail", args=(application.pk,)),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, GuaranteeApplication.Status.SUBMITTED)
        self.assertIsNotNone(application.submitted_at)

    def test_upload_validation_rejects_unsupported_and_oversized_files(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        unsupported = DocumentUploadForm(
            files={"file": SimpleUploadedFile("notes.txt", b"not a document")}
        )
        mislabeled = DocumentUploadForm(
            files={"file": SimpleUploadedFile("notes.pdf", b"not a PDF")}
        )
        oversized = DocumentUploadForm(
            files={
                "file": SimpleUploadedFile(
                    "large.pdf",
                    b"x" * (5 * 1024 * 1024 + 1),
                )
            }
        )
        self.assertFalse(unsupported.is_valid())
        self.assertFalse(mislabeled.is_valid())
        self.assertFalse(oversized.is_valid())


class ApplicationReviewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="reviewer",
            password="Test-password-123",
            email="reviewer@example.com",
            role=CustomUser.Role.ADMIN,
        )
        self.patient = CustomUser.objects.create_user(
            username="applicant",
            password="Test-password-123",
            email="applicant@example.com",
            role=CustomUser.Role.PATIENT,
        )
        self.application = create_application(
            self.patient,
            status=GuaranteeApplication.Status.SUBMITTED,
        )
        self.client.force_login(self.admin)

    def add_required_documents(self, review_status):
        for kind in required_document_kinds(self.application.assistance_type):
            ApplicationDocument.objects.create(
                application=self.application,
                kind=kind,
                file="example.pdf",
                review_status=review_status,
            )

    def add_received_quotation(self):
        ApplicationQuotation.objects.create(
            application=self.application,
            supplier="Local supplier",
            items="Treatment",
            status=ApplicationQuotation.Status.RECEIVED,
            amount="78000.00",
        )

    def test_approval_requires_all_required_documents_to_be_accepted(self):
        self.add_required_documents(ApplicationDocument.ReviewStatus.PENDING)
        self.add_received_quotation()
        decision_url = reverse("application_review", args=(self.application.pk,))

        self.client.post(
            decision_url,
            {
                "status": GuaranteeApplication.Status.APPROVED,
                "admin_note": "",
            },
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, GuaranteeApplication.Status.SUBMITTED)

        ApplicationDocument.objects.filter(application=self.application).update(
            review_status=ApplicationDocument.ReviewStatus.ACCEPTED
        )
        self.client.post(
            decision_url,
            {
                "status": GuaranteeApplication.Status.APPROVED,
                "admin_note": "",
            },
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, GuaranteeApplication.Status.APPROVED)

    def test_rejection_requires_a_reason(self):
        response = self.client.post(
            reverse("application_review", args=(self.application.pk,)),
            {
                "status": GuaranteeApplication.Status.REJECTED,
                "admin_note": "",
            },
        )
        self.assertRedirects(
            response,
            reverse("review_detail", args=(self.application.pk,)),
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, GuaranteeApplication.Status.SUBMITTED)


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_custom_404_page(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page not found", status_code=404)

    def test_other_users_application_shows_custom_404_page(self):
        owner = CustomUser.objects.create_user(
            username="owner", password="Test-password-123", email="owner@example.com"
        )
        intruder = CustomUser.objects.create_user(
            username="intruder", password="Test-password-123", email="intruder@example.com"
        )
        application = create_application(owner)
        self.client.force_login(intruder)
        response = self.client.get(reverse("application_detail", args=[application.pk]))
        self.assertTemplateUsed(response, "404.html")

    def test_500_page_renders_without_request_context(self):
        from django.template.loader import render_to_string

        html = render_to_string("500.html")
        self.assertIn("Something went wrong", html)

    def test_missing_csrf_token_shows_expired_form_page(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("login"), {"username": "a", "password": "b"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "This form has expired", status_code=403)
