#!/usr/bin/env bash
# ==============================================================================
# Script de Despliegue Automatizado para AWS Academy EC2 (Ubuntu 22.04 / 24.04)
# Proyecto 2: FitLife — Django + DRF + PostgreSQL + Gunicorn + Nginx
# Uso: chmod +x deploy_ec2.sh && sudo ./deploy_ec2.sh
# ==============================================================================

set -e

APP_DIR="/home/ubuntu/fitlife"
DB_NAME="fitlife_db"
DB_USER="postgres"
DB_PASS="Valorant-1"

echo "=== [1/7] Actualizando paquetes del sistema e instalando dependencias ==="
apt-get update -y
apt-get install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx git curl

echo "=== [2/7] Configurando PostgreSQL y creando base de datos ${DB_NAME} ==="
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")
if [ "$DB_EXISTS" != "1" ]; then
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} ENCODING 'UTF8';"
    echo "Base de datos ${DB_NAME} creada."
else
    echo "La base de datos ${DB_NAME} ya existe."
fi

echo "=== [3/7] Preparando directorio de la aplicación y entorno virtual ==="
if [ ! -d "$APP_DIR" ]; then
    git clone https://github.com/egonista/fitlife.git "$APP_DIR"
fi

cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "=== [4/7] Generando archivo .env de producción en EC2 ==="
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "127.0.0.1")
cat > "$APP_DIR/.env" <<EOF
SECRET_KEY=django-production-fitlife-aws-ec2-key-2026
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,${PUBLIC_IP},*
DB_ENGINE=django.db.backends.postgresql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
EOF

echo "=== [5/7] Aplicando migraciones, datos semilla y archivos estáticos ==="
./venv/bin/python manage.py makemigrations --noinput
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py seed_fitlife
./venv/bin/python manage.py collectstatic --noinput
chown -R ubuntu:www-data "$APP_DIR"

echo "=== [6/7] Configurando servicio systemd para Gunicorn ==="
cat > /etc/systemd/system/fitlife.service <<EOF
[Unit]
Description=Gunicorn daemon for FitLife Django Application
After=network.target postgresql.service

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn --workers 3 --bind unix:${APP_DIR}/fitlife.sock fitlife_project.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fitlife
systemctl restart fitlife

echo "=== [7/7] Configurando Nginx como Proxy Inverso en Puerto 80 ==="
cat > /etc/nginx/sites-available/fitlife <<EOF
server {
    listen 80;
    server_name ${PUBLIC_IP} _;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:${APP_DIR}/fitlife.sock;
    }
}
EOF

ln -sf /etc/nginx/sites-available/fitlife /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "=================================================================="
echo " ¡Despliegue completado exitosamente!"
echo " URL Pública AWS EC2: http://${PUBLIC_IP}/"
echo " Panel Django Admin : http://${PUBLIC_IP}/admin/"
echo " Credenciales Admin : admin / Valorant-1"
echo "=================================================================="
