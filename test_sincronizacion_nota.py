#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la sincronización de notas de entrega con cuentas por cobrar.
"""

import json
import os
from datetime import datetime

# Archivos de datos
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'
ARCHIVO_CUENTAS = 'cuentas_por_cobrar.json'
ARCHIVO_INVENTARIO = 'inventario.json'

def cargar_datos(nombre_archivo):
    """Carga datos desde un archivo JSON."""
    try:
        if not os.path.exists(nombre_archivo):
            return {}
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error leyendo {nombre_archivo}: {e}")
        return {}

def verificar_sincronizacion():
    """Verifica si la nota de entrega está sincronizada con cuentas por cobrar."""
    print("🔍 VERIFICANDO SINCRONIZACIÓN DE NOTA DE ENTREGA")
    print("="*60)
    
    # Cargar datos
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    
    if 'NE-0002' not in notas:
        print("❌ Nota NE-0002 no encontrada")
        return
    
    nota = notas['NE-0002']
    print(f"📝 NOTA DE ENTREGA: {nota['numero']}")
    print(f"   Estado: {nota.get('estado', 'N/A')}")
    print(f"   Modalidad: {nota.get('modalidad_pago', 'N/A')}")
    print(f"   Total: ${nota.get('subtotal_usd', 0):.2f}")
    print(f"   Pagos: {len(nota.get('pagos', []))}")
    
    # Verificar si está en cuentas por cobrar
    nota_en_cuentas = None
    for cuenta_id, cuenta in cuentas.items():
        if cuenta.get('nota_entrega_origen') == 'NE-0002':
            nota_en_cuentas = cuenta
            break
    
    if nota_en_cuentas:
        print(f"\n✅ SINCRONIZACIÓN ENCONTRADA:")
        print(f"   ID Cuenta: {cuenta_id}")
        print(f"   RIF: {nota_en_cuentas.get('rif', 'N/A')}")
        print(f"   Total: ${nota_en_cuentas.get('total_usd', 0):.2f}")
        print(f"   Abonado: ${nota_en_cuentas.get('abonado_usd', 0):.2f}")
        print(f"   Estado: {nota_en_cuentas.get('estado', 'N/A')}")
        print(f"   Tipo: {nota_en_cuentas.get('tipo_pago', 'N/A')}")
        print(f"   Fecha último abono: {nota_en_cuentas.get('fecha_ultimo_abono', 'N/A')}")
        print(f"   Referencia: {nota_en_cuentas.get('referencia_pago', 'N/A')}")
    else:
        print(f"\n❌ NO HAY SINCRONIZACIÓN:")
        print(f"   La nota NE-0002 no aparece en cuentas por cobrar")
        
        # Mostrar cuentas existentes para referencia
        print(f"\n📊 CUENTAS EXISTENTES:")
        for cuenta_id, cuenta in list(cuentas.items())[:5]:
            print(f"   {cuenta_id}: {cuenta.get('rif', 'N/A')} - ${cuenta.get('total_usd', 0):.2f} - {cuenta.get('estado', 'N/A')}")

def forzar_sincronizacion():
    """Fuerza la sincronización de la nota con cuentas por cobrar."""
    print(f"\n" + "="*60)
    print("🔄 FORZANDO SINCRONIZACIÓN")
    print("="*60)
    
    # Cargar datos
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    
    if 'NE-0002' not in notas:
        print("❌ Nota NE-0002 no encontrada")
        return
    
    nota = notas['NE-0002']
    
    # Crear entrada en cuentas por cobrar
    entrada_cuenta = {
        'rif': nota.get('cliente_id', ''),
        'total_usd': float(nota.get('subtotal_usd', 0)),
        'abonado_usd': float(nota.get('subtotal_usd', 0)),
        'estado': 'Cobrada',
        'tipo_pago': 'Nota de Entrega',
        'fecha_ultimo_abono': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'fecha_emision': nota.get('fecha', ''),
        'referencia_pago': f"Nota {nota['numero']} - Pago completo",
        'nota_entrega_origen': nota['numero']
    }
    
    # Agregar a cuentas por cobrar
    cuentas[f"NE-{nota['numero']}"] = entrada_cuenta
    
    # Guardar
    try:
        with open(ARCHIVO_CUENTAS, 'w', encoding='utf-8') as f:
            json.dump(cuentas, f, ensure_ascii=False, indent=4)
        print(f"✅ Sincronización forzada exitosamente")
        print(f"   Entrada creada: NE-{nota['numero']}")
        print(f"   Estado: Cobrada")
        print(f"   Total: ${nota.get('subtotal_usd', 0):.2f}")
    except Exception as e:
        print(f"❌ Error guardando sincronización: {e}")

def verificar_estado_final():
    """Verifica el estado final después de la sincronización."""
    print(f"\n" + "="*60)
    print("🔍 VERIFICACIÓN FINAL")
    print("="*60)
    
    # Cargar datos actualizados
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    
    # Buscar la entrada de la nota
    nota_en_cuentas = None
    for cuenta_id, cuenta in cuentas.items():
        if cuenta.get('nota_entrega_origen') == 'NE-0002':
            nota_en_cuentas = cuenta
            print(f"✅ SINCRONIZACIÓN VERIFICADA:")
            print(f"   ID Cuenta: {cuenta_id}")
            print(f"   RIF: {nota_en_cuentas.get('rif', 'N/A')}")
            print(f"   Total: ${nota_en_cuentas.get('total_usd', 0):.2f}")
            print(f"   Estado: {nota_en_cuentas.get('estado', 'N/A')}")
            print(f"   Tipo: {nota_en_cuentas.get('tipo_pago', 'N/A')}")
            print(f"   Referencia: {nota_en_cuentas.get('referencia_pago', 'N/A')}")
            break
    
    if not nota_en_cuentas:
        print(f"❌ La sincronización no se completó correctamente")

def main():
    """Función principal."""
    print("🚀 PRUEBA DE SINCRONIZACIÓN DE NOTA DE ENTREGA")
    print("="*80)
    
    # Verificar estado actual
    verificar_sincronizacion()
    
    # Forzar sincronización si es necesario
    forzar_sincronizacion()
    
    # Verificar estado final
    verificar_estado_final()
    
    print(f"\n" + "="*80)
    print("✅ PRUEBA COMPLETADA")
    print("="*80)

if __name__ == '__main__':
    main()
