import csv
import re
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from patrimonio.models import DIAS_SEMANA, Categoria, RecursoCultural

OBLIGATORIAS = ["titulo", "tipo", "categoria", "comuna", "direccion", "latitud", "longitud",
                "descripcion", "costo", "fuente"]
PALETA = ["#1f4e8c", "#8a5a2b", "#3e7b4f", "#7a2e57", "#b3472f", "#237a86", "#6b5b95", "#8c7a1f"]
SI = {"si", "sí", "s", "1", "true", "x", "yes"}


def _num(v):
    return float(str(v).strip().replace(",", "."))


def _hora(v):
    return datetime.strptime(v.strip(), "%H:%M").time()


def _fecha(v):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"fecha inválida «{v}» (usa AAAA-MM-DD)")


def _dias(v):
    v = re.sub(r"[áàä]", "a", re.sub(r"[éèë]", "e", v.strip().lower()))
    if not v or v in ("todos", "todos los dias"):
        return ",".join(DIAS_SEMANA)
    if "-" in v:
        a, b = [x.strip()[:3] for x in v.split("-", 1)]
        if a in DIAS_SEMANA and b in DIAS_SEMANA:
            return ",".join(DIAS_SEMANA[DIAS_SEMANA.index(a):DIAS_SEMANA.index(b) + 1])
    partes = [x.strip()[:3] for x in v.split(",")]
    if all(p in DIAS_SEMANA for p in partes):
        return ",".join(partes)
    raise ValueError(f"días inválidos «{v}» (usa lun,mar,mie,... o mar-dom)")


class Command(BaseCommand):
    help = "Importa lugares y actividades reales desde un CSV (ver datos/plantilla_lugares.csv)."

    def add_arguments(self, parser):
        parser.add_argument("archivo")
        parser.add_argument("--validar", action="store_true", help="Solo revisa el archivo, sin guardar")

    def handle(self, *args, **o):
        try:
            with open(o["archivo"], newline="", encoding="utf-8-sig") as f:
                primera = f.readline()
                f.seek(0)
                delim = ";" if primera.count(";") > primera.count(",") else ","
                filas = list(csv.DictReader(f, delimiter=delim))
        except FileNotFoundError:
            raise CommandError(f"No existe el archivo {o['archivo']}")

        faltan = [c for c in OBLIGATORIAS if filas and c not in filas[0]]
        if faltan:
            raise CommandError("Faltan columnas obligatorias: " + ", ".join(faltan))

        errores, listos = [], []
        for n, fila in enumerate(filas, start=2):  # la fila 1 es el encabezado
            titulo = (fila.get("titulo") or "").strip()
            try:
                vacias = [c for c in OBLIGATORIAS if not (fila.get(c) or "").strip()]
                if vacias:
                    raise ValueError("campos vacíos: " + ", ".join(vacias))
                tipo = fila["tipo"].strip().lower()
                if tipo not in ("sitio", "actividad"):
                    raise ValueError("tipo debe ser «sitio» o «actividad»")
                lat, lng = _num(fila["latitud"]), _num(fila["longitud"])
                if not (-56 <= lat <= -17 and -110 <= lng <= -66):
                    raise ValueError(f"coordenadas fuera de Chile ({lat}, {lng}); ¿invertiste latitud y longitud?")
                datos = dict(
                    tipo=tipo, comuna=fila["comuna"].strip(), direccion=fila["direccion"].strip(),
                    latitud=lat, longitud=lng, descripcion=fila["descripcion"].strip(),
                    costo=int(_num(fila["costo"])), fuente=fila["fuente"].strip(),
                    horario=(fila.get("horario") or "").strip(),
                    req_inscripcion=(fila.get("req_inscripcion") or "Sin inscripción previa").strip(),
                    acepta_pase_cultural=(fila.get("acepta_pase_cultural") or "").strip().lower() in SI,
                    valor_patrimonial=((fila.get("valor_patrimonial") or "medio").strip().lower()),
                    sitio_web=(fila.get("sitio_web") or "").strip(),
                    verificado=(fila.get("verificado") or "").strip().lower() in SI,
                    dias_abierto=_dias(fila.get("dias_abierto") or ""),
                    hora_apertura=_hora(fila["hora_apertura"]) if (fila.get("hora_apertura") or "").strip() else None,
                    hora_cierre=_hora(fila["hora_cierre"]) if (fila.get("hora_cierre") or "").strip() else None,
                )
                if datos["valor_patrimonial"] not in ("alto", "medio", "bajo"):
                    raise ValueError("valor_patrimonial debe ser alto, medio o bajo")
                if tipo == "actividad":
                    if not (fila.get("fecha_inicio") or "").strip():
                        raise ValueError("las actividades necesitan fecha_inicio")
                    datos["fecha_inicio"] = _fecha(fila["fecha_inicio"])
                    datos["fecha_fin"] = _fecha(fila["fecha_fin"]) if (fila.get("fecha_fin") or "").strip() else datos["fecha_inicio"]
                    if datos["fecha_fin"] < datos["fecha_inicio"]:
                        raise ValueError("fecha_fin es anterior a fecha_inicio")
                listos.append((titulo, fila["categoria"].strip(), datos))
            except (ValueError, KeyError) as e:
                errores.append(f"Fila {n} ({titulo or 'sin título'}): {e}")

        if errores:
            self.stdout.write(self.style.ERROR(f"{len(errores)} fila(s) con problemas, no se guardó nada:"))
            for e in errores:
                self.stdout.write("  - " + e)
            raise CommandError("Corrige el CSV y vuelve a intentarlo.")

        if o["validar"]:
            self.stdout.write(self.style.SUCCESS(f"El archivo está bien: {len(listos)} filas listas para importar."))
            return

        with transaction.atomic():
            for titulo, cat, datos in listos:
                categoria = Categoria.objects.filter(nombre=cat).first() or Categoria.objects.create(
                    nombre=cat, color=PALETA[Categoria.objects.count() % len(PALETA)]
                )
                RecursoCultural.objects.update_or_create(titulo=titulo, defaults=dict(datos, categoria=categoria))
        self.stdout.write(self.style.SUCCESS(f"Importadas {len(listos)} filas."))
