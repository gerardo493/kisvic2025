#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Comunicación SENIAT - Cumplimiento Fiscal
==================================================

Este módulo maneja la comunicación directa con las APIs del SENIAT
para el envío automático de documentos fiscales y cumplimiento de 
los requisitos de homologación.

Funcionalidades:
- Envío de facturas al SENIAT
- Envío de notas de crédito/débito
- Consulta de estatus de documentos
- Manejo de respuestas y errores
- Verificación de conectividad
- Sistema de reintentos automáticos
"""

import json
import requests
import time
import ssl
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from seguridad_fiscal import seguridad_fiscal

class ComunicacionSENIAT:
    """Clase para manejar la comunicación con las APIs del SENIAT"""
    
    def __init__(self, configuracion: Optional[Dict[str, Any]] = None):
        """
        Inicializa el módulo de comunicación SENIAT
        
        Args:
            configuracion: Diccionario con configuración específica
        """
        # URLs base del SENIAT (URLs reales deben obtenerse del SENIAT)
        self.config = configuracion or self._cargar_configuracion_default()
        
        # Configurar sesión HTTP con SSL/TLS
        self.session = requests.Session()
        self.session.verify = True  # Verificar certificados SSL
        
        # Headers por defecto
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'SistemaFiscal/1.0.0 SENIAT-Compliant'
        }
        
        # Estado de conectividad
        self.conectado = False
        self.ultima_conexion = None
        self.errores_consecutivos = 0
        
    def _cargar_configuracion_default(self) -> Dict[str, Any]:
        """Carga configuración por defecto para SENIAT"""
        return {
            # URLs del SENIAT (estas son URLs de ejemplo - usar las reales del SENIAT)
            'url_base': 'https://api.seniat.gob.ve/fiscal/v1/',
            'url_facturas': 'documentos/facturas',
            'url_notas_credito': 'documentos/notas-credito',
            'url_notas_debito': 'documentos/notas-debito',
            'url_consulta': 'consultas/documento',
            'url_estatus': 'sistema/estatus',
            
            # Configuración de seguridad
            'certificado_cliente': 'certs/cliente.pem',
            'clave_privada': 'certs/cliente.key',
            'certificado_ca': 'certs/seniat_ca.pem',
            
            # Configuración de empresa (debe ser proporcionada por el SENIAT)
            'rif_empresa': '',
            'codigo_contribuyente': '',
            'token_api': '',
            'ambiente': 'produccion',  # 'pruebas' o 'produccion'
            
            # Configuración de reintentos
            'max_reintentos': 3,
            'tiempo_espera': 30,  # segundos
            'timeout_conexion': 60,  # segundos
            
            # Configuración de logs
            'log_requests': True,
            'log_responses': True
        }
        
    def configurar_empresa(self, rif: str, codigo_contribuyente: str, token_api: str) -> None:
        """
        Configura los datos de la empresa para comunicación con SENIAT
        
        Args:
            rif: RIF de la empresa
            codigo_contribuyente: Código de contribuyente asignado por SENIAT
            token_api: Token de API proporcionado por SENIAT
        """
        self.config['rif_empresa'] = rif
        self.config['codigo_contribuyente'] = codigo_contribuyente
        self.config['token_api'] = token_api
        
        # Actualizar headers de autenticación
        self.headers['Authorization'] = f'Bearer {token_api}'
        self.headers['X-RIF-Empresa'] = rif
        self.headers['X-Codigo-Contribuyente'] = codigo_contribuyente
        
    def verificar_conectividad(self) -> bool:
        """
        Verifica la conectividad con los servicios del SENIAT
        
        Returns:
            True si hay conectividad, False en caso contrario
        """
        try:
            url = urljoin(self.config['url_base'], self.config['url_estatus'])
            
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=self.config['timeout_conexion']
            )
            
            if response.status_code == 200:
                self.conectado = True
                self.ultima_conexion = datetime.now()
                self.errores_consecutivos = 0
                
                # Registrar conectividad exitosa
                seguridad_fiscal.registrar_log_fiscal(
                    usuario='SISTEMA',
                    accion='VERIFICAR_CONECTIVIDAD_SENIAT',
                    documento_tipo='SISTEMA',
                    documento_numero='N/A',
                    detalles='Conectividad con SENIAT verificada exitosamente'
                )
                
                return True
            else:
                self.conectado = False
                self.errores_consecutivos += 1
                return False
                
        except Exception as e:
            self.conectado = False
            self.errores_consecutivos += 1
            
            # Registrar error de conectividad
            seguridad_fiscal.registrar_log_fiscal(
                usuario='SISTEMA',
                accion='ERROR_CONECTIVIDAD_SENIAT',
                documento_tipo='SISTEMA',
                documento_numero='N/A',
                detalles=f'Error de conectividad: {str(e)}'
            )
            
            return False
            
    def enviar_factura(self, factura: Dict[str, Any], usuario: str = 'SISTEMA') -> Dict[str, Any]:
        """
        Envía una factura al SENIAT
        
        Args:
            factura: Diccionario con los datos de la factura
            usuario: Usuario que envía la factura
            
        Returns:
            Diccionario con el resultado del envío
        """
        return self._enviar_documento(factura, 'FACTURA', self.config['url_facturas'], usuario)
        
    def enviar_nota_credito(self, nota: Dict[str, Any], usuario: str = 'SISTEMA') -> Dict[str, Any]:
        """
        Envía una nota de crédito al SENIAT
        
        Args:
            nota: Diccionario con los datos de la nota de crédito
            usuario: Usuario que envía la nota
            
        Returns:
            Diccionario con el resultado del envío
        """
        return self._enviar_documento(nota, 'NOTA_CREDITO', self.config['url_notas_credito'], usuario)
        
    def enviar_nota_debito(self, nota: Dict[str, Any], usuario: str = 'SISTEMA') -> Dict[str, Any]:
        """
        Envía una nota de débito al SENIAT
        
        Args:
            nota: Diccionario con los datos de la nota de débito
            usuario: Usuario que envía la nota
            
        Returns:
            Diccionario con el resultado del envío
        """
        return self._enviar_documento(nota, 'NOTA_DEBITO', self.config['url_notas_debito'], usuario)
        
    def _enviar_documento(self, documento: Dict[str, Any], tipo: str, endpoint: str, usuario: str) -> Dict[str, Any]:
        """
        Método interno para enviar documentos al SENIAT
        
        Args:
            documento: Documento a enviar
            tipo: Tipo de documento
            endpoint: Endpoint de la API
            usuario: Usuario que envía
            
        Returns:
            Resultado del envío
        """
        numero_documento = documento.get('numero', 'N/A')
        
        try:
            # Verificar conectividad antes del envío
            if not self.verificar_conectividad():
                return {
                    'exito': False,
                    'error': 'No hay conectividad con SENIAT',
                    'codigo_error': 'CONECTIVIDAD_ERROR',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Preparar payload según especificaciones SENIAT
            payload = self._preparar_payload_seniat(documento, tipo)
            
            # URL completa
            url = urljoin(self.config['url_base'], endpoint)
            
            # Intentar envío con reintentos
            for intento in range(self.config['max_reintentos']):
                try:
                    # Registrar intento de envío
                    seguridad_fiscal.registrar_log_fiscal(
                        usuario=usuario,
                        accion=f'ENVIO_SENIAT_{tipo}',
                        documento_tipo=tipo,
                        documento_numero=numero_documento,
                        detalles=f'Intento {intento + 1}/{self.config["max_reintentos"]} - Enviando a {url}'
                    )
                    
                    response = self.session.post(
                        url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.config['timeout_conexion']
                    )
                    
                    # Procesar respuesta
                    resultado = self._procesar_respuesta_seniat(response, tipo, numero_documento, usuario)
                    
                    if resultado['exito']:
                        return resultado
                    else:
                        # Si es error no recuperable, no reintentar
                        if resultado.get('codigo_error') in ['DOCUMENTO_DUPLICADO', 'FORMATO_INVALIDO']:
                            return resultado
                            
                except requests.exceptions.RequestException as e:
                    if intento == self.config['max_reintentos'] - 1:
                        # Último intento fallido
                        seguridad_fiscal.registrar_log_fiscal(
                            usuario=usuario,
                            accion=f'ERROR_ENVIO_SENIAT_{tipo}',
                            documento_tipo=tipo,
                            documento_numero=numero_documento,
                            detalles=f'Error después de {self.config["max_reintentos"]} intentos: {str(e)}'
                        )
                        
                        return {
                            'exito': False,
                            'error': f'Error de comunicación: {str(e)}',
                            'codigo_error': 'COMUNICACION_ERROR',
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        # Esperar antes del siguiente intento
                        time.sleep(self.config['tiempo_espera'])
                        
        except Exception as e:
            # Error inesperado
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario,
                accion=f'ERROR_CRITICO_SENIAT_{tipo}',
                documento_tipo=tipo,
                documento_numero=numero_documento,
                detalles=f'Error crítico: {str(e)}'
            )
            
            return {
                'exito': False,
                'error': f'Error crítico: {str(e)}',
                'codigo_error': 'ERROR_CRITICO',
                'timestamp': datetime.now().isoformat()
            }
            
    def _preparar_payload_seniat(self, documento: Dict[str, Any], tipo: str) -> Dict[str, Any]:
        """
        Prepara el payload según las especificaciones del SENIAT
        
        Args:
            documento: Documento a enviar
            tipo: Tipo de documento
            
        Returns:
            Payload formateado para SENIAT
        """
        # Estructura base según especificaciones SENIAT
        payload = {
            'empresa': {
                'rif': self.config['rif_empresa'],
                'codigo_contribuyente': self.config['codigo_contribuyente']
            },
            'documento': {
                'tipo': tipo,
                'numero': documento.get('numero'),
                'fecha': documento.get('fecha'),
                'hora': documento.get('hora'),
                'timestamp_creacion': documento.get('timestamp_creacion'),
                'moneda_principal': documento.get('moneda_principal', 'USD'),
                'tasa_cambio': documento.get('tasa_bcv')
            },
            'cliente': documento.get('cliente_datos', {}),
            'items': documento.get('items', []),
            'totales': {
                'subtotal_usd': documento.get('subtotal_usd'),
                'subtotal_bs': documento.get('subtotal_bs'),
                'descuento_total': documento.get('descuento_total'),
                'iva_total': documento.get('iva_total'),
                'total_usd': documento.get('total_usd'),
                'total_bs': documento.get('total_bs')
            },
            'metadatos_seguridad': documento.get('_metadatos_seguridad', {})
        }
        
        # Campos específicos según tipo de documento
        if tipo == 'NOTA_CREDITO' or tipo == 'NOTA_DEBITO':
            payload['documento_referencia'] = {
                'tipo': 'FACTURA',
                'numero': documento.get('factura_referencia_numero'),
                'fecha': documento.get('factura_referencia_fecha')
            }
            payload['motivo'] = documento.get('motivo', '')
            
        return payload
        
    def _procesar_respuesta_seniat(self, response: requests.Response, tipo: str, numero: str, usuario: str) -> Dict[str, Any]:
        """
        Procesa la respuesta del SENIAT
        
        Args:
            response: Respuesta HTTP del SENIAT
            tipo: Tipo de documento
            numero: Número de documento
            usuario: Usuario que envió
            
        Returns:
            Resultado procesado
        """
        try:
            if response.status_code == 200:
                data = response.json()
                
                # Respuesta exitosa
                seguridad_fiscal.registrar_log_fiscal(
                    usuario=usuario,
                    accion=f'EXITO_ENVIO_SENIAT_{tipo}',
                    documento_tipo=tipo,
                    documento_numero=numero,
                    detalles=f'Documento enviado exitosamente. ID SENIAT: {data.get("id_seniat", "N/A")}'
                )
                
                return {
                    'exito': True,
                    'id_seniat': data.get('id_seniat'),
                    'codigo_control': data.get('codigo_control'),
                    'fecha_procesamiento': data.get('fecha_procesamiento'),
                    'mensaje': data.get('mensaje', 'Documento procesado exitosamente'),
                    'timestamp': datetime.now().isoformat()
                }
                
            elif response.status_code == 400:
                # Error de validación
                data = response.json() if response.content else {}
                error_msg = data.get('mensaje', 'Error de validación')
                
                seguridad_fiscal.registrar_log_fiscal(
                    usuario=usuario,
                    accion=f'ERROR_VALIDACION_SENIAT_{tipo}',
                    documento_tipo=tipo,
                    documento_numero=numero,
                    detalles=f'Error de validación: {error_msg}'
                )
                
                return {
                    'exito': False,
                    'error': error_msg,
                    'codigo_error': 'VALIDACION_ERROR',
                    'detalles_error': data.get('detalles', []),
                    'timestamp': datetime.now().isoformat()
                }
                
            elif response.status_code == 409:
                # Documento duplicado
                seguridad_fiscal.registrar_log_fiscal(
                    usuario=usuario,
                    accion=f'DOCUMENTO_DUPLICADO_SENIAT_{tipo}',
                    documento_tipo=tipo,
                    documento_numero=numero,
                    detalles='Documento ya existe en SENIAT'
                )
                
                return {
                    'exito': False,
                    'error': 'Documento ya existe en SENIAT',
                    'codigo_error': 'DOCUMENTO_DUPLICADO',
                    'timestamp': datetime.now().isoformat()
                }
                
            else:
                # Otros errores HTTP
                seguridad_fiscal.registrar_log_fiscal(
                    usuario=usuario,
                    accion=f'ERROR_HTTP_SENIAT_{tipo}',
                    documento_tipo=tipo,
                    documento_numero=numero,
                    detalles=f'Error HTTP {response.status_code}: {response.text[:200]}'
                )
                
                return {
                    'exito': False,
                    'error': f'Error HTTP {response.status_code}',
                    'codigo_error': f'HTTP_{response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            # Error procesando respuesta
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario,
                accion=f'ERROR_PROCESAMIENTO_RESPUESTA_SENIAT_{tipo}',
                documento_tipo=tipo,
                documento_numero=numero,
                detalles=f'Error procesando respuesta: {str(e)}'
            )
            
            return {
                'exito': False,
                'error': f'Error procesando respuesta: {str(e)}',
                'codigo_error': 'PROCESAMIENTO_ERROR',
                'timestamp': datetime.now().isoformat()
            }
            
    def consultar_documento(self, numero: str, tipo: str) -> Dict[str, Any]:
        """
        Consulta el estatus de un documento en SENIAT
        
        Args:
            numero: Número del documento
            tipo: Tipo de documento
            
        Returns:
            Estatus del documento
        """
        try:
            url = urljoin(self.config['url_base'], self.config['url_consulta'])
            params = {
                'numero': numero,
                'tipo': tipo,
                'rif_empresa': self.config['rif_empresa']
            }
            
            response = self.session.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.config['timeout_conexion']
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'error': f'Error consultando documento: HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'error': f'Error en consulta: {str(e)}'
            }
            
    def obtener_configuracion_actual(self) -> Dict[str, Any]:
        """Obtiene la configuración actual (sin datos sensibles)"""
        config_safe = self.config.copy()
        
        # Ocultar datos sensibles
        if 'token_api' in config_safe:
            config_safe['token_api'] = '*' * 10 + config_safe['token_api'][-4:] if config_safe['token_api'] else ''
            
        return {
            'configuracion': config_safe,
            'estado_conexion': {
                'conectado': self.conectado,
                'ultima_conexion': self.ultima_conexion.isoformat() if self.ultima_conexion else None,
                'errores_consecutivos': self.errores_consecutivos
            }
        }

# Instancia global del comunicador SENIAT
comunicador_seniat = ComunicacionSENIAT() 