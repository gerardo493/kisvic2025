#!/usr/bin/env python3
"""
Script de Configuración Inicial para el Desplegador de Render
Configura automáticamente el entorno para el despliegue
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def install_requirements():
    """Instala las dependencias necesarias"""
    print("📦 Instalando dependencias...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_deploy.txt"])
        print("✅ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al instalar dependencias: {e}")
        return False

def create_directories():
    """Crea los directorios necesarios"""
    print("📁 Creando directorios necesarios...")
    
    directories = ['backups', 'temp', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directorio '{directory}' creado/verificado")

def get_render_credentials():
    """Solicita las credenciales de Render al usuario"""
    print("\n🔑 Configuración de Render")
    print("=" * 40)
    
    print("\nPara obtener tus credenciales de Render:")
    print("1. Ve a https://dashboard.render.com/account/api-keys")
    print("2. Crea una nueva API key")
    print("3. Ve a tu servicio y copia el Service ID de la URL")
    print("4. El Account ID está en la URL del dashboard\n")
    
    api_key = input("🔑 API Key de Render: ").strip()
    service_id = input("🆔 Service ID: ").strip()
    account_id = input("👤 Account ID (opcional): ").strip()
    
    if not api_key or not service_id:
        print("❌ API Key y Service ID son obligatorios")
        return None
        
    return {
        "render": {
            "api_key": api_key,
            "service_id": service_id,
            "account_id": account_id
        },
        "deploy": {
            "exclude_patterns": [
                "__pycache__",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".git",
                ".gitignore",
                ".env",
                "venv",
                "node_modules",
                "*.log",
                "*.tmp",
                "*.bak",
                "deploy_render.py",
                "render_config.json",
                "*.zip",
                "backups",
                "temp"
            ],
            "include_patterns": [
                "*.py",
                "*.html",
                "*.css",
                "*.js",
                "*.json",
                "*.txt",
                "*.md",
                "requirements.txt",
                "static/*",
                "templates/*"
            ],
            "backup_before_deploy": True,
            "create_zip_backup": True
        },
        "paths": {
            "source": ".",
            "backup": "./backups",
            "temp": "./temp"
        }
    }

def create_config_file(config):
    """Crea el archivo de configuración"""
    config_file = "render_config.json"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print(f"✅ Archivo de configuración creado: {config_file}")
        return True
    except Exception as e:
        print(f"❌ Error al crear archivo de configuración: {e}")
        return False

def create_batch_file():
    """Crea un archivo .bat para Windows"""
    batch_content = """@echo off
echo 🚀 Desplegando a Render...
python deploy_render.py
pause
"""
    
    try:
        with open("deploy_render.bat", 'w', encoding='utf-8') as f:
            f.write(batch_content)
        print("✅ Archivo batch creado: deploy_render.bat")
        return True
    except Exception as e:
        print(f"❌ Error al crear archivo batch: {e}")
        return False

def create_shell_script():
    """Crea un script de shell para Linux/Mac"""
    shell_content = """#!/bin/bash
echo "🚀 Desplegando a Render..."
python3 deploy_render.py
"""
    
    try:
        with open("deploy_render.sh", 'w', encoding='utf-8') as f:
            f.write(shell_content)
        
        # Hacer el script ejecutable en Linux/Mac
        if os.name != 'nt':  # No es Windows
            os.chmod("deploy_render.sh", 0o755)
            
        print("✅ Script de shell creado: deploy_render.sh")
        return True
    except Exception as e:
        print(f"❌ Error al crear script de shell: {e}")
        return False

def test_configuration():
    """Prueba la configuración creada"""
    print("\n🧪 Probando configuración...")
    
    try:
        from deploy_render import RenderDeployer
        deployer = RenderDeployer()
        
        if deployer.validate_config():
            print("✅ Configuración válida")
            return True
        else:
            print("❌ Configuración inválida")
            return False
    except Exception as e:
        print(f"❌ Error al probar configuración: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Configurador del Desplegador de Render")
    print("=" * 50)
    
    # Verificar si ya existe configuración
    if os.path.exists("render_config.json"):
        print("⚠️  Ya existe un archivo de configuración")
        overwrite = input("¿Deseas sobrescribirlo? (s/N): ").strip().lower()
        if overwrite != 's':
            print("Configuración cancelada")
            return
    
    # Instalar dependencias
    if not install_requirements():
        print("❌ No se pudieron instalar las dependencias")
        return
    
    # Crear directorios
    create_directories()
    
    # Obtener credenciales
    config = get_render_credentials()
    if not config:
        print("❌ No se pudieron obtener las credenciales")
        return
    
    # Crear archivo de configuración
    if not create_config_file(config):
        print("❌ No se pudo crear el archivo de configuración")
        return
    
    # Crear scripts de ejecución
    create_batch_file()
    create_shell_script()
    
    # Probar configuración
    if test_configuration():
        print("\n🎉 Configuración completada exitosamente!")
        print("\n📋 Para usar el desplegador:")
        print("   Windows: Ejecuta 'deploy_render.bat'")
        print("   Linux/Mac: Ejecuta './deploy_render.sh'")
        print("   Manual: python deploy_render.py")
        print("\n🔧 Para modificar la configuración, edita 'render_config.json'")
    else:
        print("\n❌ La configuración tiene errores. Revisa el archivo 'render_config.json'")

if __name__ == "__main__":
    main()
