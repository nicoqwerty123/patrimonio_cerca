from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class FormularioRegistro(UserCreationForm):
    email = forms.EmailField(
        required=False,
        help_text="Opcional. Te servirá para recuperar tu cuenta en el futuro.",
        widget=forms.EmailInput(attrs={"placeholder": "correo@ejemplo.com", "autocomplete": "email"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Tu nombre de usuario",
            "autocomplete": "username",
            "autofocus": True
        })
        self.fields["username"].help_text = "Letras, números y @/./+/-/_ únicamente."
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input-auth")


class FormularioLogin(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Nombre de usuario",
            "autocomplete": "username",
            "autofocus": True,
            "class": "input-auth",
        })
        self.fields["password"].widget.attrs.update({
            "placeholder": "Contraseña",
            "autocomplete": "current-password",
            "class": "input-auth",
        })
