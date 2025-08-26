# Dockerfile para mi-app-web
FROM python:3.10-slim

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

# Copiar requirements
COPY requirements_render_definitivo.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements_render_definitivo.txt

# Copiar código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 5000

# Configurar variables de entorno
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Comando de inicio
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
