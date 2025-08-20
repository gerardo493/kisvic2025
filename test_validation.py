#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para validar las funciones de validación de IDs de facturas
"""

import json
import os

def test_id_validation():
    """Prueba las validaciones de IDs de facturas"""
    
    # Simular diferentes tipos de IDs
    test_ids = [
        None,           # ID None
        "",            # ID vacío
        "   ",         # ID solo espacios
        "3",           # ID válido numérico
        "abc123",      # ID válido alfanumérico
        0,             # ID cero
        False,         # ID booleano
        [],            # ID lista vacía
        {},            # ID diccionario vacío
    ]
    
    print("=== PRUEBA DE VALIDACIÓN DE IDs ===")
    print()
    
    for test_id in test_ids:
        # Aplicar la misma lógica de validación que en app.py
        is_valid = test_id is not None and str(test_id).strip() != ''
        
        print(f"ID: {repr(test_id)}")
        print(f"  Tipo: {type(test_id)}")
        print(f"  Válido: {is_valid}")
        print(f"  String: {repr(str(test_id) if test_id is not None else 'None')}")
        print(f"  Strip: {repr(str(test_id).strip() if test_id is not None else 'None')}")
        print()
    
    # Probar con el archivo de facturas real
    print("=== VERIFICACIÓN DEL ARCHIVO DE FACTURAS ===")
    print()
    
    facturas_file = 'facturas_json/facturas.json'
    if os.path.exists(facturas_file):
        try:
            with open(facturas_file, 'r', encoding='utf-8') as f:
                facturas = json.load(f)
            
            print(f"Total de facturas: {len(facturas)}")
            print()
            
            # Verificar IDs inválidos
            ids_invalidos = []
            for id_factura in facturas.keys():
                if not id_factura or str(id_factura).strip() == '':
                    ids_invalidos.append(id_factura)
            
            if ids_invalidos:
                print(f"⚠️  SE ENCONTRARON {len(ids_invalidos)} FACTURAS CON IDs INVÁLIDOS:")
                for id_invalido in ids_invalidos:
                    print(f"   - ID: {repr(id_invalido)}")
                    print(f"     Tipo: {type(id_invalido)}")
                    if id_invalido in facturas:
                        print(f"     Número: {facturas[id_invalido].get('numero', 'N/A')}")
                    print()
            else:
                print("✅ No se encontraron facturas con IDs inválidos")
            
            # Mostrar algunos ejemplos de IDs válidos
            print("Ejemplos de IDs válidos:")
            count = 0
            for id_factura in list(facturas.keys())[:5]:
                if count < 5:
                    print(f"   - ID: {repr(id_factura)} (Tipo: {type(id_factura)})")
                    count += 1
            
        except Exception as e:
            print(f"❌ Error al leer el archivo de facturas: {e}")
    else:
        print(f"❌ Archivo de facturas no encontrado: {facturas_file}")

if __name__ == "__main__":
    test_id_validation()
