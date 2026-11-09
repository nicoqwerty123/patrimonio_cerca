#!/usr/bin/env bash
set -o errexit

if [ -d "patrimonio_cerca" ] && [ -f "patrimonio_cerca/manage.py" ]; then
    cd patrimonio_cerca
fi

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py cargar_datos
