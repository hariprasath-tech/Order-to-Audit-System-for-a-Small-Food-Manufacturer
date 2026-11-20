# Stage 1: Build front-end assets (zero CDN dependencies)
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Python production runtime (Django 5 + WeasyPrint)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for PostgreSQL and WeasyPrint (Pango, Cairo, GDK-PixBuf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements if present
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY . .

# Copy compiled and self-hosted frontend assets from Stage 1
COPY --from=frontend-builder /app/static/dist ./static/dist
COPY --from=frontend-builder /app/static/vendor ./static/vendor
COPY --from=frontend-builder /app/static/fonts ./static/fonts

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
