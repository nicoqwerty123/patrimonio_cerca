# Patrimonio Cerca 🏛️

Sistema web geolocalizado para la exploración, planificación de rutas y recordatorio de actividades patrimoniales y culturales en Chile.
Desarrollado con **Python, Django, Leaflet y OpenStreetMap**.

---

## 🚀 Puesta en marcha rápida (Para el equipo)

```bash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
# En Windows PowerShell:
.\venv\Scripts\Activate.ps1
# En Linux/Mac:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear y aplicar migraciones en la base de datos
python manage.py makemigrations patrimonio
python manage.py migrate

# 5. Cargar datos de prueba (20 sitios + 10 actividades iniciales)
python manage.py cargar_datos

# 6. (Opcional) Crear superusuario para el panel de administración
python manage.py createsuperuser

# 7. Iniciar el servidor de desarrollo
python manage.py runserver
```

Abrir en el navegador: 👉 **http://127.0.0.1:8000/**

---

## ✨ Funcionalidades Principales

1. **Mapa Interactivo Geolocalizado (`/`)**:
   - Detección de cercanía sin guardar la ubicación en el servidor (R8 privacidad Ley 19.628).
   - Marcadores en cluster, filtros por categoría (chips interactivos), costo cero, pase cultural y estado "abierto ahora".
   - Búsqueda por comuna o dirección.

2. **Cuentas de Usuario y Perfil (`/registro/`, `/login/`, `/perfil/`)**:
   - Registro con nombre de usuario y correo electrónico.
   - Migración transparente: si guardaste lugares de forma anónima y luego te registras, tus datos pasan a tu cuenta.
   - Panel de perfil con métricas, historial y actualización de correo para alertas.

3. **Notificaciones y Alertas por Correo (`/alertas/`)**:
   - Configuración de alertas anticipadas (el mismo día, 1, 2, 3 o 7 días antes).
   - Confirmación inmediata por email con diseño corporativo al activar una alerta.
   - Comando de consola para despachar alertas diarias: `python manage.py enviar_alertas_email`.

4. **Planificador "Mi Ruta" (`/ruta/`)**:
   - Ordenamiento inteligente de paradas para minimizar traslados.
   - Trazado automático en Google Maps.
   - Botón directo para compartir por **WhatsApp**, copiar enlace o **imprimir / guardar como PDF**.

5. **Fichas Patrimoniales Detalladas (`/lugar/<id>/`)**:
   - Reseña histórica, horarios, tarifas, acceso con pase cultural y nivel de valor patrimonial.
   - Mini-mapa enfocado y descarga de evento a calendario móvil/escritorio (`.ics`).

---

## 🧪 Pruebas Unitarias

```bash
python manage.py test
```
