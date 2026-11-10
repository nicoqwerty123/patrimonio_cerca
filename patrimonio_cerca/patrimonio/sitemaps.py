from django.contrib.sitemaps import Sitemap

from .models import RecursoCultural


class PaginasSitemap(Sitemap):
    """Páginas principales del sitio (mapa, rutas, alertas)."""
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return ["/", "/ruta/", "/alertas/", "/registro/"]

    def location(self, item):
        return item


class RecursosSitemap(Sitemap):
    """Ficha pública de cada sitio y actividad cultural."""
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return RecursoCultural.objects.all()

    def location(self, obj):
        return f"/lugar/{obj.pk}/"
