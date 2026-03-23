# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend with Kraken
FROM python:3.12-slim AS backend

# System deps for Kraken (PyTorch, image libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Try to install Kraken (optional — heavy dependency)
RUN pip install --no-cache-dir kraken || echo "WARNING: Kraken install failed, OCR will use Claude-only mode"

# Copy backend code
COPY backend/ ./
# Copy built frontend into static serving directory
COPY --from=frontend-build /app/frontend/dist ./static

# Copy seed data and scripts
COPY docs/glossary-seed.csv /app/seed/glossary-seed.csv
COPY scripts/ /app/scripts/

# Create data directory
RUN mkdir -p /app/data/images

# Entrypoint script
COPY backend/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
