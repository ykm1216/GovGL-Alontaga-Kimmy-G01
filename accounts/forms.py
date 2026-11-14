from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser


class RegistrationForm(UserCreationForm):
    """Registration form.

    UserCreationForm already checks that the two passwords match, runs
    Django's password validators, and saves the password hashed.
    """

    first_name = forms.CharField(max_length=150, required=True, label="First name")
    last_name = forms.CharField(max_length=150, required=True, label="Last name")
    email = forms.EmailField(required=True, label="E-mail address")
    contact_number = forms.CharField(max_length=20, required=True, label="Mobile no.")

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("first_name", "last_name", "username", "email", "contact_number")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this e-mail address already exists.")
        return email

    def clean_contact_number(self):
        number = self.cleaned_data["contact_number"].replace(" ", "").replace("-", "")
        if not (number.isdigit() and len(number) == 11 and number.startswith("09")):
            raise forms.ValidationError("Enter an 11-digit mobile number starting with 09.")
        return number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.PATIENT  # public sign-ups are always patients
        if commit:
            user.save()
        return user
