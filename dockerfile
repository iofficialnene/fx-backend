FROM python:3.11-bullseye

WORKDIR /usr/src/app
COPY . .

# System deps for numeric libs (kept minimal)
RUN apt-get update && \
    apt-get install -y build-essential gfortran libopenblas-dev liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

# Use JSON form for CMD and default to PORT env var (Render sets $PORT)
ENV PORT=5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT", "--workers", "3"]
