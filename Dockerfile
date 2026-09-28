# ==============================================================================
# MikroTik AI Agent Automation - Production Dockerfile
# Ringan, aman, dan siap deploy di VPS / Cloud / Server Lokal / Docker MikroTik
# ==============================================================================

FROM python:3.11-slim

# Mencegah penulisan file .pyc dan memastikan output log langsung tampil (unbuffered)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Jakarta

WORKDIR /app

# Install dependensi sistem dasar & timezone
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code project
COPY . .

# Buat folder data dan logs agar persistent
RUN mkdir -p /app/data /app/logs

# Jalankan via supervisor watchdog untuk auto-recovery jika ada crash
CMD ["python", "service/watchdog.py"]
