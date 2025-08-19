#!/usr/bin/env python3
"""
Script Simple de Deploy - Solo Git
Autor: Sistema Automático
Fecha: 2025-08-18
"""

import os
import sys
import subprocess
from datetime import datetime
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deploy_simple.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SimpleDeployer:
    def __init__(self):
        self.repository_name = "mi_app_web"
        
    def check_git_status(self):
        """Verifica el estado del repositorio Git."""
        try:
            logger.info("🔍 Verificando estado del repositorio Git...")
            
            # Verificar si hay cambios pendientes
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                 capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                logger.info("📝 Cambios detectados en el repositorio:")
                for line in result.stdout.strip().split('\n'):
                    if line:
                        logger.info(f"   {line}")
                return True
            else:
                logger.info("✅ No hay cambios pendientes en el repositorio")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error verificando estado de Git: {e}")
            return False
        except FileNotFoundError:
            logger.error("❌ Git no está instalado o no está en el PATH")
            return False
    
    def check_git_remote(self):
        """Verifica que el repositorio tenga un remote configurado."""
        try:
            logger.info("🔗 Verificando configuración del repositorio remoto...")
            
            result = subprocess.run(['git', 'remote', '-v'], 
                                 capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                logger.info("✅ Repositorio remoto configurado:")
                for line in result.stdout.strip().split('\n'):
                    if line:
                        logger.info(f"   {line}")
                return True
            else:
                logger.error("❌ No hay repositorio remoto configurado")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error verificando remote: {e}")
            return False
    
    def commit_changes(self, commit_message=None):
        """Realiza commit de los cambios pendientes."""
        try:
            if not commit_message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                commit_message = f"Actualización automática - {timestamp}"
            
            logger.info(f"📝 Realizando commit: {commit_message}")
            
            # Agregar todos los cambios
            subprocess.run(['git', 'add', '.'], check=True)
            logger.info("✅ Archivos agregados al staging")
            
            # Realizar commit
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            logger.info("✅ Commit realizado exitosamente")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error realizando commit: {e}")
            return False
    
    def push_changes(self):
        """Envía los cambios al repositorio remoto."""
        try:
            logger.info("🚀 Enviando cambios al repositorio remoto...")
            
            # Obtener nombre de la rama actual
            branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                        capture_output=True, text=True, check=True)
            current_branch = branch_result.stdout.strip()
            
            logger.info(f"🌿 Rama actual: {current_branch}")
            
            # Intentar push
            result = subprocess.run(['git', 'push', 'origin', current_branch], 
                                 capture_output=True, text=True, check=True)
            
            logger.info("✅ Cambios enviados exitosamente")
            logger.info(f"📤 Output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error enviando cambios: {e}")
            if e.stderr:
                logger.error(f"📋 Error details: {e.stderr}")
            return False
    
    def show_deploy_info(self):
        """Muestra información sobre el deploy."""
        try:
            logger.info("📊 Información del Deploy:")
            logger.info("=" * 40)
            
            # Obtener información del último commit
            commit_result = subprocess.run(['git', 'log', '-1', '--oneline'], 
                                        capture_output=True, text=True, check=True)
            last_commit = commit_result.stdout.strip()
            logger.info(f"📝 Último commit: {last_commit}")
            
            # Obtener información del remote
            remote_result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                        capture_output=True, text=True, check=True)
            remote_url = remote_result.stdout.strip()
            logger.info(f"🔗 Repositorio: {remote_url}")
            
            # Obtener rama actual
            branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                        capture_output=True, text=True, check=True)
            current_branch = branch_result.stdout.strip()
            logger.info(f"🌿 Rama: {current_branch}")
            
            logger.info("=" * 40)
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ No se pudo obtener información del deploy: {e}")
    
    def deploy(self, commit_message=None):
        """Proceso completo de deploy."""
        logger.info("🚀 Iniciando proceso de deploy simple...")
        logger.info("=" * 50)
        
        # 1. Verificar configuración de Git
        if not self.check_git_remote():
            logger.error("❌ Repositorio Git no configurado correctamente")
            return False
        
        # 2. Verificar estado de Git
        if not self.check_git_status():
            logger.info("📝 No hay cambios para hacer commit")
            logger.info("✅ El repositorio está actualizado")
            return True
        
        # 3. Hacer commit de los cambios
        if not self.commit_changes(commit_message):
            logger.error("❌ Falló el commit de cambios")
            return False
        
        # 4. Enviar cambios al repositorio
        if not self.push_changes():
            logger.error("❌ Falló el envío de cambios")
            return False
        
        # 5. Mostrar información del deploy
        self.show_deploy_info()
        
        logger.info("🎉 ¡Deploy completado exitosamente!")
        logger.info("📝 Render detectará los cambios automáticamente y se desplegará")
        return True

def main():
    """Función principal del script."""
    print("🚀 Script de Deploy Simple - Solo Git")
    print("=" * 50)
    
    # Crear instancia del deployer
    deployer = SimpleDeployer()
    
    # Verificar argumentos de línea de comandos
    commit_message = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("""
Uso: python deploy_simple.py [opciones]

Opciones:
  mensaje        Mensaje personalizado para el commit
  --help         Mostrar esta ayuda

Ejemplos:
  python deploy_simple.py
  python deploy_simple.py "Mejoras en el sistema de recordatorios"
  python deploy_simple.py "Corrección de bugs en facturas"
            """)
            return
        else:
            commit_message = sys.argv[1]
            logger.info(f"📝 Mensaje de commit personalizado: {commit_message}")
    
    # Ejecutar deploy
    try:
        success = deployer.deploy(commit_message)
        
        if success:
            logger.info("🎉 ¡Deploy completado exitosamente!")
            print("\n🎉 ¡Deploy completado exitosamente!")
            print("📝 Render detectará los cambios y se desplegará automáticamente")
            print("⏱️  El despliegue en Render puede tomar 2-5 minutos")
        else:
            logger.error("❌ El deploy falló")
            print("\n❌ El deploy falló. Revisa los logs para más detalles.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Deploy cancelado por el usuario")
        print("\n⏹️ Deploy cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
