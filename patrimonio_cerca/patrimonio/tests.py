from django.test import TestCase
from django.core.management import call_command

from .models import Alerta, RecursoCultural, VerificacionEmail
from .utils import buscar_lugar, haversine_km, normalizar, recursos_cercanos


class PatrimonioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos", verbosity=0)

    def test_carga_minima(self):
        self.assertGreaterEqual(RecursoCultural.objects.filter(tipo="sitio").count(), 20)
        self.assertGreaterEqual(RecursoCultural.objects.filter(tipo="actividad").count(), 10)

    def test_haversine(self):
        self.assertAlmostEqual(haversine_km(-33.45, -70.66, -33.45, -70.66), 0, places=3)
        self.assertTrue(90 < haversine_km(-33.45, -70.66, -33.04, -71.61) < 110)

    def test_radio_y_filtros(self):
        cerca = recursos_cercanos(-33.4376, -70.6505, 1)
        self.assertTrue(all(d <= 1 for _, d in cerca))
        gratis = recursos_cercanos(-33.4376, -70.6505, 5, gratis=True)
        self.assertTrue(all(r.es_gratis for r, _ in gratis))
        self.assertEqual(recursos_cercanos(-33.4376, -70.6505, 5, categorias=[999999]), [])

    def test_buscar_comuna(self):
        self.assertEqual(buscar_lugar("nunoa")[0], "Ñuñoa")
        self.assertIsNone(buscar_lugar("zzzz inexistente"))

    def test_api_sin_resultados(self):
        r = self.client.get("/api/recursos/?lat=-20&lng=-70&radio=2")
        self.assertEqual(r.json()["resultados"], [])

    def test_alerta_y_pendientes(self):
        act = RecursoCultural.objects.filter(tipo="actividad", titulo__contains="Lastarria").first()
        self.client.get("/")  # crea sesión
        self.client.post("/api/ubicacion/", {"lat": -33.44, "lng": -70.65})
        resp = self.client.post(f"/alertas/{act.pk}/guardar/", {"dias_antes": 3})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Alerta.objects.count(), 1)
        pend = self.client.get("/api/alertas/pendientes/").json()["pendientes"]
        self.assertEqual(len(pend), 1)  # actividad ya en curso: corresponde avisar
        self.assertEqual(self.client.get("/alertas/").status_code, 200)
        self.assertEqual(self.client.get(f"/lugar/{act.pk}/").status_code, 200)


class RegistroTests(TestCase):
    """El registro debe crear la cuenta y responder de inmediato (correo en segundo plano)."""

    def test_registro_crea_usuario_y_redirige(self):
        from django.contrib.auth.models import User

        datos = {
            "username": "visitante2026",
            "email": "visitante2026@example.com",
            "password1": "Patrimonio#2026",
            "password2": "Patrimonio#2026",
        }
        resp = self.client.post("/registro/", datos)
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="visitante2026")
        self.assertEqual(user.email, "visitante2026@example.com")
        self.assertTrue(user.check_password("Patrimonio#2026"))

    def test_registro_rechaza_correo_duplicado(self):
        from django.contrib.auth.models import User

        User.objects.create_user("previo", "ya_usado@example.com", "Previo#2026")
        datos = {
            "username": "otro_usuario",
            "email": "YA_USADO@example.com",
            "password1": "Patrimonio#2026",
            "password2": "Patrimonio#2026",
        }
        resp = self.client.post("/registro/", datos)
        self.assertEqual(resp.status_code, 200)  # vuelve a mostrar el formulario
        self.assertIn(b"Ya existe una cuenta registrada", resp.content)


class PaginasYBusquedaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos", verbosity=0)

    def test_404_personalizada(self):
        resp = self.client.get("/pagina-que-no-existe/")
        self.assertContains(resp, "No encontramos esta página", status_code=404)

    def test_mapa_sugiere_sitios_en_el_buscador(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        # Los sitios aparecen como sugerencias del datalist del buscador
        self.assertContains(resp, "Museo Chileno de Arte Precolombino")

    def test_buscar_por_nombre_de_sitio(self):
        hallado = buscar_lugar("precolombino")
        self.assertIsNotNone(hallado)
        self.assertEqual(hallado[0], "Museo Chileno de Arte Precolombino")


class NuevasFuncionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos", verbosity=0)

    def test_favoritos_y_ruta(self):
        a, b = RecursoCultural.objects.filter(tipo="sitio")[:2]
        self.client.post(f"/ruta/{a.pk}/guardar/")
        resp = self.client.post(f"/ruta/{b.pk}/guardar/", HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(resp.json()["total"], 2)
        pagina = self.client.get("/ruta/")
        self.assertEqual(pagina.status_code, 200)
        self.assertIn("google.com/maps/dir", pagina.context["url_google"])
        resp = self.client.post(f"/ruta/{b.pk}/guardar/", HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(resp.json()["total"], 1)

    def test_calendario_ics(self):
        act = RecursoCultural.objects.filter(tipo="actividad").first()
        resp = self.client.get(f"/lugar/{act.pk}/calendario.ics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"BEGIN:VEVENT", resp.content)

    def test_filtros_abierto_y_orden(self):
        res = recursos_cercanos(-33.4376, -70.6505, 5, orden="nombre")
        nombres = [r.titulo for r, _ in res]
        self.assertEqual(nombres, sorted(nombres, key=normalizar))
        for r, _ in recursos_cercanos(-33.4376, -70.6505, 5, abierto=True):
            self.assertTrue(r.abierto_ahora is True or r.estado == "activa")

    def test_importar_csv_valida(self):
        from io import StringIO
        call_command("importar_csv", "datos/plantilla_lugares.csv", "--validar", stdout=StringIO())


class VerificacionEmailTests(TestCase):
    """El enlace de verificación incluido en el correo de bienvenida."""

    def _enlace(self, user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        return (
            urlsafe_base64_encode(force_bytes(user.pk)),
            default_token_generator.make_token(user),
        )

    def test_verificar_correo_valido(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user("catalina", "catalina@example.com", "Clave#2026")
        uidb64, token = self._enlace(user)
        resp = self.client.get(f"/cuenta/verificar/{uidb64}/{token}/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(VerificacionEmail.objects.get(user=user).verificado)

        # Un segundo uso del mismo enlace avisa que ya estaba verificado.
        resp = self.client.get(f"/cuenta/verificar/{uidb64}/{token}/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(VerificacionEmail.objects.get(user=user).verificado)

    def test_enlace_invalido_no_verifica(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user("rodrigo", "rodri@example.com", "Clave#2026")
        resp = self.client.get("/cuenta/verificar/no-existe/token-falso/")
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            VerificacionEmail.objects.filter(user=user, verificado=True).exists()
        )

    def test_reenvio_requiere_sesion(self):
        resp = self.client.post("/cuenta/verificar/reenviar/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/login/")

    def test_cambiar_correo_lo_deja_pendiente(self):
        from django.test import Client
        from django.contrib.auth.models import User

        user = User.objects.create_user("marcela", "marcela@example.com", "Clave#2026")
        VerificacionEmail.objects.create(user=user, verificado=True)
        client = Client()
        client.force_login(user)
        resp = client.post("/perfil/", {"email": "marcela.nueva@example.com"})
        self.assertEqual(resp.status_code, 302)
        verif = VerificacionEmail.objects.get(user=user)
        self.assertFalse(verif.verificado)
        user.refresh_from_db()
        self.assertEqual(user.email, "marcela.nueva@example.com")


class RecuperarPasswordTests(TestCase):
    """Flujo completo: pedir el enlace, seguirlo y dejar una contraseña nueva."""

    def test_flujo_completo(self):
        from django.contrib.auth.models import User
        from django.core import mail

        user = User.objects.create_user("beatriz", "beatriz@example.com", "Vieja#2026")

        # 1. Pide el enlace
        resp = self.client.post("/password/recuperar/", {"email": "beatriz@example.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/password/enviada/")
        self.assertEqual(len(mail.outbox), 1)
        cuerpo = mail.outbox[0].body
        self.assertIn("/password/restablecer/", cuerpo)

        # 2. Extrae uid y token del enlace del correo
        enlace = [l for l in cuerpo.splitlines() if "/password/restablecer/" in l][0]
        partes = enlace.strip("/").split("/")
        uidb64, token = partes[-2], partes[-1]

        # 3. Abre el formulario de nueva contraseña. Desde Django 4.1 el enlace
        #    del correo redirige a una URL interna (set-password) que guarda el
        #    token en la sesión para no filtrarlo en el Referer.
        resp = self.client.get(f"/password/restablecer/{uidb64}/{token}/")
        self.assertEqual(resp.status_code, 302)
        url_formulario = resp.url

        # 4. Guarda una contraseña que cumple las reglas del registro
        resp = self.client.post(
            url_formulario,
            {"new_password1": "Nueva#2026", "new_password2": "Nueva#2026"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/password/listo/")
        user.refresh_from_db()
        self.assertTrue(user.check_password("Nueva#2026"))

        # La contraseña vieja ya no sirve
        self.assertFalse(user.check_password("Vieja#2026"))

    def test_password_debil_rechazada(self):
        from django.contrib.auth.models import User
        from django.core import mail

        user = User.objects.create_user("claudio", "claudio@example.com", "Vieja#2026")
        self.client.post("/password/recuperar/", {"email": "claudio@example.com"})
        cuerpo = mail.outbox[0].body
        enlace = [l for l in cuerpo.splitlines() if "/password/restablecer/" in l][0]
        partes = enlace.strip("/").split("/")
        uidb64, token = partes[-2], partes[-1]

        # El enlace del correo redirige primero a la URL interna del formulario
        resp = self.client.get(f"/password/restablecer/{uidb64}/{token}/")
        self.assertEqual(resp.status_code, 302)
        resp = self.client.post(
            resp.url,
            {"new_password1": "sinmayuscula1!", "new_password2": "sinmayuscula1!"},
        )
        self.assertEqual(resp.status_code, 200)  # vuelve a mostrar el formulario
        self.assertContains(resp, "menos una letra mayúscula")
        user.refresh_from_db()
        self.assertTrue(user.check_password("Vieja#2026"))

    def test_correo_desconocido_no_revela_nada(self):
        resp = self.client.post("/password/recuperar/", {"email": "nadie@example.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/password/enviada/")  # misma respuesta neutral

    def test_login_muestra_enlace_recuperacion(self):
        resp = self.client.get("/login/")
        self.assertContains(resp, "¿Olvidaste tu contraseña?")


class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos", verbosity=0)

    def test_sitemap_incluye_lugares(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        sitio = RecursoCultural.objects.first()
        self.assertContains(resp, f"/lugar/{sitio.pk}/</loc>")
        self.assertContains(resp, "/alertas/")

    def test_robots_txt(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn(b"Sitemap: http://testserver/sitemap.xml", resp.content)

    def test_meta_open_graph_en_portada_y_ficha(self):
        portada = self.client.get("/")
        self.assertContains(portada, 'property="og:image"')
        self.assertContains(portada, "tarjeta-compartir.png")
        sitio = RecursoCultural.objects.filter(tipo="sitio").first()
        ficha = self.client.get(f"/lugar/{sitio.pk}/")
        self.assertContains(ficha, f'<meta property="og:title" content="{sitio.titulo} · Patrimonio Cerca">')
