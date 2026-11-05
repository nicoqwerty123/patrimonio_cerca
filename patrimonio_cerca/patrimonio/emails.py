import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

logger = logging.getLogger(__name__)


def _enviar_correo(asunto, mensaje_plano, mensaje_html, destinatario):
    """Envía un correo electrónico multipart (texto + HTML) de forma segura."""
    if not destinatario:
        return False
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Patrimonio Cerca <contacto@patrimoniocerca.cl>")
        email = EmailMultiAlternatives(
            subject=asunto,
            body=mensaje_plano,
            from_email=from_email,
            to=[destinatario],
        )
        email.attach_alternative(mensaje_html, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo a {destinatario}: {e}")
        return False


def enviar_correo_bienvenida(user):
    """Envía un correo de bienvenida tras el registro."""
    if not user.email:
        return False

    asunto = "¡Bienvenido/a a Patrimonio Cerca! 🏛️"
    nombre = user.first_name or user.username

    plano = f"""
Hola {nombre},

¡Gracias por unirte a Patrimonio Cerca!

Ahora tienes acceso a todas las herramientas para descubrir y disfrutar el patrimonio cultural de Chile:
- Explora el mapa interactivo con más de 30 sitios y actividades verificadas.
- Guarda tus lugares favoritos y genera tu recorrido optimizado en Google Maps.
- Activa alertas personalizadas para que no te pierdas eventos, talleres ni aperturas especiales.

Puedes acceder a tu cuenta en cualquier momento desde:
http://127.0.0.1:8000/

¡Que disfrutes tu viaje cultural!
El equipo de Patrimonio Cerca
    """.strip()

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F7F5F0; margin: 0; padding: 24px 12px; color: #1C2329; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2DDD6; overflow: hidden; box-shadow: 0 4px 12px rgba(28,35,41,0.06); }}
    .header {{ background: #1A3D6B; padding: 28px 24px; text-align: center; color: #FFFFFF; }}
    .logo {{ font-size: 28px; line-height: 1; margin-bottom: 8px; color: #C8902A; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; color: #FFFFFF; }}
    .body {{ padding: 28px 24px; font-size: 15px; line-height: 1.6; color: #333333; }}
    .feature-box {{ background: #F4F7FB; border-left: 3px solid #1A3D6B; padding: 14px 16px; border-radius: 0 8px 8px 0; margin: 20px 0; font-size: 14px; }}
    .feature-box ul {{ margin: 6px 0 0 16px; padding: 0; }}
    .feature-box li {{ margin-bottom: 6px; }}
    .cta-btn {{ display: inline-block; background: #1A3D6B; color: #FFFFFF !important; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; margin-top: 12px; }}
    .footer {{ text-align: center; font-size: 12px; color: #888888; padding: 20px 24px; border-top: 1px solid #E2DDD6; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">⬡</div>
      <h1>¡Bienvenido a Patrimonio Cerca!</h1>
    </div>
    <div class="body">
      <p>Hola <strong>{nombre}</strong>,</p>
      <p>Nos alegra que formes parte de nuestra comunidad. Tu cuenta ha sido creada exitosamente.</p>
      
      <div class="feature-box">
        <strong>Con tu cuenta ahora puedes:</strong>
        <ul>
          <li><strong>Guardar tu ruta:</strong> Planifica recorridos a pie por los monumentos y sitios más valiosos.</li>
          <li><strong>Alertas tempranas:</strong> Te avisaremos con anticipación antes de tus actividades favoritas.</li>
          <li><strong>Sincronización:</strong> Tus preferencias se guardan de forma permanente.</li>
        </ul>
      </div>

      <div style="text-align: center; margin: 24px 0 10px;">
        <a href="http://127.0.0.1:8000/" class="cta-btn">Explorar el mapa ahora</a>
      </div>
    </div>
    <div class="footer">
      Patrimonio Cerca · Cultura y comunidad en Chile
    </div>
  </div>
</body>
</html>
    """.strip()

    return _enviar_correo(asunto, plano, html, user.email)


def enviar_correo_confirmacion_alerta(email, recurso, dias_antes, fecha_aviso):
    """Envía un correo confirmando la suscripción a una alerta."""
    if not email:
        return False

    asunto = f"Alerta confirmada: {recurso.titulo} 📅"
    texto_dias = "el mismo día del evento" if dias_antes == 0 else f"{dias_antes} día(s) antes"

    plano = f"""
Hola,

Has programado una alerta cultural para la siguiente actividad:

Actividad: {recurso.titulo}
Categoría: {recurso.categoria.nombre}
Ubicación: {recurso.direccion}, {recurso.comuna}
Fechas: {recurso.fechas_texto}
Horario: {recurso.horario or 'Consultar en sitio web'}
Costo: {recurso.costo_texto}

Te enviaremos un recordatorio {texto_dias} (el {fecha_aviso.strftime('%d/%m/%Y')}).

Ver detalles y mapa de cómo llegar:
http://127.0.0.1:8000/lugar/{recurso.pk}/

¡No te lo pierdas!
Patrimonio Cerca
    """.strip()

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F7F5F0; margin: 0; padding: 24px 12px; color: #1C2329; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2DDD6; overflow: hidden; box-shadow: 0 4px 12px rgba(28,35,41,0.06); }}
    .header {{ background: #1A3D6B; padding: 24px; text-align: center; color: #FFFFFF; }}
    .logo {{ font-size: 24px; color: #C8902A; margin-bottom: 6px; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; color: #FFFFFF; }}
    .body {{ padding: 24px; font-size: 15px; line-height: 1.6; color: #333333; }}
    .highlight {{ background: #FEF3C7; border: 1px solid #FDE68A; color: #92600A; padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-bottom: 18px; font-weight: 500; }}
    .info-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
    .info-table td {{ padding: 8px 0; border-bottom: 1px solid #E2DDD6; }}
    .info-table td.label {{ color: #718096; width: 110px; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
    .cta-btn {{ display: inline-block; background: #1A3D6B; color: #FFFFFF !important; text-decoration: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; font-size: 13px; margin-top: 10px; }}
    .footer {{ text-align: center; font-size: 12px; color: #888888; padding: 18px; border-top: 1px solid #E2DDD6; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">⬡</div>
      <h1>Recordatorio Programado</h1>
    </div>
    <div class="body">
      <div class="highlight">
        🔔 Te avisaremos {texto_dias} (el {fecha_aviso.strftime('%d/%m/%Y')}).
      </div>

      <h2 style="font-size: 18px; margin: 0 0 12px; color: #1A3D6B;">{recurso.titulo}</h2>

      <table class="info-table">
        <tr><td class="label">Categoría</td><td>{recurso.categoria.nombre}</td></tr>
        <tr><td class="label">Fechas</td><td>{recurso.fechas_texto}</td></tr>
        <tr><td class="label">Dirección</td><td>{recurso.direccion}, {recurso.comuna}</td></tr>
        <tr><td class="label">Horario</td><td>{recurso.horario or 'Sin información'}</td></tr>
        <tr><td class="label">Costo</td><td>{recurso.costo_texto}</td></tr>
      </table>

      <div style="text-align: center; margin-top: 20px;">
        <a href="http://127.0.0.1:8000/lugar/{recurso.pk}/" class="cta-btn">Ver ficha y ubicación</a>
      </div>
    </div>
    <div class="footer">
      Patrimonio Cerca · Sistema de Alertas Culturales
    </div>
  </div>
</body>
</html>
    """.strip()

    return _enviar_correo(asunto, plano, html, email)
