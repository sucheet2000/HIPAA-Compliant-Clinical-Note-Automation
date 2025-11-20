FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /app/output && \
    chown -R appuser:appuser /app

# Copy application code
COPY src/ src/

# Switch to non-root user
USER appuser

# Expose Flask port (for future UI)
EXPOSE 5000

CMD ["python", "src/main.py"]
