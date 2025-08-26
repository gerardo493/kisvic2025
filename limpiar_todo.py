#!/usr/bin/env python3
"""
Script para limpiar TODAS las funciones duplicadas en app.py
"""

def limpiar_todas_duplicadas():
    """Limpia todas las funciones duplicadas"""
    
    print("🧹 Limpiando TODAS las funciones duplicadas...")
    
    # Leer el archivo
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Lista de funciones a limpiar
    funciones_duplicadas = [
        {
            'nombre': 'serve_captura',
            'ruta': '@app.route(\'/uploads/capturas/<filename>\')',
            'funcion': '''@app.route('/uploads/capturas/<filename>')
def serve_captura(filename):
    try:
        return send_from_directory(CAPTURAS_FOLDER, filename)
    except Exception as e:
        print(f"Error sirviendo captura {filename}: {str(e)}")
        abort(404)''',
            'reemplazo': '# NOTA: La función serve_captura ya está definida anteriormente'
        },
        {
            'nombre': 'healthcheck',
            'ruta': '@app.route(\'/healthz\')',
            'funcion': '''@app.route('/healthz')
def healthcheck():
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        # Verificar que las carpetas críticas existen
        critical_dirs = [
            os.path.join(BASE_PATH, 'uploads'),
            os.path.join(BASE_PATH, 'uploads', 'capturas')
        ]
        for d in critical_dirs:
            os.makedirs(d, exist_ok=True)
        return jsonify({
            'status': 'ok',
            'time': now
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 500''',
            'reemplazo': '# NOTA: La función healthcheck ya está definida anteriormente'
        }
    ]
    
    # Limpiar cada función duplicada
    for func in funciones_duplicadas:
        print(f"🔍 Limpiando función: {func['nombre']}")
        
        # Contar ocurrencias
        ocurrencias = content.count(func['ruta'])
        print(f"   📊 Encontradas {ocurrencias} rutas")
        
        if ocurrencias > 1:
            # Reemplazar solo la segunda ocurrencia
            first_pos = content.find(func['funcion'])
            if first_pos != -1:
                second_pos = content.find(func['funcion'], first_pos + 1)
                if second_pos != -1:
                    # Reemplazar la segunda ocurrencia
                    content = content[:second_pos] + func['reemplazo'] + content[second_pos + len(func['funcion']):]
                    print(f"   ✅ Función {func['nombre']} limpiada")
                else:
                    print(f"   ⚠️  No se pudo encontrar la segunda ocurrencia de {func['nombre']}")
            else:
                print(f"   ⚠️  No se pudo encontrar la primera ocurrencia de {func['nombre']}")
        else:
            print(f"   ℹ️  Función {func['nombre']} no tiene duplicados")
    
    # Guardar el archivo completamente limpio
    with open('app_super_limpio.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Archivo completamente limpio guardado como 'app_super_limpio.py'")
    return True

if __name__ == "__main__":
    limpiar_todas_duplicadas()
