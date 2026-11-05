# Cómo cargar información real

Los datos que trae `cargar_datos` son **de prueba** (horarios y costos aproximados). Para la entrega hay que reemplazarlos por datos contrastados con la fuente oficial. Esto cubre el riesgo R5 de la matriz (datos desactualizados) y la regla de la plantilla de carga con campos obligatorios.

## 1. Qué buscar y dónde

| Dato | Fuente recomendada |
|---|---|
| Horario, costo, requisito de inscripción, sitio web | Sitio oficial del museo, centro cultural o municipalidad (no blogs ni redes de terceros) |
| Museos estatales: horarios y tarifas | Portal de la Subdirección Nacional de Museos (museosdechile.gob.cl) |
| Valor patrimonial (¿Monumento Nacional? ¿Zona Típica?) | Consejo de Monumentos Nacionales (monumentos.gob.cl). Alto = declarado Monumento Nacional o Patrimonio Mundial; medio = relevante sin declaratoria; bajo = otro. Definan el criterio en el equipo y escríbanlo en el informe |
| Actividades y fechas | Agenda de cada institución, cultura.gob.cl, municipalidades y Día de los Patrimonios |
| Coordenadas | Google Maps: clic derecho sobre el punto exacto y copiar la primera línea (lat, lng). Primero va la latitud (negativa en Chile) |
| Pase cultural | Confirmen qué es exactamente y qué lugares lo aceptan con la institución o la fuente que ya citaron; si no hay confirmación, escriban `no` |

## 2. Reglas para el equipo

1. Una persona por lugar busca el dato y **otra lo revisa** (R5 pide validar por pares una muestra de 10 fichas).
2. Escriban las descripciones con sus propias palabras (2 o 3 frases). No copien textos ni fotos: los derechos de autor están en su Entregable 1.
3. En `fuente` pongan el nombre del sitio y la fecha de consulta, por ejemplo: `Sitio oficial del museo, consultado 2026-11-10`.
4. `verificado` = `si` solo cuando la segunda persona confirmó los datos en la fuente. Mientras sea `no`, la ficha avisa «Información en revisión».
5. Las actividades vencen: revisen fechas la semana de la demo.

## 3. Cómo se carga

1. Abran `datos/plantilla_lugares.csv` en Excel o Google Sheets y respeten las columnas. No cambien los nombres del encabezado.
2. Una fila por lugar o actividad. Para actividades completen `fecha_inicio` y `fecha_fin` (AAAA-MM-DD) y dejen vacíos los horarios estructurados.
3. Guarden como **CSV UTF-8** en `datos/lugares.csv`.
4. Revisen sin guardar nada:
   `python manage.py importar_csv datos/lugares.csv --validar`
   Si hay errores, dice la fila y el motivo (campo vacío, coordenadas fuera de Chile, fecha mal escrita...).
5. Cuando no haya errores, importen:
   `python manage.py importar_csv datos/lugares.csv`
6. Se pueden repetir las importaciones: si el título ya existe, se actualiza.

## 4. Columnas

`titulo, tipo (sitio|actividad), categoria, comuna, direccion, latitud, longitud, descripcion, dias_abierto (mar-dom o lun,mar,...), hora_apertura (10:00), hora_cierre (18:00), horario (texto para el usuario), costo (CLP, 0 = gratis), acepta_pase_cultural (si|no), req_inscripcion, valor_patrimonial (alto|medio|bajo), fecha_inicio, fecha_fin, sitio_web, fuente, verificado (si|no)`

`dias_abierto`, `hora_apertura` y `hora_cierre` alimentan el filtro «Abierto ahora». Si se dejan vacíos, el sitio simplemente no muestra ese estado.

## 5. Dejar de usar los datos de prueba

Los registros de prueba con `verificado = no` se pueden borrar desde `/admin/` (filtro «Verificado» a la derecha) cuando ya cargaron los reales. `cargar_datos` nunca pisa un registro marcado como verificado.
