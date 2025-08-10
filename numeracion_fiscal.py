#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Numeración Fiscal - Cumplimiento SENIAT
================================================

Este módulo maneja la numeración consecutiva y única de documentos fiscales
según los requisitos del SENIAT para homologación.

Funcionalidades:
- Numeración consecutiva garantizada
- Validación de secuencias
- Prevención de duplicados
- Control de series por tipo de documento
- Auditoría de numeración
"""

import json
import os
import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from seguridad_fiscal import seguridad_fiscal

class ControlNumeracionFiscal:
    """Clase para controlar la numeración consecutiva de documentos fiscales"""
    
    def __init__(self, archivo_control: str = 'control_numeracion_fiscal.json'):
        """
        Inicializa el sistema de control de numeración
        
        Args:
            archivo_control: Archivo donde se almacena el control de numeración
        """
        self.archivo_control = archivo_control
        self._lock = threading.Lock()
        self._asegurar_archivo_control()
        
    def _asegurar_archivo_control(self):
        """Asegura que existe el archivo de control de numeración"""
        if not os.path.exists(self.archivo_control):
            estructura_inicial = {
                "series": {
                    "FACTURA": {
                        "prefijo": "FAC-",
                        "siguiente_numero": 1,
                        "longitud_numero": 8,
                        "formato": "FAC-{numero:08d}",
                        "activa": True,
                        "fecha_inicio": datetime.now().isoformat(),
                        "ultimo_numero_emitido": 0,
                        "total_documentos": 0
                    },
                    "NOTA_CREDITO": {
                        "prefijo": "NC-",
                        "siguiente_numero": 1,
                        "longitud_numero": 8,
                        "formato": "NC-{numero:08d}",
                        "activa": True,
                        "fecha_inicio": datetime.now().isoformat(),
                        "ultimo_numero_emitido": 0,
                        "total_documentos": 0
                    },
                    "NOTA_DEBITO": {
                        "prefijo": "ND-",
                        "siguiente_numero": 1,
                        "longitud_numero": 8,
                        "formato": "ND-{numero:08d}",
                        "activa": True,
                        "fecha_inicio": datetime.now().isoformat(),
                        "ultimo_numero_emitido": 0,
                        "total_documentos": 0
                    }
                },
                "configuracion": {
                    "validar_consecutivos": True,
                    "permitir_saltos": False,
                    "reinicio_anual": False,
                    "longitud_minima": 8,
                    "prefijo_obligatorio": True
                },
                "auditoria": {
                    "fecha_creacion": datetime.now().isoformat(),
                    "ultima_modificacion": datetime.now().isoformat(),
                    "total_documentos_emitidos": 0
                }
            }
            
            with open(self.archivo_control, 'w', encoding='utf-8') as f:
                json.dump(estructura_inicial, f, indent=2, ensure_ascii=False)
                
    def _cargar_control(self) -> Dict[str, Any]:
        """Carga el archivo de control de numeración"""
        try:
            with open(self.archivo_control, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Error cargando control de numeración: {str(e)}")
            
    def _guardar_control(self, control: Dict[str, Any]) -> None:
        """Guarda el archivo de control de numeración"""
        try:
            control['auditoria']['ultima_modificacion'] = datetime.now().isoformat()
            with open(self.archivo_control, 'w', encoding='utf-8') as f:
                json.dump(control, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Error guardando control de numeración: {str(e)}")
            
    def obtener_siguiente_numero(self, tipo_documento: str, usuario: str = '') -> Tuple[str, int]:
        """
        Obtiene el siguiente número consecutivo para un tipo de documento
        
        Args:
            tipo_documento: Tipo de documento (FACTURA, NOTA_CREDITO, NOTA_DEBITO)
            usuario: Usuario que solicita el número
            
        Returns:
            Tuple con (número_formateado, numero_secuencial)
            
        Raises:
            Exception: Si hay error en la numeración o validación
        """
        with self._lock:  # Asegurar atomicidad
            control = self._cargar_control()
            
            if tipo_documento not in control['series']:
                raise ValueError(f"Tipo de documento '{tipo_documento}' no válido")
                
            serie = control['series'][tipo_documento]
            
            if not serie['activa']:
                raise ValueError(f"Serie '{tipo_documento}' está inactiva")
                
            # Obtener el siguiente número
            numero_secuencial = serie['siguiente_numero']
            numero_formateado = serie['formato'].format(numero=numero_secuencial)
            
            # Validar que no exista ya (doble verificación)
            if self._numero_existe(numero_formateado, tipo_documento):
                raise Exception(f"Error crítico: Número {numero_formateado} ya existe")
                
            # Actualizar el control
            serie['siguiente_numero'] += 1
            serie['ultimo_numero_emitido'] = numero_secuencial
            serie['total_documentos'] += 1
            
            control['auditoria']['total_documentos_emitidos'] += 1
            
            # Guardar cambios
            self._guardar_control(control)
            
            # Registrar en log de auditoría
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario or 'SISTEMA',
                accion='ASIGNACION_NUMERO',
                documento_tipo=tipo_documento,
                documento_numero=numero_formateado,
                detalles=f'Número asignado: {numero_formateado} (secuencial: {numero_secuencial})'
            )
            
            return numero_formateado, numero_secuencial
            
    def _numero_existe(self, numero: str, tipo_documento: str) -> bool:
        """
        Verifica si un número ya existe en el sistema
        
        Args:
            numero: Número a verificar
            tipo_documento: Tipo de documento
            
        Returns:
            True si el número ya existe, False en caso contrario
        """
        # Aquí se debería verificar en todas las fuentes de datos
        # Por ahora verificamos en facturas JSON
        try:
            # Verificar en facturas existentes
            if tipo_documento == 'FACTURA':
                facturas_file = 'facturas_json/facturas.json'
                if os.path.exists(facturas_file):
                    with open(facturas_file, 'r', encoding='utf-8') as f:
                        facturas = json.load(f)
                        for factura in facturas.values():
                            if factura.get('numero') == numero:
                                return True
                                
            # TODO: Verificar en notas de crédito y débito cuando se implementen
            return False
        except Exception:
            # En caso de error, asumir que existe para evitar duplicados
            return True
            
    def validar_numero_consecutivo(self, numero: str, tipo_documento: str) -> bool:
        """
        Valida que un número sea consecutivo válido
        
        Args:
            numero: Número a validar
            tipo_documento: Tipo de documento
            
        Returns:
            True si el número es válido y consecutivo
        """
        try:
            control = self._cargar_control()
            
            if tipo_documento not in control['series']:
                return False
                
            serie = control['series'][tipo_documento]
            
            # Extraer número secuencial del formato
            if numero.startswith(serie['prefijo']):
                numero_str = numero[len(serie['prefijo']):]
                numero_secuencial = int(numero_str)
                
                # Validar que sea el siguiente número esperado
                return numero_secuencial == serie['siguiente_numero']
            else:
                return False
                
        except Exception:
            return False
            
    def obtener_estado_numeracion(self, tipo_documento: str = None) -> Dict[str, Any]:
        """
        Obtiene el estado actual de la numeración
        
        Args:
            tipo_documento: Tipo específico o None para todos
            
        Returns:
            Diccionario con el estado de numeración
        """
        control = self._cargar_control()
        
        if tipo_documento:
            if tipo_documento in control['series']:
                return {
                    tipo_documento: control['series'][tipo_documento],
                    'configuracion': control['configuracion']
                }
            else:
                return {}
        else:
            return control
            
    def marcar_numero_utilizado(self, numero: str, tipo_documento: str, usuario: str = '') -> bool:
        """
        Marca un número como utilizado definitivamente
        
        Args:
            numero: Número utilizado
            tipo_documento: Tipo de documento
            usuario: Usuario que utilizó el número
            
        Returns:
            True si se marcó correctamente
        """
        try:
            # Registrar uso en log de auditoría
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario or 'SISTEMA',
                accion='NUMERO_UTILIZADO',
                documento_tipo=tipo_documento,
                documento_numero=numero,
                detalles=f'Número confirmado como utilizado: {numero}'
            )
            
            return True
        except Exception as e:
            print(f"Error marcando número utilizado: {str(e)}")
            return False
            
    def reservar_rango_numeros(self, tipo_documento: str, cantidad: int, usuario: str = '') -> Dict[str, Any]:
        """
        Reserva un rango de números consecutivos (para procesamiento por lotes)
        
        Args:
            tipo_documento: Tipo de documento
            cantidad: Cantidad de números a reservar
            usuario: Usuario que reserva
            
        Returns:
            Diccionario con los números reservados
        """
        if cantidad <= 0 or cantidad > 1000:  # Límite de seguridad
            raise ValueError("Cantidad debe estar entre 1 y 1000")
            
        with self._lock:
            control = self._cargar_control()
            
            if tipo_documento not in control['series']:
                raise ValueError(f"Tipo de documento '{tipo_documento}' no válido")
                
            serie = control['series'][tipo_documento]
            inicio = serie['siguiente_numero']
            fin = inicio + cantidad - 1
            
            numeros_reservados = []
            for i in range(inicio, fin + 1):
                numero_formateado = serie['formato'].format(numero=i)
                numeros_reservados.append(numero_formateado)
                
            # Actualizar control
            serie['siguiente_numero'] = fin + 1
            serie['total_documentos'] += cantidad
            control['auditoria']['total_documentos_emitidos'] += cantidad
            
            self._guardar_control(control)
            
            # Registrar reserva
            seguridad_fiscal.registrar_log_fiscal(
                usuario=usuario or 'SISTEMA',
                accion='RESERVA_NUMEROS',
                documento_tipo=tipo_documento,
                documento_numero=f'{numeros_reservados[0]}-{numeros_reservados[-1]}',
                detalles=f'Reservados {cantidad} números desde {inicio} hasta {fin}'
            )
            
            return {
                'tipo_documento': tipo_documento,
                'numeros_reservados': numeros_reservados,
                'inicio': inicio,
                'fin': fin,
                'cantidad': cantidad,
                'fecha_reserva': datetime.now().isoformat()
            }

# Instancia global del controlador de numeración
control_numeracion = ControlNumeracionFiscal() 