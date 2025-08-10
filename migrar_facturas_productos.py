#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migración - Productos en Facturas
===========================================

Este script corrige facturas existentes que no muestran productos
debido a problemas de estructura de datos (funciones en lugar de listas).

EJECUTAR después de corregir el backend.
"""

import json
import os
from datetime import datetime

def cargar_datos(archivo):
    """Carga datos desde archivo JSON"""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_datos(archivo, datos):
    """Guarda datos en archivo JSON"""
    try:
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando {archivo}: {str(e)}")
        return False

def migrar_facturas_productos():
    """Migra facturas existentes para que tengan productos visibles"""
    print("=" * 60)
    print("    MIGRACIÓN DE PRODUCTOS EN FACTURAS")
    print("=" * 60)
    print()
    
    # Cargar facturas existentes
    facturas = cargar_datos('facturas.json')
    
    if not facturas:
        print("❌ No se encontraron facturas existentes.")
        print("   Archivo: facturas.json no existe o está vacío.")
        return
    
    print(f"📋 Facturas encontradas: {len(facturas)}")
    print()
    
    # Crear backup
    backup_file = f"facturas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if guardar_datos(backup_file, facturas):
        print(f"💾 Backup creado: {backup_file}")
    else:
        print("❌ Error creando backup. Abortando migración.")
        return
    
    facturas_corregidas = 0
    facturas_sin_problemas = 0
    facturas_con_errores = []
    
    print("\n🔄 Iniciando migración...")
    print()
    
    for factura_id, factura in facturas.items():
        print(f"   Procesando: {factura_id}")
        
        try:
            tiene_problemas = False
            
            # Verificar si la factura tiene problemas de productos
            items_ok = (
                'items' in factura and 
                isinstance(factura['items'], list) and 
                len(factura['items']) > 0
            )
            
            legacy_ok = (
                'productos' in factura and 
                isinstance(factura['productos'], list) and
                'cantidades' in factura and 
                isinstance(factura['cantidades'], list) and
                len(factura['productos']) > 0
            )
            
            if items_ok or legacy_ok:
                print(f"   ✅ Sin problemas: {factura_id}")
                facturas_sin_problemas += 1
                continue
            
            # Si llegamos aquí, la factura tiene problemas
            tiene_problemas = True
            
            # Intentar reconstruir la estructura de productos
            productos_reconstruidos = []
            cantidades_reconstruidas = []
            precios_reconstruidos = []
            items_reconstruidos = []
            
            # Buscar pistas de productos en otros campos
            total_usd = factura.get('total_usd', 0)
            subtotal_usd = factura.get('subtotal_usd', 0)
            
            if total_usd > 0 or subtotal_usd > 0:
                # Crear entrada genérica si hay totales pero no productos
                productos_reconstruidos = ['PRODUCTO_RECUPERADO']
                cantidades_reconstruidas = [1]
                precios_reconstruidos = [subtotal_usd if subtotal_usd > 0 else total_usd]
                
                items_reconstruidos = [{
                    'id': 'PRODUCTO_RECUPERADO',
                    'nombre': 'Producto recuperado de factura migrada',
                    'cantidad': 1,
                    'precio_unitario_usd': subtotal_usd if subtotal_usd > 0 else total_usd,
                    'precio_unitario_bs': (subtotal_usd if subtotal_usd > 0 else total_usd) * factura.get('tasa_bcv', 36.0),
                    'categoria': 'RECUPERADO',
                    'codigo_barras': '',
                    'subtotal_usd': subtotal_usd if subtotal_usd > 0 else total_usd,
                    'subtotal_bs': (subtotal_usd if subtotal_usd > 0 else total_usd) * factura.get('tasa_bcv', 36.0)
                }]
                
                print(f"   🔄 Productos reconstruidos: {factura_id}")
            else:
                print(f"   ⚠️  Sin datos para reconstruir: {factura_id}")
                facturas_con_errores.append({
                    'id': factura_id,
                    'problema': 'Sin productos ni totales para reconstruir',
                    'solucion': 'Revisar manualmente'
                })
                continue
            
            # Actualizar la factura con las estructuras corregidas
            factura['items'] = items_reconstruidos
            factura['productos'] = productos_reconstruidos
            factura['cantidades'] = cantidades_reconstruidas
            factura['precios'] = precios_reconstruidos
            
            # Marcar como migrada
            if '_metadatos_seguridad' not in factura:
                factura['_metadatos_seguridad'] = {}
            factura['_metadatos_seguridad']['migrada_productos'] = datetime.now().isoformat()
            
            facturas_corregidas += 1
            print(f"   ✅ Corregida: {factura_id}")
            
        except Exception as e:
            print(f"   ❌ Error procesando {factura_id}: {str(e)}")
            facturas_con_errores.append({
                'id': factura_id,
                'problema': f'Error de migración: {str(e)}',
                'solucion': 'Revisar manualmente'
            })
    
    # Guardar facturas corregidas
    if guardar_datos('facturas.json', facturas):
        print(f"\n✅ Migración completada")
        print(f"   📊 Total facturas: {len(facturas)}")
        print(f"   ✅ Sin problemas: {facturas_sin_problemas}")
        print(f"   🔄 Corregidas: {facturas_corregidas}")
        print(f"   ⚠️  Con errores: {len(facturas_con_errores)}")
    else:
        print("\n❌ Error guardando facturas migradas")
        return
    
    # Mostrar facturas con errores
    if facturas_con_errores:
        print("\n" + "=" * 60)
        print("    FACTURAS QUE REQUIEREN REVISIÓN MANUAL")
        print("=" * 60)
        
        for error in facturas_con_errores:
            print(f"\n🔧 Factura: {error['id']}")
            print(f"   ⚠️  {error['problema']}")
            print(f"   💡 Solución: {error['solucion']}")
    
    print("\n" + "=" * 60)
    print("    MIGRACIÓN COMPLETADA")
    print("=" * 60)
    print()
    print("🎯 Las facturas ahora deberían mostrar productos correctamente")
    print("🚀 Prueba abrir cualquier factura para verificar")
    print()

if __name__ == "__main__":
    migrar_facturas_productos() 