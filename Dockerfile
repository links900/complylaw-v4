# Dockerfile – works 100 % on Railway in December 2025
FROM python:3.11-slim-bookworm

# Install exact system libraries WeasyPrint needs (Debian 12 names)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo-gobject2 \
    libcairo2 \
    libglib2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libjpeg62-turbo \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Railway recommends this)
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app
USER app

# Copy and install Python packages
COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=app:app . .

# Use the PORT Railway injects
ENV PORT=8080
CMD exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4