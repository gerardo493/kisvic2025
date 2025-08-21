#!/usr/bin/env python3
"""
Script de Despliegue para Render - Version Simplificada
Sube todos los archivos del sistema al hosting de Render
"""

import os
import sys
import json
import shutil
import zipfile
import requests
from pathlib import Path
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
    def __init__(self, config_file='render_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.project_root = Path.cwd()
        
    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        if not os.path.exists(self.config_file):
            logger.error(f"Archivo de configuracion {self.config_file} no encontrado")
            sys.exit(1)
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear {self.config_file}: {e}")
            sys.exit(1)
            
    def validate_config(self):
        """Valida que la configuración sea correcta"""
        required_fields = ['render', 'deploy', 'paths']
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Campo requerido '{field}' no encontrado en la configuracion")
                return False
                
        render_config = self.config['render']
        required_render_fields = ['api_key', 'service_id']
        for field in required_render_fields:
            if field not in render_config or render_config[field] == f"tu_{field}_aqui":
                logger.error(f"Campo requerido '{field}' no configurado en render")
                return False
                
        return True
        
    def create_backup(self):
        """Crea un backup del proyecto antes del despliegue"""
        if not self.config['deploy']['backup_before_deploy']:
            return
            
        backup_dir = Path(self.config['paths']['backup'])
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = backup_dir / backup_name
        
        try:
            shutil.copytree(self.project_root, backup_path, 
                           ignore=shutil.ignore_patterns('backups', 'temp', '*.log'))
            logger.info(f"Backup creado en: {backup_path}")
            
            if self.config['deploy']['create_zip_backup']:
                zip_path = backup_dir / f"{backup_name}.zip"
                self.create_zip_archive(backup_path, zip_path)
                logger.info(f"Backup comprimido en: {zip_path}")
                
        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            
    def create_zip_archive(self, source_path, zip_path):
        """Crea un archivo ZIP del directorio fuente"""
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_path)
                        zipf.write(file_path, arcname)
        except Exception as e:
            logger.error(f"Error al crear archivo ZIP: {e}")
            
    def should_include_file(self, file_path):
        """Determina si un archivo debe ser incluido en el despliegue"""
        file_path = str(file_path)
        
        # Verificar patrones de exclusión
        for pattern in self.config['deploy']['exclude_patterns']:
            if pattern in file_path:
                return False
                
        # Verificar patrones de inclusión
        for pattern in self.config['deploy']['include_patterns']:
            if pattern in file_path:
                return True
                
        return False
        
    def get_files_to_deploy(self):
        """Obtiene la lista de archivos a desplegar"""
        files_to_deploy = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Filtrar directorios excluidos
            dirs[:] = [d for d in dirs if d not in self.config['deploy']['exclude_patterns']]
            
            for file in files:
                file_path = Path(root) / file
                if self.should_include_file(file_path):
                    files_to_deploy.append(file_path)
                    
        return files_to_deploy
        
    def create_deployment_package(self):
        """Crea el paquete de despliegue"""
        temp_dir = Path(self.config['paths']['temp'])
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        
        files_to_deploy = self.get_files_to_deploy()
        logger.info(f"Preparando {len(files_to_deploy)} archivos para despliegue...")
        
        for file_path in files_to_deploy:
            try:
                # Crear estructura de directorios en temp
                relative_path = file_path.relative_to(self.project_root)
                temp_file_path = temp_dir / relative_path
                temp_file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copiar archivo
                shutil.copy2(file_path, temp_file_path)
                logger.debug(f"Archivo preparado: {relative_path}")
                
            except Exception as e:
                logger.error(f"Error al preparar {file_path}: {e}")
                
        return temp_dir
        
    def deploy_to_render(self, temp_dir):
        """Despliega los archivos a Render usando la API"""
        render_config = self.config['render']
        
        # Crear archivo ZIP del paquete de despliegue
        zip_path = temp_dir.parent / "deployment_package.zip"
        self.create_zip_archive(temp_dir, zip_path)
        
        # Headers para la API de Render
        headers = {
            'Authorization': f'Token {render_config["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Obtener información del servicio
            service_url = f"https://api.render.com/v1/services/{render_config['service_id']}"
            response = requests.get(service_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error al obtener informacion del servicio: {response.status_code}")
                logger.error(response.text)
                return False
                
            service_info = response.json()
            logger.info(f"Servicio encontrado: {service_info.get('name', 'N/A')}")
            
            # Crear un nuevo despliegue
            deploy_url = f"{service_url}/deploys"
            deploy_data = {
                'clearCache': 'do_not_clear',
                'commitId': f"manual_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            response = requests.post(deploy_url, headers=headers, json=deploy_data)
            
            if response.status_code == 201:
                deploy_info = response.json()
                deploy_id = deploy_info['id']
                logger.info(f"Despliegue iniciado con ID: {deploy_id}")
                
                # Monitorear el estado del despliegue
                return self.monitor_deployment(service_url, deploy_id, headers)
            else:
                logger.error(f"Error al iniciar despliegue: {response.status_code}")
                logger.error(response.text)
                return False
                
        except Exception as e:
            logger.error(f"Error durante el despliegue: {e}")
            return False
            
    def monitor_deployment(self, service_url, deploy_id, headers):
        """Monitorea el estado del despliegue"""
        deploy_url = f"{service_url}/deploys/{deploy_id}"
        
        logger.info("Monitoreando estado del despliegue...")
        
        while True:
            try:
                response = requests.get(deploy_url, headers=headers)
                if response.status_code == 200:
                    deploy_info = response.json()
                    status = deploy_info['status']
                    
                    logger.info(f"Estado del despliegue: {status}")
                    
                    if status in ['live', 'deployed']:
                        logger.info("DESPLIEGUE COMPLETADO EXITOSAMENTE!")
                        return True
                    elif status in ['failed', 'canceled']:
                        logger.error(f"DESPLIEGUE FALLO con estado: {status}")
                        return False
                    elif status in ['building', 'deploying']:
                        logger.info("DESPLIEGUE EN PROGRESO...")
                        import time
                        time.sleep(10)  # Esperar 10 segundos antes de verificar nuevamente
                    else:
                        logger.info(f"Estado desconocido: {status}")
                        import time
                        time.sleep(10)
                        
                else:
                    logger.error(f"Error al obtener estado del despliegue: {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"Error al monitorear despliegue: {e}")
                return False
                
    def cleanup(self):
        """Limpia archivos temporales"""
        temp_dir = Path(self.config['paths']['temp'])
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.info("Archivos temporales eliminados")
            
        # Eliminar archivo ZIP de despliegue
        zip_path = Path("deployment_package.zip")
        if zip_path.exists():
            zip_path.unlink()
            logger.info("Archivo ZIP de despliegue eliminado")
            
    def run(self):
        """Ejecuta el proceso completo de despliegue"""
        logger.info("INICIANDO DESPLIEGUE A RENDER...")
        
        # Validar configuración
        if not self.validate_config():
            logger.error("CONFIGURACION INVALIDA. Revisa el archivo de configuracion.")
            return False
            
        try:
            # Crear backup
            self.create_backup()
            
            # Crear paquete de despliegue
            temp_dir = self.create_deployment_package()
            
            # Desplegar a Render
            success = self.deploy_to_render(temp_dir)
            
            if success:
                logger.info("DESPLIEGUE COMPLETADO EXITOSAMENTE!")
            else:
                logger.error("EL DESPLIEGUE FALLO")
                
            return success
            
        except KeyboardInterrupt:
            logger.info("DESPLIEGUE CANCELADO POR EL USUARIO")
            return False
        except Exception as e:
            logger.error(f"ERROR INESPERADO durante el despliegue: {e}")
            return False
        finally:
            # Limpiar archivos temporales
            self.cleanup()

def main():
    """Función principal"""
    print("DESPLEGADOR DE RENDER")
    print("=" * 50)
    
    deployer = RenderDeployer()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--config':
        print("Archivo de configuracion creado/actualizado")
        print(f"Ubicacion: {deployer.config_file}")
        print("Por favor, edita el archivo con tus credenciales de Render")
        return
        
    success = deployer.run()
    
    if success:
        print("\nDESPLIEGUE COMPLETADO EXITOSAMENTE!")
        sys.exit(0)
    else:
        print("\nEL DESPLIEGUE FALLO")
        sys.exit(1)

if __name__ == "__main__":
    main()
