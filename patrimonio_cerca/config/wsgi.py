import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# Auto-migración y carga de datos en arranque para evitar errores 500 en Render
try:
    from django.core.management import call_command
    call_command("migrate", interactive=False)
    from patrimonio.models import Categoria
    if not Categoria.objects.exists():
        call_command("cargar_datos")
except Exception as _e:
    pass
