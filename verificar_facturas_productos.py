#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador de Productos en Facturas
====================================

Script de diagnóstico rápido para verificar el estado
de los productos en las facturas existentes.
"""

import json

def cargar_datos(archivo):
    """Carga datos desde archivo JSON"""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def verificar_facturas():
    """Verifica el estado de productos en todas las facturas"""
    print("=" * 50)
    print("    VERIFICADOR DE PRODUCTOS")
    print("=" * 50)
    print()
    
    facturas = cargar_datos('facturas.json')
    
    if not facturas:
        print("❌ No se encontraron facturas.")
        return
    
    print(f"📋 Facturas encontradas: {len(facturas)}")
    print()
    
    # Contadores
    con_items_seniat = 0
    con_productos_legacy = 0
    sin_productos = 0
    con_problemas = 0
    
    print("🔍 Analizando facturas...")
    print()
    
    for factura_id, factura in facturas.items():
        estado_items = "❌"
        estado_legacy = "❌" 
        
        # Verificar estructura SENIAT
        if 'items' in factura and isinstance(factura['items'], list) and len(factura['items']) > 0:
            estado_items = "✅"
            con_items_seniat += 1
            
        # Verificar estructura legacy
        if ('productos' in factura and isinstance(factura['productos'], list) and 
            'cantidades' in factura and isinstance(factura['cantidades'], list) and
            len(factura['productos']) > 0):
            estado_legacy = "✅"
            con_productos_legacy += 1
            
        # Determinar estado general
        if estado_items == "✅" or estado_legacy == "✅":
            estado_general = "✅ OK"
        else:
            estado_general = "❌ SIN PRODUCTOS"
            sin_productos += 1
            
        # Verificar si tiene problemas de tipo de datos
        problemas_tipo = ""
        if 'items' in factura and not isinstance(factura['items'], list):
            problemas_tipo = f" (items: {type(factura['items']).__name__})"
            con_problemas += 1
            
        print(f"   {factura_id[:20]:<20} | SENIAT: {estado_items} | Legacy: {estado_legacy} | {estado_general}{problemas_tipo}")
    
    print()
    print("=" * 50)
    print("    RESUMEN")
    print("=" * 50)
    print(f"✅ Con estructura SENIAT:     {con_items_seniat}")
    print(f"✅ Con estructura Legacy:     {con_productos_legacy}")
    print(f"❌ Sin productos visibles:    {sin_productos}")
    print(f"⚠️  Con problemas de tipo:    {con_problemas}")
    print()
    
    if sin_productos > 0:
        print("🔧 RECOMENDACIÓN:")
        print("   Ejecuta: migrar_facturas_productos.bat")
        print("   Para corregir las facturas sin productos.")
    else:
        print("🎉 ¡Todas las facturas tienen productos visibles!")
    
    print()

if __name__ == "__main__":
    verificar_facturas() 