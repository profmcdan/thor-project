#!/bin/bash
set -e

# Move into Django app directory where manage.py and core modules reside
cd /app/app

if [ "$1" = "web" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
    
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    
    echo "Starting Gunicorn server..."
    exec gunicorn --bind 0.0.0.0:8000 core.wsgi:application --workers 4 --threads 2 --timeout 60 --access-logfile - --error-logfile -
elif [ "$1" = "celery" ]; then
    echo "Starting Celery Worker..."
    exec celery -A core worker -l info
elif [ "$1" = "celery-beat" ]; then
    echo "Starting Celery Beat..."
    # Store pid in /tmp to ensure write access under non-root appuser
    exec celery -A core beat -l info --pidfile=/tmp/celerybeat.pid
else
    exec "$@"
fi
