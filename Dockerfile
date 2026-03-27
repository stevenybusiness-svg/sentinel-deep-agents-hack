FROM python:3.12-slim

# System deps for aerospike C-extension + Node.js for frontend build
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    python3-dev \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY frontend/package.json frontend/package-lock.json ./frontend/
WORKDIR /app/frontend
RUN npm ci
WORKDIR /app
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm run build

# Backend source
WORKDIR /app
COPY sentinel/ ./sentinel/
COPY aerospike.conf .
COPY pyproject.toml .
RUN pip install -e . --no-deps

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "sentinel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
