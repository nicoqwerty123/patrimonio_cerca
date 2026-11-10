import uuid
from datetime import timedelta
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .emails import (
    enviar_correo_bienvenida_async,
    enviar_correo_confirmacion_alerta_async,
    enviar_correo_verificacion_async,
)
from .forms import (
    FormularioLogin,
    FormularioNuevaPassword,
    FormularioRecuperarPassword,
    FormularioRegistro,
)
from .models import DIAS_AVISO, Alerta, Categoria, Favorito, RecursoCultural, VerificacionEmail
from .utils import COMUNAS, buscar_lugar, haversine_km, ordenar_ruta, recursos_cercanos

CENTRO_DEFECTO = (-33.4489, -70.6693)  # Santiago centro
RADIO_DEFECTO = 5.0
MAX_PARADAS = 10  # límite de Google Maps (origen + paradas + destino)


def _uid(request):
    if request.user.is_authenticated:
        uid = f"usr_{request.user.pk}"
        request.session["uid"] = uid
        return uid
    if "uid" not in request.session:
        request.session["uid"] = uuid.uuid4().hex
    return request.session["uid"]


def _migrar_sesion(old_uid, new_uid):
    """Traspasa favoritos y alertas anónimas a la cuenta del usuario logueado."""
    if not old_uid or old_uid == new_uid:
        return
    for fav in Favorito.objects.filter(uid=old_uid):
        if not Favorito.objects.filter(uid=new_uid, recurso=fav.recurso).exists():
            fav.uid = new_uid
            fav.save()
        else:
            fav.delete()
    for al in Alerta.objects.filter(uid=old_uid):
        if not Alerta.objects.filter(uid=new_uid, recurso=al.recurso).exists():
            al.uid = new_uid
            al.save()
        else:
            al.delete()


def _num(valor, defecto):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _favoritos(request):
    uid = request.session.get("uid")
    if not uid:
        return set()
    return set(Favorito.objects.filter(uid=uid).values_list("recurso_id", flat=True))


def _volver(request, defecto):
    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(defecto)


# ---------- Funcionalidad 1: mapa interactivo ----------

def mapa(request):
    return render(request, "patrimonio/mapa.html", {
        "categorias": Categoria.objects.all(),
        "comunas": list(COMUNAS.keys()),
        # Sugerencias del buscador: comunas + nombres de sitios, para que se
        # descubra que tambien se puede buscar por lugar (ej: "Precolombino").
        "sitios": list(
            RecursoCultural.objects.filter(tipo="sitio")
            .order_by("titulo")
            .values_list("titulo", flat=True)
        ),
        "radio": request.session.get("radio", RADIO_DEFECTO),
        "fav_url": reverse("fav_toggle", args=[0]),
    })


@require_GET
def api_recursos(request):
    g = request.GET
    lat = _num(g.get("lat"), CENTRO_DEFECTO[0])
    lng = _num(g.get("lng"), CENTRO_DEFECTO[1])
    radio = min(max(_num(g.get("radio"), RADIO_DEFECTO), 0.5), 30)
    categorias = [int(x) for x in g.get("categorias", "").split(",") if x.isdigit()]
    res = recursos_cercanos(
        lat, lng, radio,
        gratis=g.get("gratis") == "1",
        pase=g.get("pase") == "1",
        categorias=categorias,
        tipo=g.get("tipo"),
        abierto=g.get("abierto") == "1",
        orden=g.get("orden", "distancia"),
    )
    favs = _favoritos(request)
    return JsonResponse({
        "radio": radio,
        "resultados": [
            dict(r.como_dict(d), url=reverse("detalle", args=[r.pk]), fav=r.pk in favs) for r, d in res
        ],
    })


@require_GET
def api_buscar(request):
    hallado = buscar_lugar(request.GET.get("q", ""))
    if not hallado:
        return JsonResponse({"ok": False})
    nombre, lat, lng = hallado
    return JsonResponse({"ok": True, "nombre": nombre, "lat": lat, "lng": lng})


@require_POST
def api_ubicacion(request):
    """Guarda la posición solo en la cookie de sesión firmada (no en la base de datos)."""
    _uid(request)
    if request.POST.get("borrar"):
        request.session.pop("pos", None)
    else:
        lat, lng = _num(request.POST.get("lat"), None), _num(request.POST.get("lng"), None)
        if lat is not None and lng is not None:
            request.session["pos"] = [lat, lng]
    radio = _num(request.POST.get("radio"), None)
    if radio:
        request.session["radio"] = min(max(radio, 0.5), 30)
    return JsonResponse({"ok": True})


