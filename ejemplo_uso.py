#!/usr/bin/env python3
"""
Ejemplo de Uso del Sistema de Despliegue a Render
Este script muestra diferentes formas de usar el desplegador
"""

from deploy_render import RenderDeployer
import json
import os

def ejemplo_configuracion_personalizada():
    """Ejemplo de configuración personalizada"""
    print("🔧 Ejemplo de Configuración Personalizada")
    print("=" * 50)
    
    # Configuración personalizada para un proyecto específico
    config_personalizada = {
        "render": {
            "api_key": "tu_api_key_aqui",
            "service_id": "tu_service_id_aqui",
            "account_id": "tu_account_id_aqui"
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
                "temp",
                "ejemplo_uso.py",  # Excluir este archivo de ejemplo
                "README_DEPLOY.md"  # Excluir documentación
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
                "templates/*",
                "app.py",  # Incluir archivo principal
                "config/*"  # Incluir carpeta de configuración
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
    
    # Guardar configuración personalizada
    with open('render_config_personalizada.json', 'w', encoding='utf-8') as f:
        json.dump(config_personalizada, f, indent=4, ensure_ascii=False)
    
    print("✅ Configuración personalizada guardada en 'render_config_personalizada.json'")
    print("📝 Archivos que se subirán:")
    for pattern in config_personalizada['deploy']['include_patterns']:
        print(f"   + {pattern}")
    print("\n📝 Archivos que NO se subirán:")
    for pattern in config_personalizada['deploy']['exclude_patterns']:
        print(f"   - {pattern}")

def ejemplo_despliegue_selectivo():
    """Ejemplo de despliegue selectivo de archivos"""
    print("\n🎯 Ejemplo de Despliegue Selectivo")
    print("=" * 50)
    
    # Crear desplegador con configuración personalizada
    deployer = RenderDeployer('render_config_personalizada.json')
    
    # Obtener lista de archivos que se van a desplegar
    files_to_deploy = deployer.get_files_to_deploy()
    
    print(f"📊 Total de archivos a desplegar: {len(files_to_deploy)}")
    print("\n📁 Archivos principales:")
    
    # Mostrar solo los primeros 10 archivos
    for i, file_path in enumerate(files_to_deploy[:10]):
        relative_path = file_path.relative_to(deployer.project_root)
        print(f"   {i+1:2d}. {relative_path}")
    
    if len(files_to_deploy) > 10:
        print(f"   ... y {len(files_to_deploy) - 10} archivos más")
    
    return deployer

def ejemplo_backup_manual():
    """Ejemplo de creación manual de backup"""
    print("\n💾 Ejemplo de Backup Manual")
    print("=" * 50)
    
    deployer = RenderDeployer('render_config_personalizada.json')
    
    # Crear backup manual
    print("🔄 Creando backup manual...")
    deployer.create_backup()
    print("✅ Backup manual completado")

def ejemplo_crear_paquete():
    """Ejemplo de creación del paquete de despliegue"""
    print("\n📦 Ejemplo de Creación de Paquete de Despliegue")
    print("=" * 50)
    
    deployer = RenderDeployer('render_config_personalizada.json')
    
    # Crear paquete de despliegue
    print("🔄 Creando paquete de despliegue...")
    temp_dir = deployer.create_deployment_package()
    
    if temp_dir.exists():
        print(f"✅ Paquete creado en: {temp_dir}")
        
        # Mostrar contenido del paquete
        print("\n📁 Contenido del paquete:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(str(temp_dir), '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files[:5]:  # Mostrar solo 5 archivos por carpeta
                print(f"{subindent}{file}")
            if len(files) > 5:
                print(f"{subindent}... y {len(files) - 5} archivos más")
    else:
        print("❌ Error al crear el paquete")

def ejemplo_monitoreo_simulado():
    """Ejemplo de monitoreo simulado del despliegue"""
    print("\n📊 Ejemplo de Monitoreo Simulado")
    print("=" * 50)
    
    print("🔄 Simulando estados de despliegue...")
    
    estados = [
        ("building", "Construyendo aplicación..."),
        ("deploying", "Desplegando archivos..."),
        ("live", "Despliegue exitoso!")
    ]
    
    for estado, descripcion in estados:
        print(f"📡 Estado: {estado} - {descripcion}")
        if estado == "live":
            print("✅ ¡Despliegue completado exitosamente!")
        else:
            print("⏳ Esperando siguiente estado...")

def ejemplo_configuracion_por_entorno():
    """Ejemplo de configuración por entorno (desarrollo, producción)"""
    print("\n🌍 Ejemplo de Configuración por Entorno")
    print("=" * 50)
    
    # Configuración para desarrollo
    config_desarrollo = {
        "render": {
            "api_key": "dev_api_key",
            "service_id": "dev_service_id",
            "account_id": "dev_account_id"
        },
        "deploy": {
            "exclude_patterns": [
                "__pycache__", "*.pyc", "venv", "*.log",
                "deploy_render.py", "render_config.json"
            ],
            "include_patterns": [
                "*.py", "*.html", "*.css", "templates/*"
            ],
            "backup_before_deploy": False,  # No backup en desarrollo
            "create_zip_backup": False
        },
        "paths": {
            "source": ".",
            "backup": "./backups/dev",
            "temp": "./temp/dev"
        }
    }
    
    # Configuración para producción
    config_produccion = {
        "render": {
            "api_key": "prod_api_key",
            "service_id": "prod_service_id",
            "account_id": "prod_account_id"
        },
        "deploy": {
            "exclude_patterns": [
                "__pycache__", "*.pyc", "venv", "*.log",
                "deploy_render.py", "render_config.json",
                "ejemplo_uso.py", "*.md"
            ],
            "include_patterns": [
                "*.py", "*.html", "*.css", "*.js",
                "templates/*", "static/*", "requirements.txt"
            ],
            "backup_before_deploy": True,  # Siempre backup en producción
            "create_zip_backup": True
        },
        "paths": {
            "source": ".",
            "backup": "./backups/prod",
            "temp": "./temp/prod"
        }
    }
    
    # Guardar configuraciones
    with open('render_config_desarrollo.json', 'w', encoding='utf-8') as f:
        json.dump(config_desarrollo, f, indent=4, ensure_ascii=False)
    
    with open('render_config_produccion.json', 'w', encoding='utf-8') as f:
        json.dump(config_produccion, f, indent=4, ensure_ascii=False)
    
    print("✅ Configuraciones por entorno creadas:")
    print("   📁 render_config_desarrollo.json")
    print("   📁 render_config_produccion.json")
    
    print("\n🔑 Para usar configuración de desarrollo:")
    print("   deployer = RenderDeployer('render_config_desarrollo.json')")
    
    print("\n🔑 Para usar configuración de producción:")
    print("   deployer = RenderDeployer('render_config_produccion.json')")

def main():
    """Función principal del ejemplo"""
    print("🚀 Ejemplos de Uso del Sistema de Despliegue a Render")
    print("=" * 70)
    
    # Verificar que existe el archivo principal
    if not os.path.exists('deploy_render.py'):
        print("❌ Error: No se encontró 'deploy_render.py'")
        print("   Asegúrate de ejecutar este script desde el directorio correcto")
        return
    
    try:
        # Ejecutar ejemplos
        ejemplo_configuracion_personalizada()
        ejemplo_despliegue_selectivo()
        ejemplo_backup_manual()
        ejemplo_crear_paquete()
        ejemplo_monitoreo_simulado()
        ejemplo_configuracion_por_entorno()
        
        print("\n🎉 ¡Todos los ejemplos se ejecutaron correctamente!")
        print("\n📋 Archivos creados:")
        print("   📁 render_config_personalizada.json")
        print("   📁 render_config_desarrollo.json")
        print("   📁 render_config_produccion.json")
        print("   📁 backups/")
        print("   📁 temp/")
        
        print("\n🚀 Para usar el sistema:")
        print("   1. Edita 'render_config_personalizada.json' con tus credenciales")
        print("   2. Ejecuta: python deploy_render.py")
        print("   3. O usa: python setup_deploy.py para configuración automática")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        print("   Verifica que todas las dependencias estén instaladas")

if __name__ == "__main__":
    main()
