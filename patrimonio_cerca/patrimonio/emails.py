import json
import logging
import os
import threading
import urllib.request

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

# Tiempo máximo (segundos) de espera a la API de Brevo y al fallback SMTP.
# Impide que un proveedor caido deje colgada la respuesta web.
BREVO_TIMEOUT = 6


def _enviar_correo(asunto, mensaje_plano, mensaje_html, destinatario):
    """Envia un correo via Brevo API v3 (HTTPS) o, como respaldo, via SMTP de Django.

    Nunca lanza excepciones: devuelve True si se envio y False en caso contrario.
    La clave API se lee de la configuracion (variables de entorno), nunca del codigo.
    """
    if not destinatario:
        return False

    brevo_api_key = (
        getattr(settings, "BREVO_API_KEY", "")
        or os.environ.get("BREVO_API_KEY", "")
    ).strip()
    sender_email = (
        getattr(settings, "BREVO_SENDER_EMAIL", "")
        or os.environ.get("BREVO_SENDER_EMAIL", "")
    ).strip()

    # 1. Envio via Brevo API v3: usa HTTPS (puerto 443), ideal para plataformas
    #    como Render donde los puertos SMTP (25/465/587) estan bloqueados.
    if brevo_api_key and sender_email:
        try:
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=json.dumps({
                    "sender": {"name": "Patrimonio Cerca", "email": sender_email},
                    "to": [{"email": destinatario}],
                    "subject": asunto,
                    "htmlContent": mensaje_html,
                    "textContent": mensaje_plano,
                }).encode("utf-8"),
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=BREVO_TIMEOUT) as resp:
                if resp.status in (200, 201, 202):
                    logger.info(f"Correo enviado via Brevo API a {destinatario}")
                    return True
                logger.warning(f"Brevo API respondio HTTP {resp.status} para {destinatario}")
        except Exception as e:
            logger.warning(f"Fallo envio via Brevo API ({destinatario}): {e}")
    elif brevo_api_key:
        logger.warning("BREVO_SENDER_EMAIL no esta configurado; se omite Brevo API.")

    # 2. Respaldo SMTP de Django con timeout corto y silencioso (ver EMAIL_TIMEOUT
    #    en settings). En desarrollo sin EMAIL_HOST solo imprime en consola.
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "Patrimonio Cerca"
        email = EmailMultiAlternatives(
            subject=asunto,
            body=mensaje_plano,
            from_email=from_email,
            to=[destinatario],
        )
        email.attach_alternative(mensaje_html, "text/html")
        return bool(email.send(fail_silently=True))
    except Exception as e:
        logger.error(f"Error al enviar correo a {destinatario}: {e}")
        return False


def _en_segundo_plano(func, *args, **kwargs):
    """Ejecuta una funcion en un hilo daemon para no bloquear la respuesta web."""
    hilo = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    hilo.start()
    return hilo


