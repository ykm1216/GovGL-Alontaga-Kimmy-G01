from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ProfileForm, RegistrationForm
from .models import CustomUser


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account was created successfully. Please log in.")
            return redirect("login")
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    next_url = request.GET.get("next", "")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}.")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()
        if next_url:
            messages.error(request, "Please log in to open that page.")

    return render(request, "accounts/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


@login_required
def dashboard_view(request):
    """Send each user to the dashboard that fits their role."""
    if request.user.role == CustomUser.Role.ADMIN:
        return redirect("admin_dashboard")
    return redirect("patient_dashboard")


@login_required
def patient_dashboard_view(request):
    if request.user.role != CustomUser.Role.PATIENT:
        messages.error(request, "You do not have access to that page.")
        return redirect("dashboard")
    return render(request, "accounts/patient_dashboard.html")


@login_required
def admin_dashboard_view(request):
    if request.user.role != CustomUser.Role.ADMIN:
        messages.error(request, "You do not have access to that page.")
        return redirect("dashboard")
    users = CustomUser.objects.order_by("-date_joined")
    context = {
        "total_users": users.count(),
        "total_patients": users.filter(role=CustomUser.Role.PATIENT).count(),
        "total_admins": users.filter(role=CustomUser.Role.ADMIN).count(),
        "recent_users": users[:10],
    }
    return render(request, "accounts/admin_dashboard.html", context)


@login_required
def profile_view(request):
    # Always uses request.user, so people can only view and edit their own profile.
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was updated successfully.")
            return redirect("profile")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})