# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

# Start the app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