# ---------- Funcionalidad 3: ficha detallada ----------

def detalle(request, pk):
    r = get_object_or_404(RecursoCultural.objects.select_related("categoria"), pk=pk)
    uid = _uid(request)
    alerta = Alerta.objects.filter(uid=uid, recurso=r).first()
    return render(request, "patrimonio/detalle.html", {
        "r": r,
        "alerta": alerta,
        "es_fav": r.pk in _favoritos(request),
        "dias_aviso": DIAS_AVISO,
        "dias_sel": alerta.dias_antes if alerta else 1,
        "ruta_url": f"https://www.google.com/maps/dir/?api=1&destination={r.latitud},{r.longitud}",
        "puede_alertar": r.tipo == "actividad" and r.estado != "finalizada",
    })


@require_GET
def calendario(request, pk):
    """Descarga un .ics para agregar la actividad al calendario del teléfono o del computador."""
    r = get_object_or_404(RecursoCultural, pk=pk, tipo="actividad")

    def esc(t):
        return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    inicio = r.fecha_inicio
    fin = (r.fecha_fin or inicio) + timedelta(days=1)
    lineas = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Patrimonio cerca//ES", "BEGIN:VEVENT",
        f"UID:actividad-{r.pk}@patrimonio-cerca",
        f"DTSTAMP:{timezone.now():%Y%m%dT%H%M%SZ}",
        f"DTSTART;VALUE=DATE:{inicio:%Y%m%d}",
        f"DTEND;VALUE=DATE:{fin:%Y%m%d}",
        f"SUMMARY:{esc(r.titulo)}",
        f"LOCATION:{esc(r.direccion + ', ' + r.comuna)}",
        f"DESCRIPTION:{esc(r.descripcion + ' Horario: ' + r.horario)}",
        "END:VEVENT", "END:VCALENDAR",
    ]
    resp = HttpResponse("\r\n".join(lineas) + "\r\n", content_type="text/calendar; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="actividad-{r.pk}.ics"'
    return resp


# ---------- Mi ruta (favoritos) ----------

@require_POST
def fav_toggle(request, pk):
    r = get_object_or_404(RecursoCultural, pk=pk)
    uid = _uid(request)
    _, creado = Favorito.objects.get_or_create(uid=uid, recurso=r)
    if not creado:
        Favorito.objects.filter(uid=uid, recurso=r).delete()
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"fav": creado, "total": Favorito.objects.filter(uid=uid).count()})
    messages.success(request, "Agregado a tu ruta." if creado else "Quitado de tu ruta.")
    return _volver(request, reverse("detalle", args=[pk]))


def mi_ruta(request):
    uid = _uid(request)
    recursos = [f.recurso for f in Favorito.objects.filter(uid=uid).select_related("recurso__categoria")]
    pos = request.session.get("pos")
    orden = ordenar_ruta(recursos, tuple(pos) if pos else None)
    paradas = orden[:MAX_PARADAS]
    total = sum(t for _, t in paradas if t)
    url = None
    if paradas:
        destino = paradas[-1][0]
        url = f"https://www.google.com/maps/dir/?api=1&destination={destino.latitud},{destino.longitud}&travelmode=walking"
        intermedias = [f"{r.latitud},{r.longitud}" for r, _ in paradas[:-1]]
        if intermedias:
            url += "&waypoints=" + quote("|".join(intermedias), safe=",")
    return render(request, "patrimonio/mi_ruta.html", {
        "paradas": [(i, r, t) for i, (r, t) in enumerate(paradas, start=1)],
        "total": total,
        "con_origen": bool(pos),
        "excede": len(orden) > MAX_PARADAS,
        "max_paradas": MAX_PARADAS,
        "url_google": url,
    })


# ---------- Funcionalidad 2: alertas y bandeja ----------

