#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración automática de Flask para compatibilidad entre versiones.
Este archivo se importa en app.py para manejar automáticamente las diferencias.
"""

import sys
import os

def setup_flask_environment():
    """Configura el entorno de Flask automáticamente."""
    
    try:
        import flask
        flask_version = flask.__version__
        major_version = int(flask_version.split('.')[0])
        
        print(f"🔍 Configurando Flask {flask_version}")
        
        # Configurar Markup según la versión
        if major_version >= 3:
            # Flask 3.x: Markup está en flask.utils
            try:
                from flask.utils import Markup
                print("✅ Markup importado desde flask.utils (Flask 3.x)")
                globals()['Markup'] = Markup
            except ImportError:
                # Fallback: usar MarkupSafe directamente
                try:
                    from markupsafe import Markup
                    print("✅ Markup importado desde markupsafe (fallback)")
                    globals()['Markup'] = Markup
                except ImportError:
                    print("❌ Markup no disponible")
                    return False
        else:
            # Flask 2.x: Markup está en flask
            try:
                from flask import Markup
                print("✅ Markup importado desde flask (Flask 2.x)")
                globals()['Markup'] = Markup
            except ImportError:
                # Fallback: usar MarkupSafe directamente
                try:
                    from markupsafe import Markup
                    print("✅ Markup importado desde markupsafe (fallback)")
                    globals()['Markup'] = Markup
                except ImportError:
                    print("❌ Markup no disponible")
                    return False
        
        # Configurar CSRF según la versión
        if major_version >= 3:
            try:
                from flask_wtf.csrf import CSRFProtect
                print("✅ CSRFProtect importado (Flask 3.x)")
                globals()['CSRFProtect'] = CSRFProtect
            except ImportError:
                print("⚠️ CSRFProtect no disponible")
        else:
            try:
                from flask_wtf.csrf import CSRFProtect
                print("✅ CSRFProtect importado (Flask 2.x)")
                globals()['CSRFProtect'] = CSRFProtect
            except ImportError:
                print("⚠️ CSRFProtect no disponible")
        
        print(f"✅ Configuración de Flask {flask_version} completada")
        return True
        
    except ImportError as e:
        print(f"❌ Error importando Flask: {e}")
        return False
    except Exception as e:
        print(f"❌ Error configurando Flask: {e}")
        return False

def get_flask_info():
    """Obtiene información detallada de Flask."""
    try:
        import flask
        return {
            'version': flask.__version__,
            'major': int(flask.__version__.split('.')[0]),
            'import_path': flask.__file__
        }
    except:
        return None

def safe_markup(text):
    """Crea Markup de manera segura."""
    try:
        if 'Markup' in globals():
            if text is None:
                return globals()['Markup']('')
            return globals()['Markup'](str(text))
        else:
            # Fallback: escapar HTML manualmente
            if text is None:
                return ''
            return str(text).replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
    except:
        # Fallback final
        if text is None:
            return ''
        return str(text)

# Configurar automáticamente al importar
if __name__ == '__main__':
    print("🚀 CONFIGURACIÓN AUTOMÁTICA DE FLASK")
    print("="*50)
    
    if setup_flask_environment():
        info = get_flask_info()
        if info:
            print(f"📊 Información de Flask:")
            print(f"   Versión: {info['version']}")
            print(f"   Versión mayor: {info['major']}")
            print(f"   Ubicación: {info['import_path']}")
        
        print("\n✅ Configuración completada exitosamente")
    else:
        print("\n❌ Error en la configuración")
        sys.exit(1)
else:
    # Configurar automáticamente al importar
    setup_flask_environment()
