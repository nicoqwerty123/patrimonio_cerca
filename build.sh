#!/usr/bin/env bash
set -o errexit

# Si estamos en la raiz del repositorio y existe la subcarpeta patrimonio_cerca, entrar en ella
if [ -d "patrimonio_cerca" ] && [ -f "patrimonio_cerca/manage.py" ]; then
    cd patrimonio_cerca
fi

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py cargar_datos
