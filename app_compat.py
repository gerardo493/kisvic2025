#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archivo de compatibilidad para app.py - Maneja diferencias entre Flask 2.x y 3.x
"""

import sys
import os

def setup_flask_compatibility():
    """Configura la compatibilidad de Flask según la versión disponible."""
    
    # Intentar importar Flask
    try:
        import flask
        flask_version = flask.__version__
        major_version = int(flask_version.split('.')[0])
        
        print(f"🔍 Detectada versión de Flask: {flask_version}")
        
        if major_version >= 3:
            print("⚠️  Flask 3.x detectado - Configurando compatibilidad...")
            
            # Para Flask 3.x, usar MarkupSafe directamente
            try:
                from markupsafe import Markup
                print("✅ Markup importado desde markupsafe")
            except ImportError:
                print("❌ MarkupSafe no disponible")
                return False
                
        else:
            print("✅ Flask 2.x detectado - Compatibilidad nativa")
            try:
                from flask import Markup
                print("✅ Markup importado desde flask")
            except ImportError:
                print("❌ Markup no disponible en Flask")
                return False
        
        return True
        
    except ImportError:
        print("❌ Flask no está instalado")
        return False

def check_dependencies():
    """Verifica que todas las dependencias estén disponibles."""
    
    dependencies = [
        'flask',
        'werkzeug', 
        'jinja2',
        'markupsafe',
        'requests',
        'beautifulsoup4'
    ]
    
    missing = []
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} disponible")
        except ImportError:
            print(f"❌ {dep} NO disponible")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠️  Dependencias faltantes: {', '.join(missing)}")
        return False
    
    print("\n✅ Todas las dependencias están disponibles")
    return True

def get_requirements_file():
    """Determina qué archivo de requirements usar."""
    
    # Verificar archivos disponibles
    files = [
        'requirements_render.txt',
        'requirements_ultra_estable.txt', 
        'requirements_flask2.txt',
        'requirements.txt'
    ]
    
    for file in files:
        if os.path.exists(file):
            print(f"📁 Archivo de requirements encontrado: {file}")
            return file
    
    print("❌ No se encontró archivo de requirements")
    return None

def main():
    """Función principal de verificación."""
    print("🚀 VERIFICACIÓN DE COMPATIBILIDAD FLASK")
    print("="*60)
    
    # Verificar Flask
    if not setup_flask_compatibility():
        print("\n❌ Problema con Flask detectado")
        return False
    
    # Verificar dependencias
    if not check_dependencies():
        print("\n❌ Dependencias faltantes")
        return False
    
    # Verificar archivo de requirements
    req_file = get_requirements_file()
    if not req_file:
        print("\n❌ No se encontró archivo de requirements")
        return False
    
    print(f"\n✅ VERIFICACIÓN COMPLETADA")
    print(f"📋 Archivo de requirements recomendado: {req_file}")
    
    return True

if __name__ == '__main__':
    success = main()
    if success:
        print("\n🎉 El sistema está listo para funcionar")
    else:
        print("\n❌ Se detectaron problemas de compatibilidad")
        sys.exit(1)
