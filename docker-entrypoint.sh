#!/usr/bin/env bash
set -euo pipefail

echo "[Entrypoint] Waiting for database connection..."
python -c "
import time, os, sys

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('[Entrypoint] ERROR: DATABASE_URL is not set!', file=sys.stderr)
    sys.exit(1)

import psycopg
for attempt in range(1, 31):
    try:
        conn = psycopg.connect(db_url)
        conn.close()
        print(f'[Entrypoint] Database is ready! (attempt {attempt})')
        break
    except Exception as e:
        print(f'[Entrypoint] Database not ready yet ({e}). Retrying in 1s...')
        time.sleep(1)
else:
    print('[Entrypoint] ERROR: Database connection timed out after 30 attempts.', file=sys.stderr)
    sys.exit(1)
"

echo "[Entrypoint] Applying database migrations..."
python manage.py migrate --noinput

echo "[Entrypoint] Collecting static files..."
python manage.py collectstatic --noinput

if [ "${SEED_ON_START:-false}" = "true" ]; then
    echo "[Entrypoint] SEED_ON_START is true. Creating benchmark demo users..."
    python manage.py create_demo_users
    echo "[Entrypoint] Seeding benchmark master data..."
    python manage.py seed_benchmark
fi

echo "[Entrypoint] Executing command: $@"
exec "$@"
