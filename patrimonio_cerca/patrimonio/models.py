from datetime import timedelta

from django.db import models
from django.utils import timezone

MESES = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

DIAS_SEMANA = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]

DIAS_AVISO = [
    (0, "El mismo día"),
    (1, "1 día antes"),
    (2, "2 días antes"),
    (3, "3 días antes"),
    (7, "1 semana antes"),
]


def _fecha_corta(d):
    return f"{d.day} {MESES[d.month]}"


class Categoria(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=7, default="#1f4e8c", help_text="Color hex del marcador")

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RecursoCultural(models.Model):
    """Un sitio patrimonial o una actividad cultural (misma tabla, como en el modelo del diseño)."""

    TIPOS = [("sitio", "Sitio patrimonial"), ("actividad", "Actividad cultural")]
    VALORES = [("alto", "Alto"), ("medio", "Medio"), ("bajo", "Bajo")]

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="recursos")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    titulo = models.CharField(max_length=140)
    descripcion = models.TextField()
    latitud = models.FloatField()
    longitud = models.FloatField()
    direccion = models.CharField(max_length=200)
    comuna = models.CharField(max_length=60)
    horario = models.CharField(max_length=120, blank=True)
    req_inscripcion = models.CharField("requisito de inscripción", max_length=160, default="Sin inscripción previa")
    costo = models.PositiveIntegerField("costo (CLP)", default=0)
    acepta_pase_cultural = models.BooleanField(default=False)
    valor_patrimonial = models.CharField(max_length=5, choices=VALORES, default="medio")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    # Horario estructurado (permite el filtro "abierto ahora"); `horario` es el texto que ve el usuario
    dias_abierto = models.CharField(max_length=40, blank=True, default="lun,mar,mie,jue,vie,sab,dom",
                                    help_text="Separados por coma: lun,mar,mie,jue,vie,sab,dom")
    hora_apertura = models.TimeField(null=True, blank=True)
    hora_cierre = models.TimeField(null=True, blank=True)
    sitio_web = models.URLField(blank=True)
    # R5: cada registro declara su fuente y cuándo se actualizó
    fuente = models.CharField(max_length=200, blank=True)
    verificado = models.BooleanField(default=False, help_text="Marcar cuando se contrastó con la fuente oficial")
    fecha_actualizacion = models.DateField(auto_now=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "recurso cultural"
        verbose_name_plural = "recursos culturales"

    def __str__(self):
        return self.titulo

    @property
    def es_gratis(self):
        return self.costo == 0

    @property
    def costo_texto(self):
        return "Gratis" if self.es_gratis else "$" + f"{self.costo:,}".replace(",", ".")

    @property
    def abierto_ahora(self):
        """True/False si el sitio tiene horario estructurado; None si no se puede saber."""
        if self.tipo != "sitio" or not self.hora_apertura or not self.hora_cierre:
            return None
        ahora = timezone.localtime()
        dias = [d.strip() for d in self.dias_abierto.split(",")]
        if DIAS_SEMANA[ahora.weekday()] not in dias:
            return False
        return self.hora_apertura <= ahora.time() <= self.hora_cierre

    @property
    def estado(self):
        if self.tipo != "actividad" or not self.fecha_inicio:
            return ""
        hoy = timezone.localdate()
        fin = self.fecha_fin or self.fecha_inicio
        if hoy < self.fecha_inicio:
            return "proxima"
        if hoy <= fin:
            return "activa"
        return "finalizada"

    @property
    def estado_texto(self):
        return {"proxima": "Próxima", "activa": "En curso", "finalizada": "Finalizada"}.get(self.estado, "")

    @property
    def fechas_texto(self):
        if not self.fecha_inicio:
            return ""
        fin = self.fecha_fin or self.fecha_inicio
        if fin == self.fecha_inicio:
            return _fecha_corta(self.fecha_inicio)
        return f"{_fecha_corta(self.fecha_inicio)} al {_fecha_corta(fin)}"

    def como_dict(self, distancia=None):
        return {
            "id": self.pk,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "categoria": self.categoria.nombre,
            "color": self.categoria.color,
            "lat": self.latitud,
            "lng": self.longitud,
            "direccion": self.direccion,
            "comuna": self.comuna,
            "horario": self.horario,
            "costo": self.costo_texto,
            "gratis": self.es_gratis,
            "pase": self.acepta_pase_cultural,
            "inscripcion": self.req_inscripcion,
            "valor": self.get_valor_patrimonial_display(),
            "fechas": self.fechas_texto,
            "estado": self.estado,
            "estado_texto": self.estado_texto,
            "abierto": self.abierto_ahora,
            "web": self.sitio_web,
            "verificado": self.verificado,
            "distancia": None if distancia is None else round(distancia, 2),
        }


class Favorito(models.Model):
    """Lugar guardado en "Mi ruta". Se asocia al identificador anónimo de sesión."""

    uid = models.CharField(max_length=32, db_index=True)
    recurso = models.ForeignKey(RecursoCultural, on_delete=models.CASCADE, related_name="favoritos")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("uid", "recurso")
        ordering = ["creado"]


class Alerta(models.Model):
    """Aviso programado. Se asocia a un identificador anónimo de sesión, nunca a una ubicación."""

    uid = models.CharField(max_length=32, db_index=True)
    recurso = models.ForeignKey(RecursoCultural, on_delete=models.CASCADE, related_name="alertas")
    dias_antes = models.PositiveSmallIntegerField(choices=DIAS_AVISO, default=1)
    creada = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)

    class Meta:
        unique_together = ("uid", "recurso")
        ordering = ["recurso__fecha_inicio"]

    def __str__(self):
        return f"Alerta {self.recurso} ({self.get_dias_antes_display()})"

    @property
    def fecha_aviso(self):
        return self.recurso.fecha_inicio - timedelta(days=self.dias_antes)

    def esta_pendiente(self, hoy=None):
        """Ya corresponde avisar: llegó la fecha de aviso y la actividad no terminó."""
        hoy = hoy or timezone.localdate()
        r = self.recurso
        if self.leida or not r.fecha_inicio:
            return False
        fin = r.fecha_fin or r.fecha_inicio
        return self.fecha_aviso <= hoy <= fin

    @property
    def mensaje(self):
        r = self.recurso
        hoy = timezone.localdate()
        if r.estado == "activa":
            return f"Está en curso hasta el {_fecha_corta(r.fecha_fin or r.fecha_inicio)}."
        dias = (r.fecha_inicio - hoy).days
        if dias == 0:
            return "Empieza hoy."
        if dias == 1:
            return "Empieza mañana."
        return f"Empieza en {dias} días ({_fecha_corta(r.fecha_inicio)})."
