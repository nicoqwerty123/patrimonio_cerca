import re
import unicodedata
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from patrimonio.models import Categoria, RecursoCultural

FUENTE = "Dato de prueba. Verificar horario, costo y requisitos en el sitio oficial antes de la entrega."

CATEGORIAS = {
    "Museos": ("Museos y colecciones", "#1f4e8c"),
    "Arquitectura": ("Edificios y barrios patrimoniales", "#8a5a2b"),
    "Parques y cerros": ("Paisaje y espacios naturales", "#3e7b4f"),
    "Memoria": ("Memoria e identidad", "#7a2e57"),
    "Escénicas y música": ("Teatro, música y cine", "#b3472f"),
    "Visitas y talleres": ("Recorridos, talleres y exposiciones", "#237a86"),
}

# titulo, categoria, comuna, direccion, lat, lng, horario, costo, pase, valor, descripcion
SITIOS = [
    ("Museo Histórico Nacional", "Museos", "Santiago", "Plaza de Armas 951", -33.4376, -70.6505, "Mar a dom 10:00 a 18:00", 0, True, "alto", "Recorre la historia de Chile desde la época colonial hasta el siglo XX en un edificio histórico frente a la Plaza de Armas."),
    ("Catedral Metropolitana", "Arquitectura", "Santiago", "Plaza de Armas s/n", -33.4378, -70.6504, "Lun a dom 09:00 a 19:00", 0, False, "alto", "Templo central de la ciudad, con más de dos siglos de historia y una fachada neoclásica."),
    ("Centro Cultural La Moneda", "Visitas y talleres", "Santiago", "Plaza de la Ciudadanía 26", -33.4440, -70.6541, "Lun a dom 09:00 a 19:30", 0, True, "medio", "Espacio subterráneo bajo la Plaza de la Ciudadanía con exposiciones, cine y centro de documentación."),
    ("Museo Chileno de Arte Precolombino", "Museos", "Santiago", "Bandera 361", -33.4396, -70.6516, "Mar a dom 10:00 a 18:00", 11000, True, "alto", "Colección de arte de los pueblos originarios de América, desde los primeros asentamientos hasta la llegada de los españoles."),
    ("Museo Nacional de Bellas Artes", "Museos", "Santiago", "José Miguel de la Barra 650", -33.4363, -70.6437, "Mar a dom 10:00 a 18:30", 0, True, "alto", "Edificio de inspiración neoclásica en el Parque Forestal con arte chileno de los siglos XIX y XX."),
    ("Cerro Santa Lucía", "Parques y cerros", "Santiago", "Av. Libertador Bernardo O'Higgins s/n", -33.4403, -70.6440, "Lun a dom 09:00 a 18:30", 0, False, "alto", "Cerro isla donde Pedro de Valdivia fundó la ciudad; hoy es un paseo con terrazas, escaleras y fuentes."),
    ("Estación Mapocho", "Arquitectura", "Santiago", "Plaza de la Cultura s/n", -33.4326, -70.6537, "Lun a dom 09:00 a 20:00", 0, False, "alto", "Antigua estación de trenes con estructura metálica, hoy centro cultural."),
    ("Museo de la Memoria y los Derechos Humanos", "Memoria", "Quinta Normal", "Matucana 501", -33.4404, -70.6791, "Mar a dom 10:00 a 18:00", 0, True, "alto", "Espacio dedicado a las violaciones a los derechos humanos durante la dictadura y a la reflexión sobre la memoria."),
    ("Museo Nacional de Historia Natural", "Museos", "Quinta Normal", "Parque Quinta Normal s/n", -33.4411, -70.6812, "Mar a dom 10:00 a 17:30", 0, True, "medio", "Colecciones de ciencias naturales y antropología dentro del Parque Quinta Normal."),
    ("La Chascona", "Museos", "Providencia", "Fernando Márquez de la Plata 0192", -33.4330, -70.6346, "Mar a dom 10:00 a 18:00", 9000, True, "alto", "Casa de Pablo Neruda en Bellavista, con su colección de objetos y sus ambientes originales."),
    ("Museo de Artes Visuales (MAVI)", "Museos", "Santiago", "Lastarria 307", -33.4389, -70.6402, "Mar a dom 10:30 a 18:30", 5000, True, "medio", "Museo de arte contemporáneo en el barrio Lastarria."),
    ("Palacio Cousiño", "Arquitectura", "Santiago", "Dieciocho 438", -33.4545, -70.6567, "Mar a dom 10:00 a 15:00", 8000, False, "alto", "Residencia de la familia Cousiño del siglo XIX, con interiores originales y visitas guiadas."),
    ("Cementerio General", "Memoria", "Recoleta", "Av. Profesor Zañartu 951", -33.4141, -70.6459, "Lun a dom 08:30 a 18:00", 0, False, "alto", "Uno de los cementerios más antiguos del país, con mausoleos y tumbas de personajes de la historia de Chile."),
    ("Cerro San Cristóbal", "Parques y cerros", "Providencia", "Pío Nono 450", -33.4251, -70.6314, "Lun a dom 08:30 a 20:00", 0, False, "medio", "Gran parque urbano con miradores, senderos y el santuario de la Inmaculada Concepción."),
    ("Museo a Cielo Abierto", "Visitas y talleres", "Valparaíso", "Cerro Bellavista, Aldunate", -33.0436, -71.6341, "Todo el día", 0, False, "alto", "Más de una veintena de murales en las calles del cerro Bellavista."),
    ("La Sebastiana", "Museos", "Valparaíso", "Ferrari 692, Cerro Florida", -33.0427, -71.6286, "Mar a dom 10:30 a 18:00", 8000, True, "alto", "Casa de Pablo Neruda en Valparaíso, con vista a la bahía."),
    ("Paseo 21 de Mayo y Ascensor Artillería", "Arquitectura", "Valparaíso", "Plaza Aduana, Cerro Artillería", -33.0393, -71.6290, "Lun a dom 07:00 a 20:00", 400, False, "alto", "Ascensor histórico que sube al mirador del cerro Artillería."),
    ("Plaza Sotomayor", "Arquitectura", "Valparaíso", "Plaza Sotomayor s/n", -33.0383, -71.6277, "Todo el día", 0, False, "alto", "Plaza principal del puerto, rodeada de edificios históricos y el monumento a los héroes de Iquique."),
    ("Palacio Baburizza", "Museos", "Valparaíso", "Paseo Yugoslavo 176", -33.0408, -71.6271, "Mar a dom 10:00 a 18:00", 2000, True, "alto", "Palacio de inicios del siglo XX en el cerro Alegre, hoy Museo de Bellas Artes de Valparaíso."),
    ("Museo Marítimo Nacional", "Museos", "Valparaíso", "Paseo 21 de Mayo s/n", -33.0399, -71.6280, "Mar a dom 10:00 a 17:30", 2000, False, "medio", "Historia naval y marítima de Chile en el cerro Artillería."),
]

