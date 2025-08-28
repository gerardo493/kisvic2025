#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para encontrar facturas con IDs problemáticos
"""

import json
import os

def find_problematic_facturas():
    """Encuentra facturas con IDs problemáticos"""
    
    facturas_file = 'facturas_json/facturas.json'
    if not os.path.exists(facturas_file):
        print(f"❌ Archivo de facturas no encontrado: {facturas_file}")
        return
    
    try:
        with open(facturas_file, 'r', encoding='utf-8') as f:
            facturas = json.load(f)
        
        print(f"📊 Total de facturas: {len(facturas)}")
        print()
        
        # Buscar IDs problemáticos
        problematic_ids = []
        valid_ids = []
        
        for id_factura in facturas.keys():
            # Verificar si el ID es problemático
            if not id_factura or str(id_factura).strip() == '':
                problematic_ids.append(id_factura)
            else:
                valid_ids.append(id_factura)
        
        print("🔍 ANÁLISIS DE IDs:")
        print(f"✅ IDs válidos: {len(valid_ids)}")
        print(f"❌ IDs problemáticos: {len(problematic_ids)}")
        print()
        
        if problematic_ids:
            print("🚨 FACTURAS CON IDs PROBLEMÁTICOS:")
            for id_problematico in problematic_ids:
                print(f"   - ID: {repr(id_problematico)}")
                print(f"     Tipo: {type(id_problematico)}")
                if id_problematico in facturas:
                    factura = facturas[id_problematico]
                    print(f"     Número: {factura.get('numero', 'N/A')}")
                    print(f"     Cliente: {factura.get('cliente_id', 'N/A')}")
                    print(f"     Fecha: {factura.get('fecha', 'N/A')}")
                print()
        else:
            print("✅ No se encontraron facturas con IDs problemáticos")
        
        # Mostrar algunos ejemplos de IDs válidos
        print("📋 EJEMPLOS DE IDs VÁLIDOS:")
        for i, id_valido in enumerate(valid_ids[:10]):
            factura = facturas[id_valido]
            print(f"   {i+1}. ID: {repr(id_valido)}")
            print(f"      Número: {factura.get('numero', 'N/A')}")
            print(f"      Cliente: {factura.get('cliente_id', 'N/A')}")
            print()
        
        # Verificar si hay IDs que podrían causar problemas en URLs
        print("🔗 VERIFICACIÓN DE URLs:")
        for id_factura in problematic_ids:
            if id_factura in facturas:
                url_editar = f"/facturas/{id_factura}/editar"
                url_ver = f"/facturas/{id_factura}"
                print(f"   ID problemático: {repr(id_factura)}")
                print(f"   URL editar: {url_editar}")
                print(f"   URL ver: {url_ver}")
                print()
        
        return problematic_ids
        
    except Exception as e:
        print(f"❌ Error al leer el archivo de facturas: {e}")
        return []

if __name__ == "__main__":
    problematic = find_problematic_facturas()
    
    if problematic:
        print("\n💡 RECOMENDACIONES:")
        print("1. Usa el botón 'Limpiar IDs' en la interfaz web")
        print("2. O ejecuta la función de limpieza manualmente")
        print("3. Verifica que no haya facturas con IDs vacíos")
    else:
        print("\n🎉 No se encontraron problemas con los IDs de facturas")