def alertas(request):
    uid = _uid(request)
    pos = request.session.get("pos")
    radio = request.session.get("radio", RADIO_DEFECTO)
    hoy = timezone.localdate()

    actividades = RecursoCultural.objects.select_related("categoria").filter(
        tipo="actividad", fecha_fin__gte=hoy
    ).order_by("fecha_inicio")
    items = []
    for a in actividades:
        d = haversine_km(pos[0], pos[1], a.latitud, a.longitud) if pos else None
        if pos and d > radio:
            continue
        items.append((a, d))

    mis_alertas = list(Alerta.objects.filter(uid=uid).select_related("recurso__categoria"))
    return render(request, "patrimonio/alertas.html", {
        "activas": [x for x in items if x[0].estado == "activa"],
        "proximas": [x for x in items if x[0].estado == "proxima"],
        "mis_alertas": mis_alertas,
        "pendientes": [a for a in mis_alertas if a.esta_pendiente(hoy)],
        "con_ubicacion": bool(pos),
        "radio": radio,
        "dias_aviso": DIAS_AVISO,
        "ids_con_alerta": {a.recurso_id for a in mis_alertas},
    })


@require_POST
def alerta_guardar(request, pk):
    r = get_object_or_404(RecursoCultural, pk=pk, tipo="actividad")
    try:
        dias = int(request.POST.get("dias_antes", 1))
    except ValueError:
        dias = 1
    if dias not in dict(DIAS_AVISO):
        dias = 1
    alerta, _ = Alerta.objects.update_or_create(
        uid=_uid(request), recurso=r, defaults={"dias_antes": dias, "leida": False}
    )

    # Notificación por correo electrónico si el usuario tiene email registrado.
    # Se despacha en segundo plano para no demorar la respuesta web.
    email_dest = request.user.email if request.user.is_authenticated and request.user.email else request.POST.get("email")
    if email_dest:
        base_url = request.build_absolute_uri("/")[:-1]
        enviar_correo_confirmacion_alerta_async(email_dest, r, dias, alerta.fecha_aviso, base_url=base_url)
        messages.success(request, f"Alerta guardada para «{r.titulo}». Te enviaremos la confirmación a {email_dest}.")
    else:
        messages.success(request, f"Alerta guardada para «{r.titulo}».")

    return _volver(request, reverse("detalle", args=[pk]))


@require_POST
def alerta_eliminar(request, pk):
    Alerta.objects.filter(uid=_uid(request), recurso_id=pk).delete()
    messages.success(request, "Alerta eliminada.")
    return _volver(request, reverse("alertas"))


@require_GET
def api_pendientes(request):
    uid = request.session.get("uid")
    if not uid:
        return JsonResponse({"pendientes": []})
    pend = [
        {"id": a.pk, "titulo": a.recurso.titulo, "mensaje": a.mensaje, "url": reverse("detalle", args=[a.recurso_id])}
        for a in Alerta.objects.filter(uid=uid, leida=False).select_related("recurso")
        if a.esta_pendiente()
    ]
    return JsonResponse({"pendientes": pend})


@require_POST
def api_leer(request):
    uid = _uid(request)
    qs = Alerta.objects.filter(uid=uid)
    if request.POST.get("id"):
        qs = qs.filter(pk=request.POST["id"])
    qs.update(leida=True)
    return JsonResponse({"ok": True})


# ---------- Autenticación de usuarios ----------

