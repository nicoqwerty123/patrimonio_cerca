from django.conf import settings

from .models import Alerta, Favorito


def avisos(request):
    """Datos globales: insignias del menú y configuración del mapa base."""
    datos = {
        "avisos_pendientes": 0,
        "n_favoritos": 0,
        "tiles": {"url": settings.TILES_URL, "attr": settings.TILES_ATTR},
    }
    uid = f"usr_{request.user.pk}" if request.user.is_authenticated else request.session.get("uid")
    if uid:
        alertas = Alerta.objects.filter(uid=uid, leida=False).select_related("recurso")
        datos["avisos_pendientes"] = sum(1 for a in alertas if a.esta_pendiente())
        datos["n_favoritos"] = Favorito.objects.filter(uid=uid).count()
    return datos
