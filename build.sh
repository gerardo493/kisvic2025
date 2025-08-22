#!/bin/bash
# Script de construcción personalizado para Render con Python 3.11

echo "🔧 Verificando versión de Python..."
python3.11 --version

echo "🔧 Instalando dependencias del sistema..."
apt-get update
apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    gcc \
    g++ \
    python3.11-dev \
    pkg-config \
    libffi-dev

echo "🐍 Configurando Python 3.11..."
python3.11 -m pip install --upgrade pip

echo "📦 Configurando variables de entorno para lxml..."
export LXML_USE_SYSTEM_LIBRARIES=1
export STATIC_DEPS=true
export PYTHONPATH=/usr/local/lib/python3.11/site-packages

echo "🧹 Limpiando completamente el entorno virtual..."
python3.11 -m pip uninstall -y Flask Flask-WTF WTForms lxml beautifulsoup4
python3.11 -m pip cache purge

echo "📦 Instalando dependencias de Python..."
python3.11 -m pip install --no-cache-dir --force-reinstall --no-deps -r requirements_forzado.txt

echo "✅ Construcción completada con Python 3.11"
