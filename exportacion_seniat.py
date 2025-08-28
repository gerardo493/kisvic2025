#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Exportación SENIAT - Cumplimiento Fiscal
=================================================

Este módulo maneja la exportación de datos fiscales en formatos estándar
(CSV, XML) para auditorías y consultas del SENIAT.

Funcionalidades:
- Exportación de facturas en CSV/XML
- Exportación de logs de auditoría
- Generación de reportes consolidados
- Validación de integridad de datos
- Filtros por fecha y tipo de documento
- Compresión de archivos grandes
"""

import json
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import zipfile
import os
import io
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from seguridad_fiscal import seguridad_fiscal

class ExportacionSENIAT:
    """Clase para manejar exportaciones de datos fiscales para SENIAT"""
    
    def __init__(self):
        """Inicializa el exportador SENIAT"""
        self.formatos_soportados = ['csv', 'xml', 'json']
        self.directorio_exportacion = 'exportaciones_seniat'
        self._asegurar_directorio()
        
    def _asegurar_directorio(self):
        """Asegura que existe el directorio de exportaciones"""
        os.makedirs(self.directorio_exportacion, exist_ok=True)
        
    def exportar_facturas(self, 
                         fecha_desde: str = None, 
                         fecha_hasta: str = None,
                         formato: str = 'csv',
                         incluir_metadatos: bool = True) -> Dict[str, Any]:
        """
        Exporta facturas en el formato especificado
        
        Args:
            fecha_desde: Fecha de inicio (YYYY-MM-DD)
            fecha_hasta: Fecha de fin (YYYY-MM-DD) 
            formato: Formato de exportación (csv, xml, json)
            incluir_metadatos: Si incluir metadatos de seguridad
            
        Returns:
            Información sobre la exportación realizada
        """
        if formato not in self.formatos_soportados:
            raise ValueError(f"Formato {formato} no soportado. Use: {', '.join(self.formatos_soportados)}")
            
        # Cargar facturas
        facturas = self._cargar_facturas_filtradas(fecha_desde, fecha_hasta)
        
        if not facturas:
            return {
                'exito': False,
                'mensaje': 'No se encontraron facturas en el rango especificado',
                'total_registros': 0
            }
            
        # Generar nombre de archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        rango_fechas = f"{fecha_desde or 'inicio'}_{fecha_hasta or 'fin'}"
        nombre_archivo = f"facturas_seniat_{rango_fechas}_{timestamp}.{formato}"
        ruta_archivo = os.path.join(self.directorio_exportacion, nombre_archivo)
        
        try:
            if formato == 'csv':
                self._exportar_facturas_csv(facturas, ruta_archivo, incluir_metadatos)
            elif formato == 'xml':
                self._exportar_facturas_xml(facturas, ruta_archivo, incluir_metadatos)
            elif formato == 'json':
                self._exportar_facturas_json(facturas, ruta_archivo, incluir_metadatos)
                
            # Registrar exportación en logs
            seguridad_fiscal.registrar_log_fiscal(
                usuario='SISTEMA',
                accion='EXPORTACION_FACTURAS_SENIAT',
                documento_tipo='EXPORTACION',
                documento_numero=nombre_archivo,
                detalles=f'Exportadas {len(facturas)} facturas en formato {formato.upper()}'
            )
            
            return {
                'exito': True,
                'archivo': ruta_archivo,
                'nombre_archivo': nombre_archivo,
                'total_registros': len(facturas),
                'formato': formato,
                'tamaño_archivo': os.path.getsize(ruta_archivo),
                'fecha_exportacion': datetime.now().isoformat()
            }
            
        except Exception as e:
            seguridad_fiscal.registrar_log_fiscal(
                usuario='SISTEMA',
                accion='ERROR_EXPORTACION_SENIAT',
                documento_tipo='EXPORTACION',
                documento_numero=nombre_archivo,
                detalles=f'Error en exportación: {str(e)}'
            )
            
            return {
                'exito': False,
                'error': str(e),
                'total_registros': 0
            }
            
    def _cargar_facturas_filtradas(self, fecha_desde: str = None, fecha_hasta: str = None) -> List[Dict[str, Any]]:
        """Carga facturas filtradas por fecha"""
        try:
            facturas_file = 'facturas_json/facturas.json'
            if not os.path.exists(facturas_file):
                return []
                
            with open(facturas_file, 'r', encoding='utf-8') as f:
                facturas_dict = json.load(f)
                
            facturas_lista = []
            
            for factura in facturas_dict.values():
                # Filtrar por fechas si se especifican
                fecha_factura = factura.get('fecha', '')
                
                if fecha_desde and fecha_factura < fecha_desde:
                    continue
                if fecha_hasta and fecha_factura > fecha_hasta:
                    continue
                    
                facturas_lista.append(factura)
                
            # Ordenar por fecha y número
            facturas_lista.sort(key=lambda x: (x.get('fecha', ''), x.get('numero', '')))
            
            return facturas_lista
            
        except Exception as e:
            print(f"Error cargando facturas: {str(e)}")
            return []
            
    def _exportar_facturas_csv(self, facturas: List[Dict[str, Any]], ruta_archivo: str, incluir_metadatos: bool):
        """Exporta facturas en formato CSV"""
        with open(ruta_archivo, 'w', newline='', encoding='utf-8') as csvfile:
            # Definir campos para CSV
            campos_basicos = [
                'numero', 'fecha', 'hora', 'timestamp_creacion',
                'cliente_rif', 'cliente_nombre', 'cliente_direccion',
                'subtotal_usd', 'subtotal_bs', 'iva_total', 'descuento_total',
                'total_usd', 'total_bs', 'tasa_bcv', 'condicion_pago',
                'estado', 'moneda_principal'
            ]
            
            campos_metadatos = [
                'hash_inmutable', 'firma_digital', 'mac_address', 'hostname',
                'fecha_creacion_metadatos', 'inmutable'
            ] if incluir_metadatos else []
            
            campos_items = [
                'items_json'  # Items serializados como JSON
            ]
            
            todos_campos = campos_basicos + campos_metadatos + campos_items
            
            writer = csv.DictWriter(csvfile, fieldnames=todos_campos)
            writer.writeheader()
            
            for factura in facturas:
                fila = {}
                
                # Campos básicos
                fila['numero'] = factura.get('numero', '')
                fila['fecha'] = factura.get('fecha', '')
                fila['hora'] = factura.get('hora', '')
                fila['timestamp_creacion'] = factura.get('timestamp_creacion', '')
                
                # Datos del cliente
                cliente = factura.get('cliente_datos', {})
                fila['cliente_rif'] = cliente.get('rif', '')
                fila['cliente_nombre'] = cliente.get('nombre', '')
                fila['cliente_direccion'] = cliente.get('direccion', '')
                
                # Totales
                fila['subtotal_usd'] = factura.get('subtotal_usd', 0)
                fila['subtotal_bs'] = factura.get('subtotal_bs', 0)
                fila['iva_total'] = factura.get('iva_total', 0)
                fila['descuento_total'] = factura.get('descuento_total', 0)
                fila['total_usd'] = factura.get('total_usd', 0)
                fila['total_bs'] = factura.get('total_bs', 0)
                fila['tasa_bcv'] = factura.get('tasa_bcv', 0)
                
                # Otros datos
                fila['condicion_pago'] = factura.get('condicion_pago', '')
                fila['estado'] = factura.get('estado', '')
                fila['moneda_principal'] = factura.get('moneda_principal', 'USD')
                
                # Metadatos de seguridad
                if incluir_metadatos:
                    metadatos = factura.get('_metadatos_seguridad', {})
                    fila['hash_inmutable'] = metadatos.get('hash_inmutable', '')
                    fila['firma_digital'] = metadatos.get('firma_digital', '')
                    fila['mac_address'] = metadatos.get('mac_address', '')
                    fila['hostname'] = metadatos.get('hostname', '')
                    fila['fecha_creacion_metadatos'] = metadatos.get('fecha_creacion', '')
                    fila['inmutable'] = metadatos.get('inmutable', False)
                
                # Items como JSON
                fila['items_json'] = json.dumps(factura.get('items', []), ensure_ascii=False)
                
                writer.writerow(fila)
                
    def _exportar_facturas_xml(self, facturas: List[Dict[str, Any]], ruta_archivo: str, incluir_metadatos: bool):
        """Exporta facturas en formato XML"""
        # Crear elemento raíz
        root = ET.Element('FacturasSENIAT')
        root.set('version', '1.0')
        root.set('fecha_exportacion', datetime.now().isoformat())
        root.set('total_facturas', str(len(facturas)))
        
        for factura in facturas:
            factura_elem = ET.SubElement(root, 'Factura')
            
            # Información básica
            info_elem = ET.SubElement(factura_elem, 'Informacion')
            self._agregar_elemento_xml(info_elem, 'numero', factura.get('numero', ''))
            self._agregar_elemento_xml(info_elem, 'fecha', factura.get('fecha', ''))
            self._agregar_elemento_xml(info_elem, 'hora', factura.get('hora', ''))
            self._agregar_elemento_xml(info_elem, 'timestamp_creacion', factura.get('timestamp_creacion', ''))
            
            # Cliente
            cliente_elem = ET.SubElement(factura_elem, 'Cliente')
            cliente_datos = factura.get('cliente_datos', {})
            self._agregar_elemento_xml(cliente_elem, 'rif', cliente_datos.get('rif', ''))
            self._agregar_elemento_xml(cliente_elem, 'nombre', cliente_datos.get('nombre', ''))
            self._agregar_elemento_xml(cliente_elem, 'direccion', cliente_datos.get('direccion', ''))
            self._agregar_elemento_xml(cliente_elem, 'telefono', cliente_datos.get('telefono', ''))
            
            # Items
            items_elem = ET.SubElement(factura_elem, 'Items')
            for item in factura.get('items', []):
                item_elem = ET.SubElement(items_elem, 'Item')
                self._agregar_elemento_xml(item_elem, 'id', item.get('id', ''))
                self._agregar_elemento_xml(item_elem, 'nombre', item.get('nombre', ''))
                self._agregar_elemento_xml(item_elem, 'cantidad', str(item.get('cantidad', 0)))
                self._agregar_elemento_xml(item_elem, 'precio_unitario_usd', str(item.get('precio_unitario_usd', 0)))
                self._agregar_elemento_xml(item_elem, 'subtotal_usd', str(item.get('subtotal_usd', 0)))
                
            # Totales
            totales_elem = ET.SubElement(factura_elem, 'Totales')
            self._agregar_elemento_xml(totales_elem, 'subtotal_usd', str(factura.get('subtotal_usd', 0)))
            self._agregar_elemento_xml(totales_elem, 'subtotal_bs', str(factura.get('subtotal_bs', 0)))
            self._agregar_elemento_xml(totales_elem, 'iva_total', str(factura.get('iva_total', 0)))
            self._agregar_elemento_xml(totales_elem, 'descuento_total', str(factura.get('descuento_total', 0)))
            self._agregar_elemento_xml(totales_elem, 'total_usd', str(factura.get('total_usd', 0)))
            self._agregar_elemento_xml(totales_elem, 'total_bs', str(factura.get('total_bs', 0)))
            self._agregar_elemento_xml(totales_elem, 'tasa_bcv', str(factura.get('tasa_bcv', 0)))
            
            # Metadatos de seguridad
            if incluir_metadatos:
                metadatos_elem = ET.SubElement(factura_elem, 'MetadatosSeguridad')
                metadatos = factura.get('_metadatos_seguridad', {})
                self._agregar_elemento_xml(metadatos_elem, 'hash_inmutable', metadatos.get('hash_inmutable', ''))
                self._agregar_elemento_xml(metadatos_elem, 'firma_digital', metadatos.get('firma_digital', ''))
                self._agregar_elemento_xml(metadatos_elem, 'mac_address', metadatos.get('mac_address', ''))
                self._agregar_elemento_xml(metadatos_elem, 'inmutable', str(metadatos.get('inmutable', False)))
                
        # Escribir XML formateado
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(dom.toprettyxml(indent='  '))
            
    def _agregar_elemento_xml(self, parent, nombre, valor):
        """Agrega un elemento XML con el valor especificado"""
        elem = ET.SubElement(parent, nombre)
        elem.text = str(valor) if valor is not None else ''
        
    def _exportar_facturas_json(self, facturas: List[Dict[str, Any]], ruta_archivo: str, incluir_metadatos: bool):
        """Exporta facturas en formato JSON"""
        datos_exportacion = {
            'metadatos_exportacion': {
                'version': '1.0',
                'fecha_exportacion': datetime.now().isoformat(),
                'total_facturas': len(facturas),
                'incluye_metadatos_seguridad': incluir_metadatos
            },
            'facturas': facturas if incluir_metadatos else [
                {k: v for k, v in factura.items() if not k.startswith('_')}
                for factura in facturas
            ]
        }
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos_exportacion, f, indent=2, ensure_ascii=False, default=str)
            
    def exportar_logs_auditoria(self, 
                               fecha_desde: str = None,
                               fecha_hasta: str = None,
                               formato: str = 'csv') -> Dict[str, Any]:
        """
        Exporta logs de auditoría fiscal
        
        Args:
            fecha_desde: Fecha de inicio
            fecha_hasta: Fecha de fin
            formato: Formato de exportación
            
        Returns:
            Información sobre la exportación
        """
        try:
            logs = self._cargar_logs_auditoria(fecha_desde, fecha_hasta)
            
            if not logs:
                return {
                    'exito': False,
                    'mensaje': 'No se encontraron logs en el rango especificado',
                    'total_registros': 0
                }
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"logs_auditoria_seniat_{timestamp}.{formato}"
            ruta_archivo = os.path.join(self.directorio_exportacion, nombre_archivo)
            
            if formato == 'csv':
                self._exportar_logs_csv(logs, ruta_archivo)
            elif formato == 'json':
                self._exportar_logs_json(logs, ruta_archivo)
                
            return {
                'exito': True,
                'archivo': ruta_archivo,
                'nombre_archivo': nombre_archivo,
                'total_registros': len(logs),
                'tamaño_archivo': os.path.getsize(ruta_archivo)
            }
            
        except Exception as e:
            return {
                'exito': False,
                'error': str(e)
            }
            
    def _cargar_logs_auditoria(self, fecha_desde: str = None, fecha_hasta: str = None) -> List[Dict[str, Any]]:
        """Carga logs de auditoría fiscal filtrados por fecha"""
        logs = []
        archivo_logs = 'logs/auditoria_fiscal.log'
        
        if not os.path.exists(archivo_logs):
            return logs
            
        try:
            with open(archivo_logs, 'r', encoding='utf-8') as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea:
                        continue
                        
                    log_entry = self._parsear_linea_log(linea)
                    if log_entry:
                        # Filtrar por fechas si se especifican
                        fecha_log = log_entry.get('timestamp', '')[:10]  # YYYY-MM-DD
                        
                        if fecha_desde and fecha_log < fecha_desde:
                            continue
                        if fecha_hasta and fecha_log > fecha_hasta:
                            continue
                            
                        logs.append(log_entry)
                        
        except Exception as e:
            print(f"Error cargando logs: {str(e)}")
            
        return logs
        
    def _parsear_linea_log(self, linea: str) -> Optional[Dict[str, Any]]:
        """Parsea una línea de log fiscal"""
        try:
            # Formato: [timestamp] USUARIO:x | ACCION:x | DOC_TIPO:x | DOC_NUM:x | IP_EXT:x | IP_LOC:x | MAC:x | HOST:x | DETALLES:x | HASH:x
            if not linea.startswith('['):
                return None
                
            # Extraer timestamp
            timestamp_end = linea.find(']')
            if timestamp_end == -1:
                return None
                
            timestamp = linea[1:timestamp_end]
            resto = linea[timestamp_end + 2:]  # +2 para saltar "] "
            
            # Parsear campos
            campos = {}
            partes = resto.split(' | ')
            
            for parte in partes:
                if ':' in parte:
                    clave, valor = parte.split(':', 1)
                    campos[clave.lower()] = valor.strip()
                    
            return {
                'timestamp': timestamp,
                'usuario': campos.get('usuario', ''),
                'accion': campos.get('accion', ''),
                'documento_tipo': campos.get('doc_tipo', ''),
                'documento_numero': campos.get('doc_num', ''),
                'ip_externa': campos.get('ip_ext', ''),
                'ip_local': campos.get('ip_loc', ''),
                'mac_address': campos.get('mac', ''),
                'hostname': campos.get('host', ''),
                'detalles': campos.get('detalles', ''),
                'hash_inmutable': campos.get('hash', '')
            }
            
        except Exception:
            return None
            
    def _exportar_logs_csv(self, logs: List[Dict[str, Any]], ruta_archivo: str):
        """Exporta logs en formato CSV"""
        with open(ruta_archivo, 'w', newline='', encoding='utf-8') as csvfile:
            campos = [
                'timestamp', 'usuario', 'accion', 'documento_tipo', 'documento_numero',
                'ip_externa', 'ip_local', 'mac_address', 'hostname', 'detalles', 'hash_inmutable'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=campos)
            writer.writeheader()
            
            for log in logs:
                writer.writerow(log)
                
    def _exportar_logs_json(self, logs: List[Dict[str, Any]], ruta_archivo: str):
        """Exporta logs en formato JSON"""
        datos = {
            'metadatos': {
                'fecha_exportacion': datetime.now().isoformat(),
                'total_logs': len(logs)
            },
            'logs': logs
        }
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
            
    def generar_reporte_consolidado(self, fecha_desde: str = None, fecha_hasta: str = None) -> Dict[str, Any]:
        """
        Genera un reporte consolidado para auditoría SENIAT
        
        Args:
            fecha_desde: Fecha de inicio
            fecha_hasta: Fecha de fin
            
        Returns:
            Información del reporte generado
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_zip = f"reporte_consolidado_seniat_{timestamp}.zip"
            ruta_zip = os.path.join(self.directorio_exportacion, nombre_zip)
            
            with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Exportar facturas en múltiples formatos
                for formato in ['csv', 'xml', 'json']:
                    resultado = self.exportar_facturas(fecha_desde, fecha_hasta, formato, True)
                    if resultado['exito']:
                        zipf.write(resultado['archivo'], os.path.basename(resultado['archivo']))
                        
                # Exportar logs de auditoría
                resultado_logs = self.exportar_logs_auditoria(fecha_desde, fecha_hasta, 'csv')
                if resultado_logs['exito']:
                    zipf.write(resultado_logs['archivo'], os.path.basename(resultado_logs['archivo']))
                    
                # Crear archivo de metadatos del reporte
                metadatos_reporte = {
                    'fecha_generacion': datetime.now().isoformat(),
                    'periodo': {
                        'fecha_desde': fecha_desde,
                        'fecha_hasta': fecha_hasta
                    },
                    'archivos_incluidos': [
                        'facturas_seniat_*.csv',
                        'facturas_seniat_*.xml', 
                        'facturas_seniat_*.json',
                        'logs_auditoria_seniat_*.csv'
                    ],
                    'proposito': 'Reporte consolidado para auditoría SENIAT',
                    'version_sistema': '1.0.0'
                }
                
                metadatos_json = json.dumps(metadatos_reporte, indent=2, ensure_ascii=False)
                zipf.writestr('metadatos_reporte.json', metadatos_json)
                
            # Limpiar archivos temporales
            self._limpiar_archivos_temporales()
            
            return {
                'exito': True,
                'archivo': ruta_zip,
                'nombre_archivo': nombre_zip,
                'tamaño_archivo': os.path.getsize(ruta_zip),
                'fecha_generacion': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'exito': False,
                'error': str(e)
            }
            
    def _limpiar_archivos_temporales(self):
        """Limpia archivos temporales de exportación individual"""
        try:
            for archivo in os.listdir(self.directorio_exportacion):
                if archivo.endswith(('.csv', '.xml', '.json')) and not archivo.startswith('reporte_consolidado'):
                    os.remove(os.path.join(self.directorio_exportacion, archivo))
        except Exception:
            pass

# Instancia global del exportador SENIAT
exportador_seniat = ExportacionSENIAT() 