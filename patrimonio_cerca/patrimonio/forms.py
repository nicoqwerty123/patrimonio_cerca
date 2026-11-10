import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


def validar_contrasena(password):
    """Reglas de contraseña compartidas por registro y recuperación."""
    if not password:
        return password

    errores = []
    if len(password) < 8:
        errores.append("Debe tener al menos 8 caracteres.")

    if not re.search(r"[A-Z]", password):
        errores.append("Debe contener al menos una letra mayúscula (A-Z).")

    # Verifica al menos un carácter especial (no alfanumérico)
    if not re.search(r"[^a-zA-Z0-9\s]", password):
        errores.append("Debe contener al menos un carácter especial (ejemplo: ! @ # $ % * _ - ?).")

    if errores:
        raise ValidationError(errores)

    return password


class FormularioRegistro(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        help_text="Te enviaremos tu confirmación de bienvenida y avisos culturales aquí.",
        widget=forms.EmailInput(attrs={
            "placeholder": "tu_correo@ejemplo.com",
            "autocomplete": "email",
            "required": True,
        })
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nombre de usuario"
        self.fields["username"].widget.attrs.update({
            "placeholder": "Tu nombre de usuario",
            "autocomplete": "username",
            "autofocus": True,
            "required": True,
        })
        self.fields["username"].help_text = "Letras, números y caracteres @/./+/-/_ únicamente."

        self.fields["password1"].label = "Contraseña"
        self.fields["password1"].help_text = (
            "Debe tener mínimo 8 caracteres, incluir al menos una mayúscula (A-Z) y un carácter especial (!@#$%...). "
        )

        self.fields["password2"].label = "Confirmar contraseña"
        self.fields["password2"].help_text = "Vuelve a escribir la misma contraseña."

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input-auth")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("El correo electrónico es obligatorio.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe una cuenta registrada con este correo electrónico.")
        return email

    def clean_password1(self):
        return validar_contrasena(self.cleaned_data.get("password1"))


class FormularioNuevaPassword(SetPasswordForm):
    """Restablecimiento de contraseña con los mismos textos y reglas del registro."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Nueva contraseña"
        self.fields["new_password1"].help_text = (
            "Mínimo 8 caracteres, una mayúscula (A-Z) y un carácter especial (!@#$%...)."
        )
        self.fields["new_password2"].label = "Confirmar nueva contraseña"
        self.fields["new_password2"].help_text = "Vuelve a escribir la misma contraseña."
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input-auth")

    def clean_new_password1(self):
        return validar_contrasena(self.cleaned_data.get("new_password1"))


class FormularioRecuperarPassword(PasswordResetForm):
    """Pide el correo para enviar el enlace de recuperación, con textos del sitio."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Correo electrónico"
        self.fields["email"].widget.attrs.update({
            "placeholder": "tu_correo@ejemplo.com",
            "autocomplete": "email",
            "autofocus": True,
            "class": "input-auth",
        })


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
