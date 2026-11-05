import math
import unicodedata

from django.db.models import Q
from django.utils import timezone

from .models import RecursoCultural

# Coordenadas de comunas para buscar sin servicios externos de geocodificación (riesgo R3).
COMUNAS = {
    "Santiago": (-33.4569, -70.6483),
    "Providencia": (-33.4314, -70.6093),
    "Ñuñoa": (-33.4569, -70.5975),
    "Las Condes": (-33.4083, -70.5675),
    "Vitacura": (-33.3860, -70.5710),
    "San Joaquín": (-33.4967, -70.6203),
    "San Miguel": (-33.4975, -70.6516),
    "Macul": (-33.4903, -70.5994),
    "Recoleta": (-33.4066, -70.6406),
    "Independencia": (-33.4215, -70.6633),
    "Quinta Normal": (-33.4378, -70.6828),
    "Estación Central": (-33.4547, -70.6790),
    "La Florida": (-33.5227, -70.5985),
    "Maipú": (-33.5105, -70.7575),
    "Valparaíso": (-33.0472, -71.6127),
    "Viña del Mar": (-33.0153, -71.5500),
}


def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def buscar_lugar(texto):
    """Devuelve (nombre, lat, lng) para una comuna, dirección o nombre de sitio; None si no hay."""
    q = normalizar(texto)
    if not q:
        return None
    for nombre, (lat, lng) in COMUNAS.items():
        if normalizar(nombre) == q:
            return nombre, lat, lng
    for nombre, (lat, lng) in COMUNAS.items():
        if q in normalizar(nombre):
            return nombre, lat, lng
    for r in RecursoCultural.objects.all():
        if q in normalizar(r.direccion) or q in normalizar(r.titulo):
            return r.titulo, r.latitud, r.longitud
    return None


def recursos_cercanos(lat, lng, radio_km, gratis=False, pase=False, categorias=None, tipo=None,
                      abierto=False, orden="distancia"):
    """Lista de (recurso, distancia_km) dentro del radio."""
    hoy = timezone.localdate()
    dlat = radio_km / 111.0
    dlng = radio_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    qs = RecursoCultural.objects.select_related("categoria").filter(
        latitud__range=(lat - dlat, lat + dlat),
        longitud__range=(lng - dlng, lng + dlng),
    )
    qs = qs.filter(Q(tipo="sitio") | Q(fecha_fin__gte=hoy))
    if gratis:
        qs = qs.filter(costo=0)
    if pase:
        qs = qs.filter(acepta_pase_cultural=True)
    if categorias:
        qs = qs.filter(categoria_id__in=categorias)
    if tipo in ("sitio", "actividad"):
        qs = qs.filter(tipo=tipo)
    res = [(r, haversine_km(lat, lng, r.latitud, r.longitud)) for r in qs]
    res = [(r, d) for r, d in res if d <= radio_km]
    if abierto:
        res = [(r, d) for r, d in res if r.abierto_ahora is True or r.estado == "activa"]
    if orden == "nombre":
        res.sort(key=lambda x: normalizar(x[0].titulo))
    elif orden == "costo":
        res.sort(key=lambda x: (x[0].costo, x[1]))
    else:
        res.sort(key=lambda x: x[1])
    return res


def ordenar_ruta(recursos, origen=None):
    """Ordena paradas con el vecino más cercano. Devuelve [(recurso, tramo_km)] (tramo None en la primera sin origen)."""
    pendientes = list(recursos)
    if not pendientes:
        return []
    salida = []
    if origen is None:
        primero = pendientes.pop(0)
        salida.append((primero, None))
        actual = (primero.latitud, primero.longitud)
    else:
        actual = origen
    while pendientes:
        sig = min(pendientes, key=lambda r: haversine_km(actual[0], actual[1], r.latitud, r.longitud))
        salida.append((sig, haversine_km(actual[0], actual[1], sig.latitud, sig.longitud)))
        pendientes.remove(sig)
        actual = (sig.latitud, sig.longitud)
    return salida
