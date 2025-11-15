# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (matches app.py)
EXPOSE 5000

# Use gunicorn to run the Flask app in production
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
