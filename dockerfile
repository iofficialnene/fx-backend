FROM python:3.11-bullseye

# Set working directory
WORKDIR /usr/src/app

# Copy project files
COPY . .

# Install system dependencies (safe for all scientific Python packages)
RUN apt-get update && \
    apt-get install -y build-essential gfortran libopenblas-dev liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose app port
EXPOSE 5000

# Run Flask app with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
