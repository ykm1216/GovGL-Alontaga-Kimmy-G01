from django.urls import path

from . import views

urlpatterns = [
    path("", views.application_list_view, name="application_list"),
    path("new/", views.application_create_view, name="application_create"),
    path("<int:application_id>/", views.application_detail_view, name="application_detail"),
    path(
        "documents/<int:document_id>/download/",
        views.document_download_view,
        name="document_download",
    ),
    path(
        "quotations/<int:quotation_id>/download/",
        views.quotation_download_view,
        name="quotation_download",
    ),
    path("<int:application_id>/edit/", views.application_edit_view, name="application_edit"),
    path("<int:application_id>/delete/", views.application_delete_view, name="application_delete"),
    path("<int:application_id>/submit/", views.application_submit_view, name="application_submit"),
    path(
        "<int:application_id>/documents/<str:kind>/upload/",
        views.document_upload_view,
        name="document_upload",
    ),
    path(
        "<int:application_id>/documents/<int:document_id>/delete/",
        views.document_delete_view,
        name="document_delete",
    ),
    path(
        "<int:application_id>/quotations/add/",
        views.quotation_create_view,
        name="quotation_create",
    ),
    path(
        "<int:application_id>/quotations/<int:quotation_id>/delete/",
        views.quotation_delete_view,
        name="quotation_delete",
    ),
    path("review/", views.review_list_view, name="review_list"),
    path(
        "review/<int:application_id>/",
        views.review_detail_view,
        name="review_detail",
    ),
    path(
        "review/<int:application_id>/documents/<int:document_id>/",
        views.document_review_view,
        name="document_review",
    ),
    path(
        "review/<int:application_id>/decision/",
        views.application_review_view,
        name="application_review",
    ),
]
