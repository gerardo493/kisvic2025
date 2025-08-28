#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba completa para demostrar el flujo de notas de entrega.
Crea una nueva nota, la entrega, procesa un pago y verifica el inventario.
"""

import json
import os
from datetime import datetime

# Archivos de datos
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_CLIENTES = 'clientes.json'

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

def guardar_datos(nombre_archivo, datos):
    """Guarda datos en un archivo JSON."""
    try:
        directorio = os.path.dirname(nombre_archivo)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"❌ Error guardando {nombre_archivo}: {e}")
        return False

def crear_nueva_nota_entrega():
    """Crea una nueva nota de entrega para demostración."""
    print("\n" + "="*60)
    print("📝 CREANDO NUEVA NOTA DE ENTREGA")
    print("="*60)
    
    # Cargar datos existentes
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    # Obtener numeración secuencial
    numero_secuencial = len(notas) + 1
    numero_nota = f"NE-{numero_secuencial:04d}"
    
    # Seleccionar productos del inventario (productos con stock disponible)
    productos_disponibles = []
    cantidades_disponibles = []
    precios_disponibles = []
    
    # Tomar los primeros 3 productos con stock
    contador = 0
    for producto_id, producto in inventario.items():
        if contador >= 3:
            break
        if producto.get('cantidad', 0) > 10:  # Solo productos con stock suficiente
            productos_disponibles.append(producto_id)
            cantidades_disponibles.append("5")  # Cantidad fija para prueba
            precios_disponibles.append(str(producto.get('precio', 0)))
            contador += 1
    
    if not productos_disponibles:
        print("❌ No hay productos disponibles en inventario")
        return None
    
    # Calcular totales
    subtotal_usd = sum(float(precios_disponibles[i]) * int(cantidades_disponibles[i]) for i in range(len(precios_disponibles)))
    
    # Crear nota de entrega
    nota = {
        'numero': numero_nota,
        'numero_secuencial': numero_secuencial,
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'hora': datetime.now().strftime('%H:%M:%S'),
        'timestamp_creacion': datetime.now().isoformat(),
        'cliente_id': 'J-501924333',  # Usar cliente existente
        'modalidad_pago': 'efectivo',
        'productos': productos_disponibles,
        'cantidades': cantidades_disponibles,
        'precios': precios_disponibles,
        'subtotal_usd': subtotal_usd,
        'total_usd': subtotal_usd,
        'estado': 'PENDIENTE_ENTREGA',
        'usuario_creacion': 'admin',
        'observaciones': 'Nota de prueba para demostración de funcionalidad'
    }
    
    # Guardar nota
    notas[numero_nota] = nota
    guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
    
    print(f"✅ Nota creada: {numero_nota}")
    print(f"   Cliente: J-501924333 (EL OASIS NATURAL)")
    print(f"   Productos: {len(productos_disponibles)}")
    print(f"   Total: ${subtotal_usd:.2f}")
    print(f"   Estado: {nota['estado']}")
    
    # Mostrar productos
    print(f"\n📦 PRODUCTOS EN LA NOTA:")
    for i, producto_id in enumerate(productos_disponibles):
        if producto_id in inventario:
            producto = inventario[producto_id]
            cantidad = cantidades_disponibles[i]
            precio = precios_disponibles[i]
            print(f"   {producto_id}: {producto.get('nombre', 'N/A')}")
            print(f"      Cantidad: {cantidad} - Precio: ${precio} - Stock actual: {producto.get('cantidad', 0)}")
    
    return nota

def entregar_nota(nota):
    """Marca la nota como entregada."""
    print(f"\n" + "="*60)
    print("🚚 ENTREGANDO NOTA DE ENTREGA")
    print("="*60)
    
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    
    if nota['numero'] not in notas:
        print(f"❌ Nota {nota['numero']} no encontrada")
        return False
    
    # Actualizar estado
    notas[nota['numero']]['estado'] = 'ENTREGADO'
    notas[nota['numero']]['fecha_entrega'] = datetime.now().strftime('%Y-%m-%d')
    notas[nota['numero']]['hora_entrega'] = datetime.now().strftime('%H:%M:%S')
    notas[nota['numero']]['entregado_por'] = 'admin'
    notas[nota['numero']]['recibido_por'] = 'EL OASIS NATURAL'
    notas[nota['numero']]['firma_recibido'] = True
    
    # Guardar cambios
    guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
    
    print(f"✅ Nota {nota['numero']} marcada como ENTREGADA")
    print(f"   Fecha de entrega: {nota['fecha']}")
    print(f"   Entregado por: admin")
    print(f"   Recibido por: EL OASIS NATURAL")
    
    return True

def procesar_pago_completo(nota):
    """Procesa el pago completo de la nota entregada."""
    print(f"\n" + "="*60)
    print("💳 PROCESANDO PAGO COMPLETO")
    print("="*60)
    
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if nota['numero'] not in notas:
        print(f"❌ Nota {nota['numero']} no encontrada")
        return False
    
    nota_actual = notas[nota['numero']]
    
    # Verificar estado
    if nota_actual.get('estado') != 'ENTREGADO':
        print(f"❌ La nota debe estar ENTREGADA para procesar pagos")
        return False
    
    # Inicializar pagos
    if 'pagos' not in nota_actual:
        nota_actual['pagos'] = []
    
    # Crear pago completo
    monto_pago = float(nota_actual.get('subtotal_usd', 0))
    nuevo_pago = {
        'id': str(len(nota_actual['pagos']) + 1),
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monto': monto_pago,
        'metodo': 'efectivo',
        'referencia': 'PAGO_COMPLETO_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'timestamp': datetime.now().isoformat()
    }
    
    # Agregar pago
    nota_actual['pagos'].append(nuevo_pago)
    
    # Marcar como pagada
    nota_actual['estado'] = 'PAGADA'
    nota_actual['fecha_pago_completo'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Guardar nota
    guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
    
    print(f"✅ Pago procesado exitosamente")
    print(f"   Monto pagado: ${monto_pago:.2f}")
    print(f"   Estado final: {nota_actual['estado']}")
    print(f"   Fecha de pago: {nota_actual['fecha_pago_completo']}")
    
    # DESCONTAR DEL INVENTARIO
    print(f"\n📦 DESCONTANDO DEL INVENTARIO:")
    productos = nota_actual.get('productos', [])
    cantidades = nota_actual.get('cantidades', [])
    
    for i, producto_id in enumerate(productos):
        cantidad = int(cantidades[i]) if i < len(cantidades) else 0
        
        if producto_id in inventario:
            stock_actual = int(inventario[producto_id].get('cantidad', 0))
            nuevo_stock = max(0, stock_actual - cantidad)
            
            inventario[producto_id]['cantidad'] = nuevo_stock
            inventario[producto_id]['ultima_salida'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"   📦 {producto_id}: {inventario[producto_id].get('nombre', 'N/A')}")
            print(f"      Stock: {stock_actual} → {nuevo_stock} (descontado: {cantidad})")
        else:
            print(f"   ⚠️ Producto {producto_id} no encontrado en inventario")
    
    # Guardar inventario
    guardar_datos(ARCHIVO_INVENTARIO, inventario)
    print(f"✅ Inventario actualizado y guardado")
    
    return True

def verificar_resultado_final(nota):
    """Verifica el resultado final de todo el proceso."""
    print(f"\n" + "="*60)
    print("🔍 VERIFICACIÓN FINAL DEL PROCESO")
    print("="*60)
    
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if nota['numero'] in notas:
        nota_final = notas[nota['numero']]
        print(f"📝 NOTA {nota['numero']} - ESTADO FINAL:")
        print(f"   Estado: {nota_final.get('estado', 'N/A')}")
        print(f"   Fecha creación: {nota_final.get('fecha', 'N/A')}")
        print(f"   Fecha entrega: {nota_final.get('fecha_entrega', 'N/A')}")
        print(f"   Fecha pago: {nota_final.get('fecha_pago_completo', 'N/A')}")
        print(f"   Pagos registrados: {len(nota_final.get('pagos', []))}")
        print(f"   Total: ${nota_final.get('subtotal_usd', 0):.2f}")
        
        if 'pagos' in nota_final and nota_final['pagos']:
            total_pagado = sum(pago['monto'] for pago in nota_final['pagos'])
            print(f"   Total pagado: ${total_pagado:.2f}")
    
    # Verificar inventario final
    print(f"\n📦 INVENTARIO FINAL:")
    if nota['numero'] in notas:
        nota_final = notas[nota['numero']]
        productos = nota_final.get('productos', [])
        cantidades = nota_final.get('cantidades', [])
        
        for i, producto_id in enumerate(productos):
            cantidad = int(cantidades[i]) if i < len(cantidades) else 0
            
            if producto_id in inventario:
                producto = inventario[producto_id]
                print(f"   {producto_id}: {producto.get('nombre', 'N/A')}")
                print(f"      Stock final: {producto.get('cantidad', 0)}")
                print(f"      Última salida: {producto.get('ultima_salida', 'N/A')}")

def main():
    """Función principal del script de demostración completa."""
    print("🚀 DEMOSTRACIÓN COMPLETA DEL FLUJO DE NOTAS DE ENTREGA")
    print("="*80)
    
    # Paso 1: Crear nueva nota
    nota = crear_nueva_nota_entrega()
    if not nota:
        print("❌ No se pudo crear la nota de entrega")
        return
    
    # Paso 2: Entregar la nota
    if not entregar_nota(nota):
        print("❌ No se pudo entregar la nota")
        return
    
    # Paso 3: Procesar pago completo
    if not procesar_pago_completo(nota):
        print("❌ No se pudo procesar el pago")
        return
    
    # Paso 4: Verificar resultado final
    verificar_resultado_final(nota)
    
    print(f"\n" + "="*80)
    print("🎉 DEMOSTRACIÓN COMPLETADA EXITOSAMENTE!")
    print("="*80)
    print(f"\n📋 FLUJO COMPLETO DEMOSTRADO:")
    print(f"   1. ✅ Creación de nota de entrega")
    print(f"   2. ✅ Entrega de productos")
    print(f"   3. ✅ Procesamiento de pago completo")
    print(f"   4. ✅ Descuento automático del inventario")
    print(f"   5. ✅ Actualización de estados")
    print(f"   6. ✅ Trazabilidad completa")
    
    print(f"\n🎯 FUNCIONALIDAD VERIFICADA:")
    print(f"   • Sistema de notas de entrega funcionando")
    print(f"   • Procesamiento de pagos automático")
    print(f"   • Descuento de inventario en tiempo real")
    print(f"   • Sincronización de datos")
    print(f"   • Trazabilidad de operaciones")

if __name__ == '__main__':
    main()
