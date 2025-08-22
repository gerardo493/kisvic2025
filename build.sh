#!/bin/bash
set -e

echo "🚀 Iniciando build de la aplicación..."

# Actualizar pip
echo "📦 Actualizando pip..."
python -m pip install --upgrade pip

# Instalar dependencias del sistema si es necesario
echo "🔧 Instalando dependencias del sistema..."
apt-get update -qq && apt-get install -y -qq \
    python3-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev

# Instalar dependencias de Python
echo "🐍 Instalando dependencias de Python..."
python -m pip install --no-cache-dir -r requirements.txt

# Verificar instalación
echo "✅ Verificando instalación..."
python -c "import psutil, cryptography, beautifulsoup4, flask; print('Todas las dependencias instaladas correctamente')"

echo "🎉 Build completado exitosamente!"
