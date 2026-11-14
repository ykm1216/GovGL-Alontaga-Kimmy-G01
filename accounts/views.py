from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import RegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account was created successfully.")
            return redirect("home")  # becomes the login page in the next commit
        messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})