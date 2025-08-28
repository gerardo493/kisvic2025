#!/usr/bin/env python3
"""
Script para identificar y corregir facturas que tienen pagos pero no tienen ID válido.
Este script resuelve el problema de los pagos que muestran #None en la tabla de pagos recibidos.
"""

import json
import os
from datetime import datetime

# Archivos de datos
ARCHIVO_FACTURAS = 'facturas_json/facturas.json'
ARCHIVO_BACKUP = f'backups/facturas_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

def cargar_datos(archivo):
    """Carga datos desde un archivo JSON"""
    try:
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"❌ Error cargando {archivo}: {e}")
        return {}

def guardar_datos(archivo, datos):
    """Guarda datos en un archivo JSON"""
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error guardando {archivo}: {e}")
        return False

def crear_backup(archivo_origen):
    """Crea un backup del archivo original"""
    try:
        if os.path.exists(archivo_origen):
            os.makedirs(os.path.dirname(ARCHIVO_BACKUP), exist_ok=True)
            with open(archivo_origen, 'r', encoding='utf-8') as f_origen:
                with open(ARCHIVO_BACKUP, 'w', encoding='utf-8') as f_backup:
                    f_backup.write(f_origen.read())
            print(f"✅ Backup creado: {ARCHIVO_BACKUP}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error creando backup: {e}")
        return False

def analizar_facturas():
    """Analiza las facturas y identifica problemas"""
    print("🔍 Analizando facturas...")
    
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    if not facturas:
        print("❌ No se pudieron cargar las facturas")
        return
    
    print(f"📊 Total de facturas cargadas: {len(facturas)}")
    
    # Contadores
    facturas_sin_id = 0
    facturas_con_pagos_sin_id = 0
    pagos_afectados = 0
    
    # Identificar problemas
    facturas_problematicas = []
    
    for key, factura in facturas.items():
        # Verificar si la factura tiene ID
        factura_id = factura.get('id')
        
        if not factura_id:
            facturas_sin_id += 1
            print(f"⚠️ Factura sin ID encontrada (clave: {key})")
            
            # Verificar si tiene pagos
            if 'pagos' in factura and factura['pagos']:
                facturas_con_pagos_sin_id += 1
                pagos_afectados += len(factura['pagos'])
                facturas_problematicas.append(key)
                print(f"   └─ Tiene {len(factura['pagos'])} pagos que causarán #None en la tabla")
    
    print(f"\n📋 RESUMEN DEL ANÁLISIS:")
    print(f"   • Facturas sin ID: {facturas_sin_id}")
    print(f"   • Facturas con pagos pero sin ID: {facturas_con_pagos_sin_id}")
    print(f"   • Pagos afectados: {pagos_afectados}")
    
    return facturas_problematicas

def corregir_facturas(facturas_problematicas):
    """Corrige las facturas problemáticas"""
    if not facturas_problematicas:
        print("✅ No hay facturas que corregir")
        return
    
    print(f"\n🔧 Corrigiendo {len(facturas_problematicas)} facturas...")
    
    # Crear backup antes de modificar
    if not crear_backup(ARCHIVO_FACTURAS):
        print("❌ No se pudo crear el backup. Abortando corrección.")
        return
    
    # Cargar facturas
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    
    # Corregir cada factura problemática
    for key in facturas_problematicas:
        factura = facturas[key]
        
        # Opción 1: Asignar la clave como ID si es válida
        if key.isdigit() or (isinstance(key, str) and key.strip()):
            nuevo_id = key
            print(f"   🔄 Asignando ID '{nuevo_id}' a factura (clave: {key})")
            factura['id'] = nuevo_id
            
        # Opción 2: Generar un nuevo ID si la clave no es válida
        else:
            import uuid
            nuevo_id = str(uuid.uuid4())[:8]
            print(f"   🔄 Generando nuevo ID '{nuevo_id}' para factura (clave: {key})")
            factura['id'] = nuevo_id
    
    # Guardar correcciones
    if guardar_datos(ARCHIVO_FACTURAS, facturas):
        print("✅ Facturas corregidas y guardadas exitosamente")
    else:
        print("❌ Error guardando las correcciones")

def main():
    """Función principal"""
    print("🚀 INICIANDO CORRECCIÓN DE FACTURAS SIN ID")
    print("=" * 50)
    
    # Analizar facturas
    facturas_problematicas = analizar_facturas()
    
    if facturas_problematicas:
        print(f"\n❓ ¿Deseas corregir las {len(facturas_problematicas)} facturas problemáticas?")
        respuesta = input("   Escribe 'SI' para continuar: ").strip().upper()
        
        if respuesta == 'SI':
            corregir_facturas(facturas_problematicas)
        else:
            print("❌ Corrección cancelada por el usuario")
    else:
        print("✅ No se encontraron problemas que corregir")
    
    print("\n🏁 Proceso completado")

if __name__ == "__main__":
    main()
