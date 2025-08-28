#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear una nueva nota de entrega y sincronizarla con cuentas por cobrar.
"""

import json
import os
from datetime import datetime

# Archivos de datos
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_CUENTAS = 'cuentas_por_cobrar.json'

def cargar_datos(nombre_archivo):
    """Carga datos desde un archivo JSON."""
    try:
        if not os.path.exists(nombre_archivo):
            return {}
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
            if not contenido:
                return {}
            return json.loads(contenido)
    except Exception as e:
        print(f"❌ Error leyendo {nombre_archivo}: {e}")
        return {}

def guardar_datos(nombre_archivo, datos):
    """Guarda datos en un archivo JSON con verificación."""
    try:
        directorio = os.path.dirname(nombre_archivo)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        
        # Guardar datos
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
        
        # Verificar que se guardó correctamente
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            datos_verificados = json.load(f)
        
        if len(datos_verificados) == len(datos):
            print(f"✅ Datos guardados y verificados en {nombre_archivo}")
            return True
        else:
            print(f"❌ Error: Datos no se guardaron correctamente en {nombre_archivo}")
            return False
            
    except Exception as e:
        print(f"❌ Error guardando {nombre_archivo}: {e}")
        return False

def crear_nota_entrega_sincronizada():
    """Crea una nueva nota de entrega y la sincroniza."""
    print("📝 CREANDO NUEVA NOTA DE ENTREGA SINCRONIZADA")
    print("="*60)
    
    # Cargar datos existentes
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    print(f"📊 Estado inicial:")
    print(f"   Notas existentes: {len(notas)}")
    print(f"   Productos en inventario: {len(inventario)}")
    
    # Obtener numeración secuencial
    numero_secuencial = len(notas) + 1
    numero_nota = f"NE-{numero_secuencial:04d}"
    
    # Seleccionar productos del inventario (productos con stock disponible)
    productos_disponibles = []
    cantidades_disponibles = []
    precios_disponibles = []
    
    # Tomar los primeros 2 productos con stock
    contador = 0
    for producto_id, producto in inventario.items():
        if contador >= 2:
            break
        if producto.get('cantidad', 0) > 10:  # Solo productos con stock suficiente
            productos_disponibles.append(producto_id)
            cantidades_disponibles.append("3")  # Cantidad fija para prueba
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
        'observaciones': 'Nota de prueba para sincronización'
    }
    
    # Guardar nota
    notas[numero_nota] = nota
    
    print(f"📝 Nota creada en memoria: {numero_nota}")
    print(f"   Cliente: J-501924333 (EL OASIS NATURAL)")
    print(f"   Productos: {len(productos_disponibles)}")
    print(f"   Total: ${subtotal_usd:.2f}")
    print(f"   Estado: {nota['estado']}")
    
    # Guardar en archivo
    if guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas):
        print(f"💾 Nota guardada exitosamente en archivo")
        
        # Verificar que se guardó
        notas_verificadas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        if numero_nota in notas_verificadas:
            print(f"✅ Verificación: Nota {numero_nota} encontrada en archivo")
        else:
            print(f"❌ Error: Nota {numero_nota} NO encontrada en archivo")
            return None
    else:
        print(f"❌ Error guardando nota en archivo")
        return None
    
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

def entregar_y_pagar_nota(nota):
    """Entrega la nota y procesa el pago completo."""
    print(f"\n🚚 ENTREGANDO Y PAGANDO NOTA")
    print("="*60)
    
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    
    if nota['numero'] not in notas:
        print(f"❌ Nota {nota['numero']} no encontrada en archivo")
        return False
    
    # Marcar como entregada
    notas[nota['numero']]['estado'] = 'ENTREGADO'
    notas[nota['numero']]['fecha_entrega'] = datetime.now().strftime('%Y-%m-%d')
    notas[nota['numero']]['hora_entrega'] = datetime.now().strftime('%H:%M:%S')
    notas[nota['numero']]['entregado_por'] = 'admin'
    notas[nota['numero']]['recibido_por'] = 'EL OASIS NATURAL'
    notas[nota['numero']]['firma_recibido'] = True
    
    # Procesar pago completo
    monto_pago = float(nota.get('subtotal_usd', 0))
    nuevo_pago = {
        'id': '1',
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monto': monto_pago,
        'metodo': 'efectivo',
        'referencia': 'PAGO_COMPLETO_' + datetime.now().strftime('%Y%m%d_%H%M%S'),
        'timestamp': datetime.now().isoformat()
    }
    
    # Agregar pago
    notas[nota['numero']]['pagos'] = [nuevo_pago]
    notas[nota['numero']]['estado'] = 'PAGADA'
    notas[nota['numero']]['fecha_pago_completo'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Guardar cambios
    if guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas):
        print(f"✅ Nota {nota['numero']} entregada y pagada")
        print(f"   Estado: {notas[nota['numero']]['estado']}")
        print(f"   Monto pagado: ${monto_pago:.2f}")
        return True
    else:
        print(f"❌ Error guardando cambios")
        return False

def sincronizar_con_cuentas_por_cobrar(nota):
    """Sincroniza la nota pagada con cuentas por cobrar."""
    print(f"\n🔄 SINCRONIZANDO CON CUENTAS POR COBRAR")
    print("="*60)
    
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    
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
    if guardar_datos(ARCHIVO_CUENTAS, cuentas):
        print(f"✅ Sincronización exitosa")
        print(f"   Entrada creada: NE-{nota['numero']}")
        print(f"   Estado: Cobrada")
        print(f"   Total: ${nota.get('subtotal_usd', 0):.2f}")
        return True
    else:
        print(f"❌ Error guardando sincronización")
        return False

def verificar_sincronizacion(nota):
    """Verifica que la sincronización se haya completado correctamente."""
    print(f"\n🔍 VERIFICANDO SINCRONIZACIÓN")
    print("="*60)
    
    # Verificar nota
    notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
    if nota['numero'] in notas:
        nota_final = notas[nota['numero']]
        print(f"📝 NOTA {nota['numero']}:")
        print(f"   Estado: {nota_final.get('estado', 'N/A')}")
        print(f"   Pagos: {len(nota_final.get('pagos', []))}")
        print(f"   Total: ${nota_final.get('subtotal_usd', 0):.2f}")
    else:
        print(f"❌ Nota {nota['numero']} no encontrada")
        return False
    
    # Verificar cuentas por cobrar
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    nota_en_cuentas = None
    for cuenta_id, cuenta in cuentas.items():
        if cuenta.get('nota_entrega_origen') == nota['numero']:
            nota_en_cuentas = cuenta
            break
    
    if nota_en_cuentas:
        print(f"\n✅ SINCRONIZACIÓN VERIFICADA:")
        print(f"   ID Cuenta: {cuenta_id}")
        print(f"   RIF: {nota_en_cuentas.get('rif', 'N/A')}")
        print(f"   Total: ${nota_en_cuentas.get('total_usd', 0):.2f}")
        print(f"   Estado: {nota_en_cuentas.get('estado', 'N/A')}")
        print(f"   Tipo: {nota_en_cuentas.get('tipo_pago', 'N/A')}")
        return True
    else:
        print(f"\n❌ SINCRONIZACIÓN NO ENCONTRADA")
        return False

def main():
    """Función principal."""
    print("🚀 CREACIÓN Y SINCRONIZACIÓN DE NOTA DE ENTREGA")
    print("="*80)
    
    # Paso 1: Crear nota
    nota = crear_nota_entrega_sincronizada()
    if not nota:
        print("❌ No se pudo crear la nota")
        return
    
    # Paso 2: Entregar y pagar
    if not entregar_y_pagar_nota(nota):
        print("❌ No se pudo entregar y pagar la nota")
        return
    
    # Paso 3: Sincronizar con cuentas por cobrar
    if not sincronizar_con_cuentas_por_cobrar(nota):
        print("❌ No se pudo sincronizar")
        return
    
    # Paso 4: Verificar sincronización
    if not verificar_sincronizacion(nota):
        print("❌ La sincronización no se completó correctamente")
        return
    
    print(f"\n" + "="*80)
    print("🎉 SINCRONIZACIÓN COMPLETADA EXITOSAMENTE!")
    print("="*80)
    print(f"\n📋 RESUMEN:")
    print(f"   1. ✅ Nota de entrega creada")
    print(f"   2. ✅ Nota entregada y pagada")
    print(f"   3. ✅ Sincronizada con cuentas por cobrar")
    print(f"   4. ✅ Verificación completada")

if __name__ == '__main__':
    main()
