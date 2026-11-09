from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Prueba el envio real de correos electronicos configurados en settings."

    def add_arguments(self, parser):
        parser.add_argument("destinatario", type=str, help="Correo electronico de destino para la prueba.")

    def handle(self, *args, **options):
        dest = options["destinatario"]
        self.stdout.write(f"Iniciando prueba de envio a: {dest}")
        self.stdout.write(f"Backend actual: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Servidor SMTP: {getattr(settings, 'EMAIL_HOST', 'None (Consola local)')}")
        self.stdout.write(f"Remitente: {settings.DEFAULT_FROM_EMAIL}")

        try:
            send_mail(
                subject="Prueba de correo - Patrimonio Cerca",
                message="¡Hola! Si estas leyendo este correo, la conexion SMTP de Patrimonio Cerca esta funcionando correctamente.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[dest],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"¡EXITO! Correo enviado exitosamente a {dest}."))
            if "console" in settings.EMAIL_BACKEND:
                self.stdout.write(self.style.WARNING("NOTA: El backend actual es 'console' (se imprimio arriba en pantalla). Para que llegue a tu bandeja real, debes configurar un servidor SMTP en tu archivo .env"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR al enviar correo: {e}"))
