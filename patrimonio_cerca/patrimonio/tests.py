from django.test import TestCase
from django.core.management import call_command

from .models import Alerta, RecursoCultural
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
