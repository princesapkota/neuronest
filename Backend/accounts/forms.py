from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from accounts.models import Profile, Sex


class PatientSignupForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    hospital_patient_id = forms.CharField(max_length=50)
    sex = forms.ChoiceField(choices=Sex.choices)
    age = forms.IntegerField(min_value=0, max_value=130)

    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email is already registered.")
        return email

    def clean_hospital_patient_id(self):
        pid = self.cleaned_data["hospital_patient_id"].strip()
        if Profile.objects.filter(hospital_patient_id=pid).exists():
            raise ValidationError("This patient ID is already registered.")
        return pid

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            raise ValidationError("Passwords do not match.")
        return cleaned