def registro_view(request):
    if request.user.is_authenticated:
        return redirect("mapa")
    anon_uid = request.session.get("uid")
    if request.method == "POST":
        form = FormularioRegistro(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            new_uid = f"usr_{user.pk}"
            request.session["uid"] = new_uid
            _migrar_sesion(anon_uid, new_uid)

            # Envío de correo de bienvenida + verificación en segundo plano
            if user.email:
                base_url = request.build_absolute_uri("/")[:-1]
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                enviar_correo_bienvenida_async(user, base_url=base_url, uidb64=uid, token=token)

            messages.success(request, f"¡Bienvenido/a, {user.username}! Tu cuenta ha sido creada exitosamente. Te enviamos un correo a {user.email}.")
            return redirect("mapa")
    else:
        form = FormularioRegistro()
    return render(request, "patrimonio/registro.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("mapa")
    anon_uid = request.session.get("uid")
    next_url = request.GET.get("next") or request.POST.get("next") or reverse("mapa")
    if request.method == "POST":
        form = FormularioLogin(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            new_uid = f"usr_{user.pk}"
            request.session["uid"] = new_uid
            _migrar_sesion(anon_uid, new_uid)
            messages.success(request, f"Hola de nuevo, {user.username}.")
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("mapa")
    else:
        form = FormularioLogin(request)
    return render(request, "patrimonio/login.html", {"form": form, "next": next_url})


def logout_view(request):
    auth_logout(request)
    request.session.flush()
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("mapa")


def perfil_view(request):
    """Panel de perfil de usuario con estadísticas y actualización de correo."""
    if not request.user.is_authenticated:
        messages.info(request, "Debes iniciar sesión para ver tu perfil.")
        return redirect("login")

    uid = f"usr_{request.user.pk}"
    mis_favoritos = Favorito.objects.filter(uid=uid).select_related("recurso__categoria")
    mis_alertas = Alerta.objects.filter(uid=uid).select_related("recurso")

    if request.method == "POST":
        nuevo_email = request.POST.get("email", "").strip()
        cambio = nuevo_email and nuevo_email != request.user.email
        request.user.email = nuevo_email
        request.user.save()
        if cambio:
            # El correo nuevo queda pendiente de verificación: se envía otro enlace.
            VerificacionEmail.objects.update_or_create(
                user=request.user, defaults={"verificado": False}
            )
            enlace_uid = urlsafe_base64_encode(force_bytes(request.user.pk))
            token = default_token_generator.make_token(request.user)
            enviar_correo_verificacion_async(
                request.user, enlace_uid, token,
                base_url=request.build_absolute_uri("/")[:-1],
            )
            messages.success(
                request,
                f"Correo actualizado. Enviamos un enlace de verificación a {nuevo_email}.",
            )
        else:
            messages.success(request, "Tu correo electrónico ha sido actualizado.")
        return redirect("perfil")

    verificacion = VerificacionEmail.objects.filter(user=request.user).first()
    return render(request, "patrimonio/perfil.html", {
        "usuario": request.user,
        "total_favoritos": mis_favoritos.count(),
        "total_alertas": mis_alertas.count(),
        "mis_favoritos": mis_favoritos[:5],
        "mis_alertas": mis_alertas,
        "verificado": bool(verificacion and verificacion.verificado),
    })


# ---------- Verificación de correo ----------

def verificar_email(request, uidb64, token):
    """Confirma el correo siguiendo el enlace incluido en el correo de bienvenida."""
    user = None
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        verif, creado = VerificacionEmail.objects.get_or_create(user=user)
        if verif.verificado:
            messages.info(request, f"Tu correo {user.email} ya estaba verificado: todo en orden.")
        else:
            verif.verificado = True
            verif.save()
            messages.success(request, f"¡Listo! Verificamos {user.email}; tu cuenta quedó completamente activa.")
        return redirect("perfil" if request.user.is_authenticated else "login")

    messages.error(
        request,
        "El enlace de verificación no es válido o ya expiró (por seguridad, duran 3 días). "
        "Puedes pedir uno nuevo desde tu perfil.",
    )
    return redirect("login")


@require_POST
def reenviar_verificacion(request):
    """Vuelve a enviar el enlace de verificación al correo del usuario logueado."""
    if not request.user.is_authenticated:
        return redirect("login")
    user = request.user
    if not user.email:
        messages.error(request, "Primero guarda un correo en tu perfil para poder verificarlo.")
        return redirect("perfil")

    verif = VerificacionEmail.objects.filter(user=user).first()
    if verif and verif.verificado:
        messages.info(request, "Tu correo ya está verificado; no necesitas otro enlace.")
        return redirect("perfil")

    enlace_uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    enviar_correo_verificacion_async(
        user, enlace_uid, token, base_url=request.build_absolute_uri("/")[:-1]
    )
    messages.success(request, f"Enviamos un nuevo enlace de verificación a {user.email}.")
    return redirect("perfil")


# ---------- Recuperación de contraseña ----------

class RecuperarPasswordView(auth_views.PasswordResetView):
    """Pide el correo y envía el enlace para crear una contraseña nueva."""
    template_name = "patrimonio/password/recuperar.html"
    form_class = FormularioRecuperarPassword
    subject_template_name = "patrimonio/password/asunto.txt"
    email_template_name = "patrimonio/password/mensaje.txt"
    html_email_template_name = "patrimonio/password/mensaje.html"
    success_url = reverse_lazy("password_enviada")


class RecuperarEnviadaView(auth_views.PasswordResetDoneView):
    template_name = "patrimonio/password/enviada.html"


class RecuperarConfirmarView(auth_views.PasswordResetConfirmView):
    """Formulario de nueva contraseña (mismas reglas que el registro)."""
    template_name = "patrimonio/password/nueva.html"
    form_class = FormularioNuevaPassword
    success_url = reverse_lazy("password_lista")


class RecuperarListaView(auth_views.PasswordResetCompleteView):
    template_name = "patrimonio/password/listo.html"
