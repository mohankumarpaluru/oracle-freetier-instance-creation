FROM python:3.9-slim

WORKDIR /app

# Install system dependencies (if any needed for paramiko/cryptography)
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY main.py .
COPY email_content.html .

# Create volume mount point for logs and config (if not via env)
VOLUME /app/logs

# Run the bot
CMD ["python", "-u", "main.py"]
