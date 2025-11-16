# Use Python 3.10
FROM python:3.10

# Disable yfinance cache to prevent worker crash
ENV YFINANCE_NO_CACHE=1

# Render gives you a port. Your app must bind to it.
ENV PORT=5000

# Working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 5000

# Start Gunicorn
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 200
