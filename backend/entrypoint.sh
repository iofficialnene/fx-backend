#!/usr/bin/env sh
set -e

# entrypoint.sh
# Render/Heroku-compatible entry script
# Ensures PORT is set (Render provides this automatically)
: "${PORT:=5000}"

echo "Starting Gunicorn on port $PORT..."

# --preload reduces worker memory usage
# --worker-tmp-dir avoids read-only FS issues
exec gunicorn app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers
