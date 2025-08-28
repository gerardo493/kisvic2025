#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps

# Crear aplicación Flask
app = Flask(__name__)
app.secret_key = 'notas-entrega-secret-key-2025'

# Constantes
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'

# Decorador para requerir login (simulado)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simular login para pruebas
        return f(*args, **kwargs)
    return decorated_function

def cargar_datos(nombre_archivo):
    """Carga datos desde un archivo JSON."""
    try:
        if not os.path.exists(nombre_archivo):
            return {}
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
            if not contenido.strip():
                return {}
            return json.loads(contenido)
    except Exception as e:
        print(f"Error leyendo {nombre_archivo}: {e}")
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
        print(f"Error guardando {nombre_archivo}: {e}")
        return False

# Ruta principal
@app.route('/')
def index():
    return """
    <h1>🚚 Sistema de Notas de Entrega</h1>
    <p><a href="/notas-entrega">Ver Notas de Entrega</a></p>
    <p><a href="/notas-entrega/nueva">Nueva Nota de Entrega</a></p>
    """

# Ruta para mostrar notas de entrega
@app.route('/notas-entrega')
@login_required
def mostrar_notas_entrega():
    """Muestra la lista de notas de entrega."""
    try:
        notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        
        # Agregar información del cliente a cada nota
        for nota in notas.values():
            cliente_id = nota.get('cliente_id')
            if cliente_id in clientes:
                nota['cliente_nombre'] = clientes[cliente_id].get('nombre', 'N/A')
            else:
                nota['cliente_nombre'] = 'Cliente no encontrado'
        
        return render_template('notas_entrega.html', notas=notas, clientes=clientes)
    except Exception as e:
        return f'Error cargando notas de entrega: {e}'

# Ruta para crear nueva nota
@app.route('/notas-entrega/nueva', methods=['GET', 'POST'])
@login_required
def nueva_nota_entrega():
    """Crea una nueva nota de entrega."""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cliente_id = request.form['cliente_id']
            fecha = request.form['fecha']
            modalidad_pago = request.form['modalidad_pago']
            
            # Obtener productos, cantidades y precios
            productos = request.form.getlist('productos[]')
            cantidades = request.form.getlist('cantidades[]')
            precios = request.form.getlist('precios[]')
            
            # Calcular totales
            subtotal_usd = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(precios)))
            
            # Obtener numeración secuencial
            notas = cargar_datos(ARCHIVO_NOTAS_ENTREGA)
            numero_secuencial = len(notas) + 1
            numero_nota = f"NE-{numero_secuencial:04d}"
            
            # Crear nota de entrega
            nota = {
                'numero': numero_nota,
                'numero_secuencial': numero_secuencial,
                'fecha': fecha,
                'modalidad_pago': modalidad_pago,
                'productos': productos,
                'cantidades': cantidades,
                'precios': precios,
                'subtotal_usd': subtotal_usd,
                'estado': 'PENDIENTE_ENTREGA'
            }
            
            # Guardar nota
            notas[numero_nota] = nota
            guardar_datos(ARCHIVO_NOTAS_ENTREGA, notas)
            
            return redirect(url_for('mostrar_notas_entrega'))
            
        except Exception as e:
            return f'Error creando nota: {e}'
    
    # GET: mostrar formulario
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('nota_entrega_form.html', clientes=clientes, inventario=inventario)

if __name__ == '__main__':
    print("🚀 Iniciando aplicación de Notas de Entrega en puerto 5001...")
    print("📱 Accede a: http://127.0.0.1:5001")
    app.run(debug=True, host='127.0.0.1', port=5001)
