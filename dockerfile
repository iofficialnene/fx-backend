# Use official Python 3.11 slim image to avoid version conflicts
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y build-essential libatlas-base-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port for Render
EXPOSE 5000

# Run the app with gunicorn
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000"]
