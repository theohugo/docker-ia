#!/bin/sh
set -eu

if [ "${RUN_STARTUP_TASKS:-False}" = "True" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
