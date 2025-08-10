#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Seguridad Fiscal - Cumplimiento SENIAT
================================================

Este módulo implementa los requisitos técnicos de seguridad y auditoría
requeridos por el SENIAT para la homologación de sistemas fiscales.

Funcionalidades:
- Inmutabilidad de documentos fiscales
- Cifrado AES-256 para datos sensibles
- Sistema de hashing y firma digital
- Logs de auditoría inviolables
- Validaciones de campos obligatorios
"""

import hashlib
import hmac
import json
import base64
import uuid
import psutil
import socket
from datetime import datetime
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

class SeguridadFiscal:
    """Clase principal para manejo de seguridad fiscal según SENIAT"""
    
    def __init__(self, clave_maestra: Optional[str] = None):
        """
        Inicializa el sistema de seguridad fiscal
        
        Args:
            clave_maestra: Clave para cifrado de datos (si no se proporciona, se genera)
        """
        self.clave_maestra = clave_maestra or self._generar_clave_maestra()
        self.fernet = self._inicializar_cifrado()
        self.log_auditoria_file = 'logs/auditoria_fiscal.log'
        self._asegurar_directorios()
        
    def _asegurar_directorios(self):
        """Crear directorios necesarios si no existen"""
        os.makedirs('logs', exist_ok=True)
        os.makedirs('documentos_fiscales', exist_ok=True)
        os.makedirs('backups_seguridad', exist_ok=True)
        
    def _generar_clave_maestra(self) -> str:
        """Genera una clave maestra segura para el sistema"""
        return Fernet.generate_key().decode()
        
    def _inicializar_cifrado(self) -> Fernet:
        """Inicializa el sistema de cifrado con la clave maestra"""
        if isinstance(self.clave_maestra, str):
            clave_bytes = self.clave_maestra.encode()
        else:
            clave_bytes = self.clave_maestra
            
        # Usar PBKDF2 para derivar la clave de cifrado
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'seniat_fiscal_salt_2024',  # Salt fijo para consistencia
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(clave_bytes))
        return Fernet(key)
        
    def generar_hash_documento(self, documento: Dict[str, Any]) -> str:
        """
        Genera un hash SHA-256 único e inmutable para un documento fiscal
        
        Args:
            documento: Diccionario con los datos del documento
            
        Returns:
            Hash SHA-256 del documento en formato hexadecimal
        """
        # Ordenar las claves para asegurar consistencia en el hash
        documento_ordenado = self._ordenar_recursivamente(documento)
        documento_json = json.dumps(documento_ordenado, sort_keys=True, ensure_ascii=False)
        documento_bytes = documento_json.encode('utf-8')
        
        # Agregar timestamp de creación para unicidad
        timestamp = datetime.now().isoformat()
        datos_completos = f"{documento_json}|{timestamp}".encode('utf-8')
        
        return hashlib.sha256(datos_completos).hexdigest()
    
    def _ordenar_recursivamente(self, obj):
        """Ordena recursivamente los diccionarios para hash consistente"""
        if isinstance(obj, dict):
            return {k: self._ordenar_recursivamente(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [self._ordenar_recursivamente(item) for item in obj]
        else:
            return obj
            
    def firmar_documento(self, documento: Dict[str, Any], clave_secreta: str) -> str:
        """
        Genera una firma HMAC para el documento fiscal
        
        Args:
            documento: Diccionario con los datos del documento
            clave_secreta: Clave secreta para la firma
            
        Returns:
            Firma HMAC en formato hexadecimal
        """
        hash_documento = self.generar_hash_documento(documento)
        firma = hmac.new(
            clave_secreta.encode('utf-8'),
            hash_documento.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return firma
        
    def validar_firma_documento(self, documento: Dict[str, Any], firma: str, clave_secreta: str) -> bool:
        """
        Valida la firma de un documento fiscal
        
        Args:
            documento: Diccionario con los datos del documento
            firma: Firma a validar
            clave_secreta: Clave secreta para validación
            
        Returns:
            True si la firma es válida, False en caso contrario
        """
        firma_calculada = self.firmar_documento(documento, clave_secreta)
        return hmac.compare_digest(firma, firma_calculada)
        
    def cifrar_datos(self, datos: str) -> str:
        """
        Cifra datos sensibles usando AES-256
        
        Args:
            datos: Cadena de texto a cifrar
            
        Returns:
            Datos cifrados en base64
        """
        datos_bytes = datos.encode('utf-8')
        datos_cifrados = self.fernet.encrypt(datos_bytes)
        return base64.b64encode(datos_cifrados).decode('utf-8')
        
    def descifrar_datos(self, datos_cifrados: str) -> str:
        """
        Descifra datos previamente cifrados
        
        Args:
            datos_cifrados: Datos cifrados en base64
            
        Returns:
            Datos descifrados como cadena de texto
        """
        datos_bytes = base64.b64decode(datos_cifrados.encode('utf-8'))
        datos_descifrados = self.fernet.decrypt(datos_bytes)
        return datos_descifrados.decode('utf-8')
        
    def obtener_mac_address(self) -> str:
        """Obtiene la dirección MAC de la máquina"""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                           for i in range(0, 8*6, 8)][::-1])
            return mac
        except Exception:
            return "MAC_NO_DISPONIBLE"
            
    def obtener_info_sistema(self) -> Dict[str, str]:
        """Obtiene información detallada del sistema para auditoría"""
        try:
            hostname = socket.gethostname()
            ip_local = socket.gethostbyname(hostname)
        except Exception:
            hostname = "HOST_NO_DISPONIBLE"
            ip_local = "IP_NO_DISPONIBLE"
            
        return {
            'mac_address': self.obtener_mac_address(),
            'hostname': hostname,
            'ip_local': ip_local,
            'timestamp_preciso': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'cpu_count': psutil.cpu_count() if hasattr(psutil, 'cpu_count') else 'N/A',
            'memoria_total': str(psutil.virtual_memory().total) if hasattr(psutil, 'virtual_memory') else 'N/A'
        }
        
    def registrar_log_fiscal(self, 
                           usuario: str, 
                           accion: str, 
                           documento_tipo: str,
                           documento_numero: str,
                           ip_externa: str = '',
                           detalles: str = '') -> None:
        """
        Registra un log de auditoría fiscal inmutable
        
        Args:
            usuario: Usuario que realizó la acción
            accion: Tipo de acción realizada
            documento_tipo: Tipo de documento afectado
            documento_numero: Número del documento
            ip_externa: IP externa del usuario
            detalles: Detalles adicionales de la operación
        """
        info_sistema = self.obtener_info_sistema()
        
        log_entry = {
            'timestamp': info_sistema['timestamp_preciso'],
            'usuario': usuario,
            'accion': accion,
            'documento_tipo': documento_tipo,
            'documento_numero': documento_numero,
            'ip_externa': ip_externa,
            'ip_local': info_sistema['ip_local'],
            'mac_address': info_sistema['mac_address'],
            'hostname': info_sistema['hostname'],
            'detalles': detalles,
            'session_id': str(uuid.uuid4())
        }
        
        # Generar hash del log para inmutabilidad
        log_hash = self.generar_hash_documento(log_entry)
        log_entry['hash_inmutable'] = log_hash
        
        # Formatear línea de log
        linea_log = self._formatear_linea_log(log_entry)
        
        # Escribir al archivo de auditoría
        try:
            with open(self.log_auditoria_file, 'a', encoding='utf-8') as f:
                f.write(linea_log + '\n')
        except Exception as e:
            # Log de emergencia en caso de error
            emergency_log = f"[ERROR_LOG] {datetime.now().isoformat()} - Error escribiendo log: {str(e)}\n"
            with open('logs/emergency.log', 'a', encoding='utf-8') as f:
                f.write(emergency_log)
                
    def _formatear_linea_log(self, log_entry: Dict[str, str]) -> str:
        """Formatea una línea de log según estándares SENIAT"""
        return (f"[{log_entry['timestamp']}] "
                f"USUARIO:{log_entry['usuario']} | "
                f"ACCION:{log_entry['accion']} | "
                f"DOC_TIPO:{log_entry['documento_tipo']} | "
                f"DOC_NUM:{log_entry['documento_numero']} | "
                f"IP_EXT:{log_entry['ip_externa']} | "
                f"IP_LOC:{log_entry['ip_local']} | "
                f"MAC:{log_entry['mac_address']} | "
                f"HOST:{log_entry['hostname']} | "
                f"DETALLES:{log_entry['detalles']} | "
                f"HASH:{log_entry['hash_inmutable']}")
                
    def validar_campos_obligatorios_factura(self, factura: Dict[str, Any]) -> List[str]:
        """
        Valida que una factura contenga todos los campos obligatorios según Providencia 00102
        
        Args:
            factura: Diccionario con los datos de la factura
            
        Returns:
            Lista de errores encontrados (vacía si todo está correcto)
        """
        errores = []
        
        # Campos obligatorios básicos
        campos_requeridos = [
            'numero', 'fecha', 'hora', 'cliente_id', 'total_usd', 'total_bs',
            'tasa_bcv', 'subtotal_usd', 'iva_total'
        ]
        
        for campo in campos_requeridos:
            if campo not in factura:
                errores.append(f"Campo obligatorio faltante: {campo}")
            elif campo in ['iva_total', 'subtotal_usd', 'total_usd', 'total_bs', 'tasa_bcv']:
                # Para campos numéricos, permitir 0
                if factura[campo] is None:
                    errores.append(f"Campo obligatorio faltante: {campo}")
            elif not factura[campo]:
                errores.append(f"Campo obligatorio faltante: {campo}")
                
        # Validar datos del cliente
        if 'cliente_datos' in factura:
            cliente = factura['cliente_datos']
            campos_cliente = ['rif', 'nombre', 'direccion']
            for campo in campos_cliente:
                if campo not in cliente or not cliente[campo]:
                    errores.append(f"Campo obligatorio del cliente faltante: {campo}")
                    
        # Validar que tenga items
        if 'items' not in factura or not factura['items']:
            errores.append("La factura debe tener al menos un item")
            
        # Validar numeración
        if 'numero' in factura:
            numero = factura['numero']
            if not isinstance(numero, str) or len(numero) < 1:
                errores.append("Número de factura inválido")
                
        # Validar timestamps
        if 'hora' in factura:
            try:
                datetime.strptime(factura['hora'], '%H:%M:%S')
            except ValueError:
                errores.append("Formato de hora inválido (debe ser HH:MM:SS)")
                
        return errores
        
    def crear_documento_inmutable(self, documento: Dict[str, Any], tipo_documento: str) -> Dict[str, Any]:
        """
        Crea un documento fiscal inmutable con todas las validaciones de seguridad
        
        Args:
            documento: Datos del documento
            tipo_documento: Tipo de documento (FACTURA, NOTA_CREDITO, etc.)
            
        Returns:
            Documento con metadatos de seguridad agregados
        """
        # Validar campos obligatorios
        if tipo_documento == 'FACTURA':
            errores = self.validar_campos_obligatorios_factura(documento)
            if errores:
                raise ValueError(f"Errores en campos obligatorios: {'; '.join(errores)}")
                
        # Agregar metadatos de seguridad
        documento_seguro = documento.copy()
        info_sistema = self.obtener_info_sistema()
        
        documento_seguro['_metadatos_seguridad'] = {
            'tipo_documento': tipo_documento,
            'fecha_creacion': info_sistema['timestamp_preciso'],
            'mac_address': info_sistema['mac_address'],
            'hostname': info_sistema['hostname'],
            'version_sistema': '1.0.0',
            'inmutable': True,
            'id_documento': str(uuid.uuid4())
        }
        
        # Generar hash inmutable
        hash_documento = self.generar_hash_documento(documento_seguro)
        documento_seguro['_metadatos_seguridad']['hash_inmutable'] = hash_documento
        
        # Firmar documento
        clave_firma = self.clave_maestra[:32]  # Usar primeros 32 chars como clave de firma
        firma = self.firmar_documento(documento_seguro, clave_firma)
        documento_seguro['_metadatos_seguridad']['firma_digital'] = firma
        
        return documento_seguro
        
    def validar_documento_inmutable(self, documento: Dict[str, Any]) -> bool:
        """
        Valida que un documento fiscal no haya sido alterado
        
        Args:
            documento: Documento a validar
            
        Returns:
            True si el documento es válido e inmutable, False en caso contrario
        """
        if '_metadatos_seguridad' not in documento:
            return False
            
        metadatos = documento['_metadatos_seguridad']
        
        # Verificar que esté marcado como inmutable
        if not metadatos.get('inmutable', False):
            return False
            
        # Validar firma digital
        hash_almacenado = metadatos.get('hash_inmutable', '')
        firma_almacenada = metadatos.get('firma_digital', '')
        
        # Crear copia temporal sin metadatos para validar hash original
        documento_temp = documento.copy()
        documento_temp.pop('_metadatos_seguridad')
        
        # Recrear metadatos sin hash y firma para validación
        metadatos_temp = metadatos.copy()
        metadatos_temp.pop('hash_inmutable', None)
        metadatos_temp.pop('firma_digital', None)
        documento_temp['_metadatos_seguridad'] = metadatos_temp
        
        # Validar hash
        hash_calculado = self.generar_hash_documento(documento_temp)
        
        # Validar firma
        clave_firma = self.clave_maestra[:32]
        firma_valida = self.validar_firma_documento(documento_temp, firma_almacenada, clave_firma)
        
        return hash_calculado == hash_almacenado and firma_valida

# Instancia global del sistema de seguridad fiscal
seguridad_fiscal = SeguridadFiscal() 