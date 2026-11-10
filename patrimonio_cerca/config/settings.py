import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga de variables de entorno desde archivo .env local si existe
def _cargar_env():
    for ruta in [BASE_DIR / ".env", BASE_DIR.parent / ".env"]:
        if ruta.exists():
            with open(ruta, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if linea and not linea.startswith("#") and "=" in linea:
                        k, v = linea.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip("'\""))

_cargar_env()


def _db_desde_url(url):
    """Convierte una URL de PostgreSQL (Neon, Supabase, Render) a la config de Django.

    Ejemplo: postgres://usuario:clave@host:5432/basedatos?sslmode=require
    Sin DATABASE_URL definido se usa SQLite local, para desarrollar sin nada extra.
    """
    from urllib.parse import parse_qs, unquote, urlparse

    p = urlparse(url)
    if p.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured(
            f"DATABASE_URL solo soporta postgres/postgresql (llego: {p.scheme or 'vacio'})."
        )
    db = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(p.path.lstrip("/")),
        "USER": unquote(p.username or ""),
        "PASSWORD": unquote(p.password or ""),
        "HOST": p.hostname or "",
        "PORT": str(p.port or ""),
    }
    # Parametros de la query (?sslmode=require&connect_timeout=10) que acepta psycopg2.
    validos = ("sslmode", "sslrootcert", "connect_timeout", "options", "application_name")
    opts = {k: v[-1] for k, v in parse_qs(p.query).items() if k in validos}
    if opts:
        db["OPTIONS"] = opts
    return db

# En producción, definir la variable de entorno DJANGO_SECRET_KEY
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-cambiar-en-produccion")
# En producción (Render) DEBUG queda desactivado por seguridad: los errores muestran
# una página genérica sin exponer código ni configuración. En desarrollo local,
# definir DJANGO_DEBUG=True en el archivo .env para ver el detalle de los errores.
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

# Dominios autorizados a servir la app. Para agregar un dominio propio en el futuro,
# definir DJANGO_ALLOWED_HOSTS en las variables de entorno (separados por coma).
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "patrimonio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Cookies de sesion y CSRF solo via HTTPS en produccion (Render sirve siempre por HTTPS).
# En desarrollo local (DEBUG=True) se permiten http:// para no romper 127.0.0.1:8000.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "patrimonio.context.avisos",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": (
        _db_desde_url(os.environ["DATABASE_URL"])
        if os.environ.get("DATABASE_URL")
        else {
            # SQLite local para desarrollo. En produccion (Render) definir la
            # variable DATABASE_URL con una base PostgreSQL externa y persistente
            # (Neon, Supabase o Render Postgres): el disco gratuito de Render es
            # efimero y borra SQLite en cada despliegue.
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    )
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Riesgo R8 (Ley 19.628): la ubicación del usuario NO se guarda en la base de datos.
# Con sesiones firmadas en cookie, la posición vive solo en el navegador del usuario.
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 días (para recordar alertas)

# OpenStreetMap exige que las peticiones de mosaicos indiquen el sitio de origen (Referer).
# Django por defecto usa "same-origin" y lo oculta, lo que provoca el error 403 "Access blocked".
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Mapa base. Usamos OpenStreetMap estándar (gratuito, sin API key requerida).
TILES_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILES_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

# Configuración de Correo Electrónico
# Envío principal: Brevo API v3 por HTTPS (puerto 443). Las plataformas PaaS como Render
# bloquean los puertos SMTP salientes (25/465/587), por eso el envío por API es el canal
# recomendado. Definir BREVO_API_KEY y BREVO_SENDER_EMAIL en las variables de entorno.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")

# Tope de espera para el respaldo SMTP: evita que un servidor caído cuelgue
# la respuesta web durante minutos.
EMAIL_TIMEOUT = 5

# Respaldo SMTP (solo si Brevo API no está disponible). En desarrollo sin EMAIL_HOST
# los correos se imprimen formateados en la terminal.
if BREVO_API_KEY and BREVO_SENDER_EMAIL:
    # Brevo API por HTTPS: funciona en Render (que bloquea los puertos SMTP).
    EMAIL_BACKEND = "patrimonio.backends.BrevoAPIEmailBackend"
elif os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", f"Patrimonio Cerca <{EMAIL_HOST_USER}>")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Remitente por defecto para los correos que genera Django (recuperar contraseña,
# etc.). El backend de Brevo lo ignora y usa BREVO_SENDER_EMAIL, pero los demás
# backends lo respetan. Siempre el correo del proyecto, nunca uno personal.
if not os.environ.get("DEFAULT_FROM_EMAIL"):
    DEFAULT_FROM_EMAIL = f"Patrimonio Cerca <{BREVO_SENDER_EMAIL or 'patrimonio.cerca@gmail.com'}>"


