#!/usr/bin/env python3
"""
Script para eliminar la función index duplicada específica
"""

def eliminar_index_duplicada():
    """Elimina la función index duplicada"""
    
    print("🧹 Eliminando función index duplicada...")
    
    # Leer el archivo
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar la función duplicada específica (la que está en el medio)
    target_function = '''# --- Rutas protegidas ---
@app.route('/')
@login_required
def index():
    stats = obtener_estadisticas()
    # Calcular total facturado y promedio por factura
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    total_facturado_usd = sum(float(f.get('total_usd', 0)) for f in facturas.values())
    cantidad_facturas = len(facturas)
    promedio_factura_usd = total_facturado_usd / cantidad_facturas if cantidad_facturas > 0 else 0
    # Obtener tasa euro igual que antes
    try:
        # r = requests.get('https://s3.amazonaws.com/dolartoday/data.json', timeout=5)  # Temporarily commented out
        # data = r.json()  # Temporarily commented out
        # tasa_bcv_eur = float(data['EUR']['promedio']) if 'EUR' in data and 'promedio' in data['EUR'] else None  # Temporarily commented out
        tasa_bcv_eur = 0  # Temporarily set to 0
    except Exception:
        tasa_bcv_eur = 0
    advertencia_tasa = None
    if not stats.get('tasa_bcv') or stats.get('tasa_bcv', 0) < 1:
        advertencia_tasa = '¡Advertencia! No se ha podido obtener la tasa BCV actual.'
    stats['tasa_bcv_eur'] = tasa_bcv_eur
    return render_template('index.html', **stats, advertencia_tasa=advercia_tasa, total_facturado_usd=total_facturado_usd, promedio_factura_usd=promedio_factura_usd)'''
    
    # Buscar la primera ocurrencia
    first_pos = content.find(target_function)
    if first_pos != -1:
        # Buscar la segunda ocurrencia (la duplicada)
        second_pos = content.find(target_function, first_pos + 1)
        if second_pos != -1:
            # Eliminar la segunda ocurrencia
            new_content = content[:second_pos] + content[second_pos + len(target_function):]
            
            # Guardar el archivo limpio
            with open('app_sin_duplicados.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ Función index duplicada eliminada")
            print("✅ Archivo guardado como 'app_sin_duplicados.py'")
            return True
        else:
            print("❌ No se encontró la segunda ocurrencia")
            return False
    else:
        print("❌ No se encontró la primera ocurrencia")
        return False

if __name__ == "__main__":
    eliminar_index_duplicada()
