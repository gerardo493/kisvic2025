#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archivo de compatibilidad para manejar diferencias entre Flask 2.x y 3.x
"""

import flask

# Detectar versión de Flask
FLASK_VERSION = flask.__version__
FLASK_MAJOR = int(FLASK_VERSION.split('.')[0])

# Importar Markup según la versión
if FLASK_MAJOR >= 3:
    # Flask 3.x: Markup está en flask.utils
    try:
        from flask.utils import Markup
    except ImportError:
        # Fallback: usar MarkupSafe directamente
        from markupsafe import Markup
else:
    # Flask 2.x: Markup está en flask
    try:
        from flask import Markup
    except ImportError:
        # Fallback: usar MarkupSafe directamente
        from markupsafe import Markup

# Función helper para usar Markup de manera segura
def safe_markup(text):
    """Crea Markup de manera segura independientemente de la versión de Flask."""
    if text is None:
        return Markup('')
    return Markup(str(text))

# Función helper para escapar HTML
def escape_html(text):
    """Escapa HTML de manera segura."""
    if text is None:
        return ''
    return str(text).replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

# Función helper para verificar si Markup está disponible
def is_markup_available():
    """Verifica si Markup está disponible."""
    try:
        Markup('test')
        return True
    except:
        return False

# Información de compatibilidad
def get_compatibility_info():
    """Obtiene información de compatibilidad."""
    return {
        'flask_version': FLASK_VERSION,
        'flask_major': FLASK_MAJOR,
        'markup_available': is_markup_available(),
        'markup_location': 'flask.utils' if FLASK_MAJOR >= 3 else 'flask'
    }

if __name__ == '__main__':
    info = get_compatibility_info()
    print("🔍 INFORMACIÓN DE COMPATIBILIDAD FLASK")
    print("="*50)
    print(f"Versión de Flask: {info['flask_version']}")
    print(f"Versión mayor: {info['flask_major']}")
    print(f"Markup disponible: {info['markup_available']}")
    print(f"Ubicación de Markup: {info['markup_location']}")
    
    if info['markup_available']:
        print("✅ Markup funcionando correctamente")
        test_markup = safe_markup("<strong>Test</strong>")
        print(f"Test Markup: {test_markup}")
    else:
        print("❌ Markup no disponible")