def enviar_correo_bienvenida(user, base_url="http://127.0.0.1:8000"):
    """Envia el correo de bienvenida tras registrarse."""
    if not user.email:
        return False

    nombre = user.first_name or user.username
    asunto = f"Bienvenido/a a Patrimonio Cerca, {nombre}"

    plano = f"""Hola {nombre},

Tu cuenta en Patrimonio Cerca ya esta activa.

A partir de ahora puedes:
- Guardar tus monumentos y museos favoritos en 'Mi ruta'.
- Recibir avisos y alertas antes de tus actividades culturales.

Empieza a explorar aqui:
{base_url}/

El equipo de Patrimonio Cerca.
""".strip()

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #F7F5F0; margin: 0; padding: 20px 10px; color: #1C2329; }}
    .caja {{ max-width: 440px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2DDD6; border-radius: 12px; padding: 26px 22px; box-shadow: 0 2px 8px rgba(28,35,41,0.05); }}
    .logo {{ font-size: 24px; color: #C8902A; margin-bottom: 6px; }}
    h1 {{ font-size: 19px; color: #1A3D6B; margin: 0 0 10px 0; font-weight: 700; }}
    p {{ font-size: 14px; line-height: 1.55; color: #4A5568; margin: 0 0 12px 0; }}
    .puntos {{ background: #F4F7FB; border-radius: 8px; padding: 12px 16px; margin: 14px 0; font-size: 13px; color: #2D3748; }}
    .puntos li {{ margin-bottom: 4px; }}
    .btn {{ display: inline-block; background: #1A3D6B; color: #FFFFFF !important; text-decoration: none; font-size: 13px; font-weight: 600; padding: 10px 20px; border-radius: 6px; }}
    .footer {{ font-size: 11px; color: #A0AEC0; margin-top: 20px; padding-top: 12px; border-top: 1px solid #E2DDD6; text-align: center; }}
  </style>
</head>
<body>
  <div class="caja">
    <div class="logo">&#x2B21;</div>
    <h1>Hola {nombre}, tu cuenta esta lista</h1>
    <p>Te damos la bienvenida a <strong>Patrimonio Cerca</strong>. Ya puedes comenzar a descubrir y guardar sitios patrimoniales cerca de ti.</p>

    <div class="puntos">
      <ul style="margin: 0; padding-left: 18px;">
        <li>Planifica y optimiza tus recorridos en <em>Mi ruta</em>.</li>
        <li>Programa avisos por correo para tus actividades favoritas.</li>
      </ul>
    </div>

    <div style="text-align: center; margin-top: 18px;">
      <a href="{base_url}/" class="btn">Explorar el mapa ahora</a>
    </div>

    <div class="footer">
      Patrimonio Cerca &middot; Plataforma cultural comunitaria
    </div>
  </div>
</body>
</html>"""
    return _enviar_correo(asunto, plano, html, user.email)


def enviar_correo_bienvenida_async(user, base_url="http://127.0.0.1:8000"):
    """Despacha el correo de bienvenida en segundo plano sin demorar la respuesta web."""
    return _en_segundo_plano(enviar_correo_bienvenida, user, base_url=base_url)


def enviar_correo_confirmacion_alerta(email, recurso, dias_antes, fecha_aviso, base_url="http://127.0.0.1:8000"):
    """Envia la confirmacion inmediata al programar una alerta."""
    if not email:
        return False

    asunto = f"Alerta confirmada: {recurso.titulo}"
    texto_dias = "el mismo dia del evento" if dias_antes == 0 else f"{dias_antes} dia(s) antes"

    plano = f"""Hola,

Has programado una alerta cultural para la siguiente actividad:

Actividad: {recurso.titulo}
Categoria: {recurso.categoria.nombre}
Ubicacion: {recurso.direccion}, {recurso.comuna}
Fechas: {recurso.fechas_texto}
Horario: {recurso.horario or 'Consultar en sitio web'}
Costo: {recurso.costo_texto}

Te enviaremos un recordatorio {texto_dias} (el {fecha_aviso.strftime('%d/%m/%Y')}).

Ver detalles y mapa:
{base_url}/lugar/{recurso.pk}/

Patrimonio Cerca
""".strip()

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F7F5F0; margin: 0; padding: 20px 10px; color: #1C2329; }}
    .card {{ max-width: 480px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2DDD6; padding: 24px; box-shadow: 0 2px 8px rgba(28,35,41,0.06); }}
    .header {{ text-align: center; margin-bottom: 16px; }}
    .logo {{ font-size: 24px; color: #C8902A; }}
    h1 {{ margin: 6px 0 0; font-size: 19px; font-weight: 700; color: #1A3D6B; }}
    .highlight {{ background: #FEF3C7; border: 1px solid #FDE68A; color: #92600A; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin: 14px 0; font-weight: 500; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }}
    .info-table td {{ padding: 6px 0; border-bottom: 1px solid #E2DDD6; }}
    .info-table td.label {{ color: #718096; width: 100px; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
    .cta-btn {{ display: inline-block; background: #1A3D6B; color: #FFFFFF !important; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; font-size: 13px; margin-top: 10px; }}
    .footer {{ text-align: center; font-size: 11px; color: #A0AEC0; padding-top: 14px; margin-top: 14px; border-top: 1px solid #E2DDD6; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">&#x2B21;</div>
      <h1>Recordatorio Programado</h1>
    </div>

    <div class="highlight">
      Te avisaremos {texto_dias} (el {fecha_aviso.strftime('%d/%m/%Y')}).
    </div>

    <h2 style="font-size: 16px; margin: 0 0 10px; color: #1A3D6B;">{recurso.titulo}</h2>

    <table class="info-table">
      <tr><td class="label">Categoria</td><td>{recurso.categoria.nombre}</td></tr>
      <tr><td class="label">Fechas</td><td>{recurso.fechas_texto}</td></tr>
      <tr><td class="label">Direccion</td><td>{recurso.direccion}, {recurso.comuna}</td></tr>
      <tr><td class="label">Horario</td><td>{recurso.horario or 'Sin informacion'}</td></tr>
      <tr><td class="label">Costo</td><td>{recurso.costo_texto}</td></tr>
    </table>

    <div style="text-align: center; margin-top: 16px;">
      <a href="{base_url}/lugar/{recurso.pk}/" class="cta-btn">Ver ficha y ubicacion</a>
    </div>

    <div class="footer">
      Patrimonio Cerca &middot; Sistema de Alertas Culturales
    </div>
  </div>
</body>
</html>""".strip()

    return _enviar_correo(asunto, plano, html, email)


def enviar_correo_confirmacion_alerta_async(email, recurso, dias_antes, fecha_aviso, base_url="http://127.0.0.1:8000"):
    """Despacha la confirmacion de alerta en segundo plano sin demorar la respuesta web."""
    return _en_segundo_plano(
        enviar_correo_confirmacion_alerta, email, recurso, dias_antes, fecha_aviso, base_url=base_url
    )
