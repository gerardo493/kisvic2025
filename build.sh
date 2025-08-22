#!/bin/bash
# Script de construcción personalizado para Render

echo "🔧 Instalando dependencias del sistema..."
apt-get update
apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    gcc \
    g++ \
    python3-dev \
    pkg-config \
    libffi-dev

echo "🐍 Configurando Python..."
python -m pip install --upgrade pip

echo "📦 Instalando dependencias de Python..."
export LXML_USE_SYSTEM_LIBRARIES=1
export STATIC_DEPS=true
pip install --no-cache-dir -r requirements.txt

echo "✅ Construcción completada"
