FROM python:3.12-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    gcc \
    g++ \
    python3-dev \
    pkg-config \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Cloud Run expone PORT (normalmente 8080)
EXPOSE 8080
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Comando de inicio
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
