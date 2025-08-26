#!/usr/bin/env python3
"""
Script para limpiar funciones duplicadas en app.py
"""

def limpiar_duplicados():
    """Limpia las funciones duplicadas"""
    
    print("🧹 Limpiando funciones duplicadas...")
    
    # Leer el archivo
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Contar ocurrencias
    ocurrencias = content.count('@app.route(\'/uploads/capturas/<filename>\')')
    print(f"📊 Encontradas {ocurrencias} rutas duplicadas")
    
    if ocurrencias > 1:
        # Reemplazar solo la segunda ocurrencia
        target = '''@app.route('/uploads/capturas/<filename>')
def serve_captura(filename):
    try:
        return send_from_directory(CAPTURAS_FOLDER, filename)
    except Exception as e:
        print(f"Error sirviendo captura {filename}: {str(e)}")
        abort(404)'''
        
        replacement = "# NOTA: La función serve_captura ya está definida anteriormente"
        
        # Encontrar la segunda ocurrencia
        first_pos = content.find(target)
        if first_pos != -1:
            second_pos = content.find(target, first_pos + 1)
            if second_pos != -1:
                # Reemplazar la segunda ocurrencia
                new_content = content[:second_pos] + replacement + content[second_pos + len(target):]
                
                # Guardar el archivo limpio
                with open('app_limpio.py', 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print("✅ Archivo limpio guardado como 'app_limpio.py'")
                return True
    
    print("❌ No se encontraron duplicados para limpiar")
    return False

if __name__ == "__main__":
    limpiar_duplicados()

