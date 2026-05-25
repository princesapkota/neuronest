from django import forms
from accounts.models import Profile
from .models import DiagnosticResult

# this is the form an employee fills to upload a scan, it picks the patient, the model and the file
class DiagnosticUploadForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=Profile.objects.filter(role="patient").order_by("full_name"),
        required=True,
        label="Patient",
    )

    model_type = forms.ChoiceField(
        choices=DiagnosticResult.ModelType.choices,
        required=True,
        label="Model",
    )

    input_file = forms.FileField(required=True, label="Upload file")

    # this makes sure the uploaded file type matches the chosen model (nii for brain, image for the rest)
    def clean(self):
        cleaned = super().clean()
        model_type = cleaned.get("model_type")
        f = cleaned.get("input_file")
        if not model_type or not f:
            return cleaned

        name = (f.name or "").lower()

        if model_type == DiagnosticResult.ModelType.BRAIN_TUMOR:
            if not (name.endswith(".nii") or name.endswith(".nii.gz")):
                raise forms.ValidationError("Brain tumor requires .nii or .nii.gz.")
        else:
            if not (name.endswith(".jpg") or name.endswith(".jpeg") or name.endswith(".png")):
                raise forms.ValidationError("Pneumonia/Fracture require .jpg/.jpeg/.png.")
        return cleaned
    

    