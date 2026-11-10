import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from patrimonio.models import Alerta
from patrimonio.emails import _enviar_correo

# URL publica de la app: en Render/GitHub Actions se define la variable BASE_URL.
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")


class Command(BaseCommand):
    help = "Envía correos electrónicos para las alertas culturales que vencen o comienzan hoy."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        self.stdout.write(f"Verificando alertas para la fecha: {hoy}")

        alertas_pendientes = Alerta.objects.filter(leida=False).select_related("recurso")
        enviadas = 0

        for a in alertas_pendientes:
            if a.esta_pendiente(hoy):
                # Determinar si el uid corresponde a un usuario registrado
                email = None
                if a.uid.startswith("usr_"):
                    try:
                        user_id = int(a.uid.replace("usr_", ""))
                        user = User.objects.get(pk=user_id)
                        email = user.email
                    except (ValueError, User.DoesNotExist):
                        pass

                if email:
                    r = a.recurso
                    asunto = f"¡Recordatorio hoy! {r.titulo} 🏛️"
                    plano = f"Hola,\n\nTe recordamos que la actividad «{r.titulo}» está por comenzar o está activa hoy.\nFechas: {r.fechas_texto}\nLugar: {r.direccion}, {r.comuna}\nHorario: {r.horario}\nCosto: {r.costo_texto}\n\nVer más detalles: {BASE_URL}/lugar/{r.pk}/\n\n¡Que lo disfrutes!\nPatrimonio Cerca"
                    html = f"<h2>Recordatorio: {r.titulo}</h2><p>La actividad cultural que guardaste está activa o comienza hoy.</p><p><strong>Fechas:</strong> {r.fechas_texto}<br><strong>Ubicación:</strong> {r.direccion}, {r.comuna}<br><strong>Horario:</strong> {r.horario}<br><strong>Costo:</strong> {r.costo_texto}</p><p><a href='{BASE_URL}/lugar/{r.pk}/'>Ver detalles de la actividad</a></p>"

                    if _enviar_correo(asunto, plano, html, email):
                        a.leida = True
                        a.save()
                        enviadas += 1
                        self.stdout.write(self.style.SUCCESS(f"Alerta enviada a {email} para {r.titulo}"))

        self.stdout.write(self.style.SUCCESS(f"Proceso finalizado. Total correos enviados: {enviadas}"))
