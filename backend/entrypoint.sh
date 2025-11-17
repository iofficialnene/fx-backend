#!/bin/sh
# entrypoint.sh
# Use the PORT env var (Render sets $PORT)
: "${PORT:=5000}"
exec gunicorn app:app --bind 0.0.0.0:"$PORT" --workers 3 --timeout 60
