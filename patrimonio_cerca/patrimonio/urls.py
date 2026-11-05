from django.urls import path

from . import views

urlpatterns = [
    path("", views.mapa, name="mapa"),
    path("lugar/<int:pk>/", views.detalle, name="detalle"),
    path("lugar/<int:pk>/calendario.ics", views.calendario, name="calendario"),
    path("ruta/", views.mi_ruta, name="mi_ruta"),
    path("ruta/<int:pk>/guardar/", views.fav_toggle, name="fav_toggle"),
    path("alertas/", views.alertas, name="alertas"),
    path("alertas/<int:pk>/guardar/", views.alerta_guardar, name="alerta_guardar"),
    path("alertas/<int:pk>/eliminar/", views.alerta_eliminar, name="alerta_eliminar"),
    path("api/recursos/", views.api_recursos, name="api_recursos"),
    path("api/buscar/", views.api_buscar, name="api_buscar"),
    path("api/ubicacion/", views.api_ubicacion, name="api_ubicacion"),
    path("api/alertas/pendientes/", views.api_pendientes, name="api_pendientes"),
    path("api/alertas/leer/", views.api_leer, name="api_leer"),
    path("registro/", views.registro_view, name="registro"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("perfil/", views.perfil_view, name="perfil"),
]
