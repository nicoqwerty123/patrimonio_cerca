import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_TIMEOUT = 6


class BrevoAPIEmailBackend(BaseEmailBackend):
    """Backend de correo de Django que envía por la API HTTP de Brevo.

    Las plataformas PaaS como Render bloquean los puertos SMTP salientes
    (25/465/587); este backend permite que cualquier correo generado por
    Django (recuperar contraseña, verificación, etc.) salga igual que los
    envíos de emails.py: por HTTPS 443.
    """

    def send_messages(self, email_messages):
        api_key = getattr(settings, "BREVO_API_KEY", "")
        sender = getattr(settings, "BREVO_SENDER_EMAIL", "")
        if not api_key or not sender:
            logger.warning("BrevoAPIEmailBackend sin BREVO_API_KEY/BREVO_SENDER_EMAIL: no se envía nada.")
            return 0
        if not email_messages:
            return 0

        enviados = 0
        for msg in email_messages:
            html = ""
            for contenido, tipo in getattr(msg, "alternatives", []):
                if tipo == "text/html":
                    html = contenido
                    break
            try:
                req = urllib.request.Request(
                    "https://api.brevo.com/v3/smtp/email",
                    data=json.dumps({
                        "sender": {"name": "Patrimonio Cerca", "email": sender},
                        "to": [{"email": d} for d in msg.to],
                        "subject": msg.subject,
                        "htmlContent": html or f"<pre>{msg.body}</pre>",
                        "textContent": msg.body,
                    }).encode("utf-8"),
                    headers={
                        "api-key": api_key,
                        "Content-Type": "application/json",
                        "accept": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=BREVO_TIMEOUT) as resp:
                    if resp.status in (200, 201, 202):
                        enviados += 1
                        logger.info(f"Correo de Django enviado via Brevo API a {msg.to}")
            except Exception as e:
                logger.warning(f"Fallo envio via Brevo API ({msg.to}): {e}")
                if not self.fail_silently:
                    raise
        return enviados
