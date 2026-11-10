from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from patrimonio.sitemaps import PaginasSitemap, RecursosSitemap

sitemaps = {
    "paginas": PaginasSitemap,
    "recursos": RecursosSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="patrimonio/robots.txt", content_type="text/plain; charset=utf-8"),
        name="robots",
    ),
    path("", include("patrimonio.urls")),
]
