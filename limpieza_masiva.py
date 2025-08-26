#!/usr/bin/env python3
"""
Script de LIMPIEZA MASIVA para eliminar TODAS las funciones duplicadas
"""

import re

def limpieza_masiva():
    """Elimina TODAS las funciones duplicadas de una vez"""
    
    print("🧹 INICIANDO LIMPIEZA MASIVA - ELIMINANDO TODAS LAS FUNCIONES DUPLICADAS...")
    
    # Leer el archivo
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar todas las funciones definidas
    pattern = r'@app\.route\([^)]+\)\s*\n@login_required\s*\ndef\s+(\w+)\s*\([^)]*\):'
    matches = list(re.finditer(pattern, content))
    
    print(f"📊 Encontradas {len(matches)} funciones con decoradores")
    
    # Agrupar por nombre de función
    funciones_por_nombre = {}
    for match in matches:
        nombre_funcion = match.group(1)
        if nombre_funcion not in funciones_por_nombre:
            funciones_por_nombre[nombre_funcion] = []
        funciones_por_nombre[nombre_funcion].append(match.start())
    
    # Identificar funciones duplicadas
    funciones_duplicadas = {}
    for nombre, posiciones in funciones_por_nombre.items():
        if len(posiciones) > 1:
            funciones_duplicadas[nombre] = posiciones
            print(f"🚨 Función '{nombre}' duplicada {len(posiciones)} veces")
    
    if not funciones_duplicadas:
        print("✅ No se encontraron funciones duplicadas")
        return True
    
    # Eliminar duplicados (mantener solo la primera)
    contenido_limpio = content
    eliminaciones = 0
    
    for nombre, posiciones in funciones_duplicadas.items():
        # Mantener la primera, eliminar las demás
        for i, pos in enumerate(posiciones[1:], 1):
            print(f"🗑️  Eliminando duplicado #{i} de '{nombre}' en posición {pos}")
            
            # Buscar el inicio de la función
            start_pos = pos
            
            # Buscar el final de la función (hasta la siguiente función o fin de archivo)
            next_function = None
            for other_nombre, other_positions in funciones_por_nombre.items():
                for other_pos in other_positions:
                    if other_pos > pos:
                        if next_function is None or other_pos < next_function:
                            next_function = other_pos
            
            if next_function:
                end_pos = next_function
            else:
                # Si es la última función, buscar hasta el final del archivo
                end_pos = len(contenido_limpio)
            
            # Extraer la función completa
            funcion_completa = contenido_limpio[start_pos:end_pos]
            
            # Reemplazar con comentario
            reemplazo = f"# NOTA: La función {nombre} ya está definida anteriormente\n"
            contenido_limpio = contenido_limpio[:start_pos] + reemplazo + contenido_limpio[end_pos:]
            
            eliminaciones += 1
    
    # Guardar archivo completamente limpio
    with open('app_ultra_limpio.py', 'w', encoding='utf-8') as f:
        f.write(contenido_limpio)
    
    print(f"\n🎉 LIMPIEZA MASIVA COMPLETADA!")
    print(f"✅ Eliminadas {eliminaciones} funciones duplicadas")
    print(f"✅ Archivo guardado como 'app_ultra_limpio.py'")
    
    return True

if __name__ == "__main__":
    limpieza_masiva()
