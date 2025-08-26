#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la discrepancia entre el stock original y el actual
de los productos en la nota de entrega NE-0002.
"""

import json
import os
from datetime import datetime

# Archivos de datos
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'
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

def analizar_discrepancia_stock():
    """Analiza la discrepancia entre el stock original y el actual."""
    print("🔍 ANALIZANDO DISCREPANCIA DE STOCK")
    print("="*60)
    
    # Cargar datos
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if 'NE-0002' not in notas:
        print("❌ Nota NE-0002 no encontrada")
        return
    
    nota = notas['NE-0002']
    print(f"📝 NOTA DE ENTREGA: {nota['numero']}")
    print(f"   Fecha creación: {nota.get('fecha', 'N/A')}")
    print(f"   Estado: {nota.get('estado', 'N/A')}")
    print(f"   Total: ${nota.get('subtotal_usd', 0):.2f}")
    
    # Analizar cada producto
    productos = nota.get('productos', [])
    cantidades = nota.get('cantidades', [])
    
    print(f"\n📦 ANÁLISIS DE PRODUCTOS:")
    print("-" * 60)
    
    for i, producto_id in enumerate(productos):
        cantidad_nota = int(cantidades[i]) if i < len(cantidades) else 0
        
        if producto_id in inventario:
            producto = inventario[producto_id]
            stock_actual = int(producto.get('cantidad', 0))
            ultima_salida = producto.get('ultima_salida', 'N/A')
            
            print(f"\n🔍 PRODUCTO {producto_id}: {producto.get('nombre', 'N/A')}")
            print(f"   Cantidad en nota: {cantidad_nota}")
            print(f"   Stock actual: {stock_actual}")
            print(f"   Última salida: {ultima_salida}")
            
            # Calcular stock teórico (si no se hubiera descontado)
            stock_teorico = stock_actual + cantidad_nota
            print(f"   Stock teórico (sin descuento): {stock_teorico}")
            
            # Verificar si el descuento fue correcto
            if ultima_salida == '2025-08-25 22:48:42':
                print(f"   ✅ Última salida coincide con la nota de entrega")
                print(f"   📊 Descuento aplicado: {cantidad_nota} unidades")
            else:
                print(f"   ⚠️ Última salida NO coincide con la nota de entrega")
                print(f"   📊 Última salida: {ultima_salida}")
                
        else:
            print(f"\n❌ PRODUCTO {producto_id}: No encontrado en inventario")
    
    # Verificar si hay otros movimientos recientes
    print(f"\n🔍 VERIFICANDO MOVIMIENTOS RECIENTES:")
    print("-" * 60)
    
    for producto_id in productos:
        if producto_id in inventario:
            producto = inventario[producto_id]
            historial = producto.get('historial_ajustes', [])
            
            # Buscar movimientos del 25 de agosto
            movimientos_25_ago = []
            for movimiento in historial:
                if '2025-08-25' in movimiento.get('fecha', ''):
                    movimientos_25_ago.append(movimiento)
            
            if movimientos_25_ago:
                print(f"\n📅 MOVIMIENTOS DEL 25/08/2025 - Producto {producto_id}:")
                for mov in movimientos_25_ago:
                    print(f"   {mov.get('fecha', 'N/A')} - {mov.get('tipo', 'N/A')}: {mov.get('cantidad', 0)} - {mov.get('motivo', 'N/A')}")
            else:
                print(f"\n📅 No hay movimientos del 25/08/2025 para producto {producto_id}")

def verificar_estado_sistema():
    """Verifica el estado general del sistema."""
    print(f"\n" + "="*60)
    print("📊 ESTADO GENERAL DEL SISTEMA")
    print("="*60)
    
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    print(f"📝 Total notas de entrega: {len(notas)}")
    print(f"📦 Total productos en inventario: {len(inventario)}")
    
    # Contar notas por estado
    estados = {}
    for nota in notas.values():
        estado = nota.get('estado', 'SIN_ESTADO')
        estados[estado] = estados.get(estado, 0) + 1
    
    print(f"\n📊 ESTADOS DE NOTAS DE ENTREGA:")
    for estado, cantidad in estados.items():
        print(f"   {estado}: {cantidad}")
    
    # Verificar productos con stock bajo
    productos_stock_bajo = []
    for producto_id, producto in inventario.items():
        if int(producto.get('cantidad', 0)) < 10:
            productos_stock_bajo.append((producto_id, producto.get('nombre', 'N/A'), producto.get('cantidad', 0)))
    
    if productos_stock_bajo:
        print(f"\n⚠️ PRODUCTOS CON STOCK BAJO (< 10):")
        for producto_id, nombre, stock in productos_stock_bajo[:10]:  # Solo mostrar los primeros 10
            print(f"   {producto_id}: {nombre} - Stock: {stock}")

def main():
    """Función principal."""
    print("🚀 VERIFICACIÓN DE DISCREPANCIA DE STOCK")
    print("="*80)
    
    # Analizar discrepancia específica
    analizar_discrepancia_stock()
    
    # Verificar estado general
    verificar_estado_sistema()
    
    print(f"\n" + "="*80)
    print("✅ VERIFICACIÓN COMPLETADA")
    print("="*80)
    
    print(f"\n💡 RECOMENDACIONES:")
    print(f"   1. Verificar que no haya otros movimientos de inventario")
    print(f"   2. Confirmar que el descuento se aplicó correctamente")
    print(f"   3. Revisar si hay facturas o notas que afecten el stock")
    print(f"   4. Validar que la nota de entrega esté en el estado correcto")

if __name__ == '__main__':
    main()
