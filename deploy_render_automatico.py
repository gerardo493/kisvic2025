#!/usr/bin/env python3
"""
Script Automático para Deploy en Render
Autor: Sistema Automático
Fecha: 2025-08-18
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deploy_render.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RenderDeployer:
    def __init__(self):
        self.config_file = 'render_config.json'
        self.render_token = os.environ.get('RENDER_TOKEN')
        self.service_id = None
        self.base_url = "https://api.render.com/v1"
        self.headers = {}
        
        # Cargar configuración
        self.load_config()
        
    def load_config(self):
        """Carga la configuración desde el archivo JSON."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.service_id = config.get('service_id')
                    logger.info(f"✅ Configuración cargada: Service ID = {self.service_id}")
            else:
                logger.warning(f"⚠️ Archivo de configuración {self.config_file} no encontrado")
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
    
    def setup_headers(self):
        """Configura los headers para la API de Render."""
        if not self.render_token:
            logger.error("❌ RENDER_TOKEN no encontrado en variables de entorno")
            return False
        
        self.headers = {
            'Authorization': f'Bearer {self.render_token}',
            'Content-Type': 'application/json'
        }
        logger.info("✅ Headers configurados para API de Render")
        return True
    
    def check_git_status(self):
        """Verifica el estado del repositorio Git."""
        try:
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
            
            # Intentar push
            result = subprocess.run(['git', 'push'], 
                                 capture_output=True, text=True, check=True)
            
            logger.info("✅ Cambios enviados exitosamente")
            logger.info(f"📤 Output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error enviando cambios: {e}")
            if e.stderr:
                logger.error(f"📋 Error details: {e.stderr}")
            return False
    
    def trigger_render_deploy(self):
        """Dispara el deploy en Render manualmente."""
        if not self.service_id:
            logger.error("❌ Service ID no configurado")
            return False
        
        if not self.setup_headers():
            return False
        
        try:
            url = f"{self.base_url}/services/{self.service_id}/deploys"
            payload = {
                "clearCache": "do_not_clear"
            }
            
            logger.info(f"🚀 Disparando deploy en Render...")
            logger.info(f"📡 URL: {url}")
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 201:
                deploy_data = response.json()
                deploy_id = deploy_data.get('id')
                logger.info(f"✅ Deploy iniciado exitosamente")
                logger.info(f"🆔 Deploy ID: {deploy_id}")
                logger.info(f"📊 Estado: {deploy_data.get('status', 'N/A')}")
                return deploy_id
            else:
                logger.error(f"❌ Error iniciando deploy: {response.status_code}")
                logger.error(f"📋 Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False
    
    def monitor_deploy(self, deploy_id):
        """Monitorea el progreso del deploy."""
        if not deploy_id:
            return False
        
        logger.info(f"👀 Monitoreando deploy {deploy_id}...")
        
        max_attempts = 30  # 5 minutos máximo
        attempt = 0
        
        while attempt < max_attempts:
            try:
                url = f"{self.base_url}/services/{self.service_id}/deploys/{deploy_id}"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    deploy_data = response.json()
                    status = deploy_data.get('status')
                    
                    logger.info(f"📊 Estado del deploy: {status}")
                    
                    if status in ['live', 'deployed']:
                        logger.info("🎉 ¡Deploy completado exitosamente!")
                        return True
                    elif status in ['failed', 'canceled']:
                        logger.error(f"❌ Deploy falló con estado: {status}")
                        return False
                    elif status in ['building', 'deploying']:
                        logger.info("🔨 Deploy en progreso...")
                    else:
                        logger.info(f"⏳ Estado desconocido: {status}")
                
                time.sleep(10)  # Esperar 10 segundos
                attempt += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Error monitoreando deploy: {e}")
                attempt += 1
                time.sleep(10)
        
        logger.warning("⚠️ Tiempo de espera agotado para el deploy")
        return False
    
    def deploy(self, commit_message=None, auto_commit=True):
        """Proceso completo de deploy."""
        logger.info("🚀 Iniciando proceso de deploy automático...")
        logger.info("=" * 50)
        
        # 1. Verificar estado de Git
        if not self.check_git_status():
            if auto_commit:
                logger.info("📝 No hay cambios para hacer commit")
            else:
                logger.warning("⚠️ No se pueden hacer cambios automáticos")
                return False
        
        # 2. Hacer commit si hay cambios
        if auto_commit:
            if not self.commit_changes(commit_message):
                logger.error("❌ Falló el commit de cambios")
                return False
        
        # 3. Enviar cambios al repositorio
        if not self.push_changes():
            logger.error("❌ Falló el envío de cambios")
            return False
        
        # 4. Disparar deploy en Render
        deploy_id = self.trigger_render_deploy()
        if not deploy_id:
            logger.error("❌ Falló el disparo del deploy")
            return False
        
        # 5. Monitorear el deploy
        if self.monitor_deploy(deploy_id):
            logger.info("🎉 ¡Deploy completado exitosamente!")
            return True
        else:
            logger.error("❌ El deploy falló o no se completó")
            return False

def main():
    """Función principal del script."""
    print("🚀 Script de Deploy Automático para Render")
    print("=" * 50)
    
    # Crear instancia del deployer
    deployer = RenderDeployer()
    
    # Verificar argumentos de línea de comandos
    commit_message = None
    auto_commit = True
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-commit":
            auto_commit = False
            logger.info("🔒 Modo sin commit automático activado")
        elif sys.argv[1] == "--help":
            print("""
Uso: python deploy_render_automatico.py [opciones]

Opciones:
  --no-commit    No hacer commit automático de cambios
  --help         Mostrar esta ayuda

Ejemplos:
  python deploy_render_automatico.py
  python deploy_render_automatico.py --no-commit
            """)
            return
        else:
            commit_message = sys.argv[1]
            logger.info(f"📝 Mensaje de commit personalizado: {commit_message}")
    
    # Ejecutar deploy
    try:
        success = deployer.deploy(commit_message, auto_commit)
        
        if success:
            logger.info("🎉 ¡Deploy completado exitosamente!")
            print("\n🎉 ¡Deploy completado exitosamente!")
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
