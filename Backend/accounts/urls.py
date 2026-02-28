from django.urls import path
from . import views

urlpatterns = [
    path("patient/signup/", views.patient_signup, name="patient_signup"),
    path("verify/sent/", views.verify_email_sent, name="verify_email_sent"),
    path("verify/<uidb64>/<token>/", views.verify_email, name="verify_email"),
]