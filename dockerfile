FROM python:3.11-bullseye

WORKDIR /usr/src/app
COPY . .

RUN apt-get update && \
    apt-get install -y build-essential gfortran libopenblas-dev liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Local testing will use 5000
EXPOSE 5000

# Render uses $PORT, local uses 5000
CMD ["bash", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000}"]
