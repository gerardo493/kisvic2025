#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación final para Render.
Verifica que todos los archivos estén correctos antes del deploy.
"""

import os
import sys
from datetime import datetime

def verificar_archivos_render():
    """Verifica que todos los archivos necesarios para Render estén presentes."""
    print("🔍 VERIFICANDO ARCHIVOS PARA RENDER")
    print("="*60)
    
    archivos_requeridos = [
        'requirements_render_definitivo.txt',
        'render_definitivo.yaml',
        'runtime.txt',
        'gunicorn.conf.py',
        'app.py',
        'flask_config.py'
    ]
    
    archivos_alternativos = [
        'environment.yml',
        'Dockerfile'
    ]
    
    archivos_faltantes = []
    
    # Verificar archivos requeridos
    for archivo in archivos_requeridos:
        if os.path.exists(archivo):
            print(f"✅ {archivo}")
        else:
            print(f"❌ {archivo} - FALTANTE")
            archivos_faltantes.append(archivo)
    
    # Verificar archivos alternativos
    print(f"\n📁 ARCHIVOS ALTERNATIVOS:")
    for archivo in archivos_alternativos:
        if os.path.exists(archivo):
            print(f"✅ {archivo}")
        else:
            print(f"⚠️ {archivo} - No encontrado (opcional)")
    
    return len(archivos_faltantes) == 0

def verificar_requirements():
    """Verifica el archivo de requirements."""
    print(f"\n📦 VERIFICANDO REQUIREMENTS:")
    print("-" * 40)
    
    archivo = 'requirements_render_definitivo.txt'
    if not os.path.exists(archivo):
        print(f"❌ {archivo} no encontrado")
        return False
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
            
        # Verificar Flask 2.2.5
        if 'Flask==2.2.5' in contenido:
            print("✅ Flask==2.2.5 encontrado")
        else:
            print("❌ Flask==2.2.5 NO encontrado")
            return False
        
        # Verificar Flask-WTF 1.0.1
        if 'Flask-WTF==1.0.1' in contenido:
            print("✅ Flask-WTF==1.0.1 encontrado")
        else:
            print("❌ Flask-WTF==1.0.1 NO encontrado")
            return False
        
        # Verificar gunicorn
        if 'gunicorn==' in contenido:
            print("✅ Gunicorn encontrado")
        else:
            print("❌ Gunicorn NO encontrado")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error leyendo {archivo}: {e}")
        return False

def verificar_configuracion_render():
    """Verifica la configuración de Render."""
    print(f"\n⚙️ VERIFICANDO CONFIGURACIÓN RENDER:")
    print("-" * 40)
    
    archivo = 'render_definitivo.yaml'
    if not os.path.exists(archivo):
        print(f"❌ {archivo} no encontrado")
        return False
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
            
        # Verificar Python 3.10
        if 'python3.10' in contenido:
            print("✅ Python 3.10 configurado")
        else:
            print("❌ Python 3.10 NO configurado")
            return False
        
        # Verificar requirements
        if 'requirements_render_definitivo.txt' in contenido:
            print("✅ Requirements correctos")
        else:
            print("❌ Requirements incorrectos")
            return False
        
        # Verificar gunicorn
        if 'gunicorn' in contenido:
            print("✅ Gunicorn configurado")
        else:
            print("❌ Gunicorn NO configurado")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error leyendo {archivo}: {e}")
        return False

def generar_resumen_deploy():
    """Genera un resumen de los pasos para el deploy."""
    print(f"\n📋 RESUMEN PARA DEPLOY EN RENDER:")
    print("="*60)
    
    print("1️⃣ CAMBIAR BUILD COMMAND:")
    print("   pip install -r requirements_render_definitivo.txt")
    
    print("\n2️⃣ CAMBIAR START COMMAND:")
    print("   gunicorn --config gunicorn.conf.py app:app")
    
    print("\n3️⃣ CONFIGURAR ENVIRONMENT VARIABLES:")
    print("   PYTHON_VERSION: 3.10.0")
    print("   FLASK_ENV: production")
    print("   SECRET_KEY: generate")
    print("   LXML_USE_SYSTEM_LIBRARIES: 1")
    print("   STATIC_DEPS: true")
    
    print("\n4️⃣ HACER DEPLOY MANUAL:")
    print("   - Click en 'Manual Deploy'")
    print("   - Seleccionar 'Deploy latest commit'")
    
    print("\n5️⃣ VERIFICAR LOGS:")
    print("   - Sin errores de Markup")
    print("   - Flask 2.2.5 funcionando")
    print("   - Aplicación accesible")

def main():
    """Función principal de verificación."""
    print("🚀 VERIFICACIÓN COMPLETA PARA RENDER")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar archivos
    archivos_ok = verificar_archivos_render()
    
    # Verificar requirements
    requirements_ok = verificar_requirements()
    
    # Verificar configuración
    config_ok = verificar_configuracion_render()
    
    # Resumen
    print(f"\n" + "="*80)
    print("📊 RESUMEN DE VERIFICACIÓN:")
    print("="*80)
    
    if archivos_ok:
        print("✅ Archivos para Render: COMPLETOS")
    else:
        print("❌ Archivos para Render: INCOMPLETOS")
    
    if requirements_ok:
        print("✅ Requirements: CORRECTOS")
    else:
        print("❌ Requirements: INCORRECTOS")
    
    if config_ok:
        print("✅ Configuración Render: CORRECTA")
    else:
        print("❌ Configuración Render: INCORRECTA")
    
    # Estado general
    if archivos_ok and requirements_ok and config_ok:
        print(f"\n🎉 ¡TODO LISTO PARA RENDER!")
        generar_resumen_deploy()
    else:
        print(f"\n❌ HAY PROBLEMAS QUE RESOLVER ANTES DEL DEPLOY")
        print("Revisa los errores anteriores y corrige los archivos faltantes.")
    
    print(f"\n" + "="*80)
    print("📚 CONSULTA INSTRUCCIONES_RENDER.md PARA MÁS DETALLES")

if __name__ == '__main__':
    main()