# titulo, categoria, comuna, direccion, lat, lng, horario, costo, pase, inscripcion, desde(dias), hasta(dias), descripcion
ACTIVIDADES = [
    ("Visita guiada por el barrio Lastarria", "Visitas y talleres", "Santiago", "Plaza Mulato Gil de Castro, Lastarria", -33.4386, -70.6396, "Sáb y dom 11:00", 0, False, "Sin inscripción previa", -1, 10, "Recorrido a pie de dos horas por el barrio, sus edificios y plazas."),
    ("Exposición fotográfica sobre Santiago antiguo", "Visitas y talleres", "Santiago", "Plaza de la Ciudadanía 26", -33.4440, -70.6541, "Todos los días 09:00 a 19:00", 3000, True, "Sin inscripción previa", -3, 20, "Fotografías históricas de la ciudad en el Centro Cultural La Moneda."),
    ("Obra de teatro en Estación Mapocho", "Escénicas y música", "Santiago", "Plaza de la Cultura s/n", -33.4326, -70.6537, "Vie y sáb 20:00", 5000, True, "Entradas en línea", 2, 9, "Función de teatro chileno contemporáneo en la sala de la antigua estación."),
    ("Taller de cerámica precolombina", "Visitas y talleres", "Santiago", "Bandera 361", -33.4396, -70.6516, "Sábado 11:00 a 13:00", 4000, True, "Inscripción previa, cupos limitados", 5, 5, "Taller práctico de modelado inspirado en piezas de la colección del museo."),
    ("Ciclo de cine documental sobre memoria", "Escénicas y música", "Quinta Normal", "Matucana 501", -33.4404, -70.6791, "Jueves 19:00", 0, False, "Sin inscripción previa", 8, 29, "Proyección de documentales chilenos seguida de conversación con el público."),
    ("Concierto de música de cámara", "Escénicas y música", "Santiago", "Plaza de Armas 951", -33.4376, -70.6505, "Domingo 12:00", 0, False, "Retiro de entradas el mismo día", 3, 3, "Concierto de cuerdas en el patio del museo."),
    ("Recorrido nocturno por el Cementerio General", "Visitas y talleres", "Recoleta", "Av. Profesor Zañartu 951", -33.4141, -70.6459, "Viernes 20:00", 6000, False, "Inscripción previa", 14, 14, "Visita guiada al atardecer por los mausoleos más antiguos."),
    ("Ascensores y cerros: recorrido guiado", "Visitas y talleres", "Valparaíso", "Plaza Aduana", -33.0393, -71.6290, "Todos los días 10:30", 0, False, "Sin inscripción previa", -2, 30, "Caminata guiada por ascensores, miradores y escaleras de los cerros Artillería y Alegre."),
    ("Muestra de arte contemporáneo porteño", "Visitas y talleres", "Valparaíso", "Paseo Yugoslavo 176", -33.0408, -71.6271, "Mar a dom 10:00 a 18:00", 2000, True, "Sin inscripción previa", 4, 40, "Obras de artistas de la región en las salas del palacio."),
    ("Función de teatro callejero en Plaza Sotomayor", "Escénicas y música", "Valparaíso", "Plaza Sotomayor s/n", -33.0383, -71.6277, "Sábado 17:00", 0, False, "Sin inscripción previa", 1, 1, "Compañías locales presentan obras breves al aire libre."),
]


DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


def parsear_horario(texto):
    """Convierte 'Mar a dom 10:00 a 18:00' o 'Todo el día' en (dias, apertura, cierre)."""
    h = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    if "todo el dia" in h:
        return ",".join(DIAS), time(0, 0), time(23, 59)
    m = re.match(r"(\w{3}) a (\w{3}) (\d\d):(\d\d) a (\d\d):(\d\d)", h)
    if not m or m.group(1) not in DIAS or m.group(2) not in DIAS:
        return None
    a, b = DIAS.index(m.group(1)), DIAS.index(m.group(2))
    return ",".join(DIAS[a:b + 1]), time(int(m.group(3)), int(m.group(4))), time(int(m.group(5)), int(m.group(6)))


class Command(BaseCommand):
    help = "Carga 20 sitios patrimoniales y 10 actividades de prueba (se puede ejecutar varias veces)."

    def handle(self, *args, **opts):
        hoy = timezone.localdate()
        cats = {}
        for nombre, (desc, color) in CATEGORIAS.items():
            cats[nombre], _ = Categoria.objects.update_or_create(
                nombre=nombre, defaults={"descripcion": desc, "color": color}
            )
        for t, c, com, d, lat, lng, h, costo, pase, valor, desc in SITIOS:
            if RecursoCultural.objects.filter(titulo=t, verificado=True).exists():
                continue  # no se pisan los datos reales ya verificados
            datos = dict(categoria=cats[c], tipo="sitio", comuna=com, direccion=d, latitud=lat, longitud=lng,
                         horario=h, costo=costo, acepta_pase_cultural=pase, valor_patrimonial=valor,
                         descripcion=desc, fuente=FUENTE)
            horario = parsear_horario(h)
            if horario:
                datos["dias_abierto"], datos["hora_apertura"], datos["hora_cierre"] = horario
            RecursoCultural.objects.update_or_create(titulo=t, defaults=datos)
        for t, c, com, d, lat, lng, h, costo, pase, insc, ini, fin, desc in ACTIVIDADES:
            if RecursoCultural.objects.filter(titulo=t, verificado=True).exists():
                continue
            RecursoCultural.objects.update_or_create(
                titulo=t,
                defaults=dict(categoria=cats[c], tipo="actividad", comuna=com, direccion=d, latitud=lat, longitud=lng,
                              horario=h, costo=costo, acepta_pase_cultural=pase, req_inscripcion=insc,
                              valor_patrimonial="medio", descripcion=desc, fuente=FUENTE,
                              fecha_inicio=hoy + timedelta(days=ini), fecha_fin=hoy + timedelta(days=fin)),
            )
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(SITIOS)} sitios y {len(ACTIVIDADES)} actividades cargados."
        ))
