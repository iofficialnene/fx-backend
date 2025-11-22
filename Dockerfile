# ============================================
# STAGE 1: Build Frontend (Vite/React)
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ============================================
# STAGE 2: Python Backend + Serve Frontend
# ============================================
FROM python:3.11-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y --auto-remove build-essential gcc

COPY backend/app.py backend/confluence.py ./

COPY --from=frontend-builder /frontend/dist ./frontend/dist

ENV YFINANCE_CACHE_DIR=/tmp/py-yfinance
RUN mkdir -p /tmp/py-yfinance && chmod -R 777 /tmp/py-yfinance

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "120"]