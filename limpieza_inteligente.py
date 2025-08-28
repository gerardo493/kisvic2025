#!/usr/bin/env python3
"""
Script de LIMPIEZA INTELIGENTE que preserva la estructura del código
"""

import re

def limpieza_inteligente():
    """Elimina funciones duplicadas preservando la estructura"""
    
    print("🧹 INICIANDO LIMPIEZA INTELIGENTE...")
    
    # Leer el archivo
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar funciones duplicadas de manera más específica
    funciones_duplicadas = {}
    
    # Patrón para encontrar funciones completas
    pattern = r'@app\.route\([^)]+\)\s*\n@login_required\s*\ndef\s+(\w+)\s*\([^)]*\):(.*?)(?=@app\.route|if __name__|$)'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    print(f"📊 Encontradas {len(matches)} funciones con decoradores")
    
    # Agrupar por nombre de función
    for match in matches:
        nombre_funcion = match.group(1)
        if nombre_funcion not in funciones_duplicadas:
            funciones_duplicadas[nombre_funcion] = []
        funciones_duplicadas[nombre_funcion].append({
            'start': match.start(),
            'end': match.end(),
            'content': match.group(0)
        })
    
    # Identificar duplicados
    duplicados_a_eliminar = []
    for nombre, funciones in funciones_duplicadas.items():
        if len(funciones) > 1:
            print(f"🚨 Función '{nombre}' duplicada {len(funciones)} veces")
            # Mantener la primera, marcar las demás para eliminar
            for i, func in enumerate(funciones[1:], 1):
                duplicados_a_eliminar.append({
                    'nombre': nombre,
                    'start': func['start'],
                    'end': func['end'],
                    'numero': i
                })
    
    if not duplicados_a_eliminar:
        print("✅ No se encontraron funciones duplicadas")
        return True
    
    # Eliminar duplicados en orden inverso para no afectar las posiciones
    duplicados_a_eliminar.sort(key=lambda x: x['start'], reverse=True)
    
    contenido_limpio = content
    eliminaciones = 0
    
    for dup in duplicados_a_eliminar:
        print(f"🗑️  Eliminando duplicado #{dup['numero']} de '{dup['nombre']}'")
        
        # Reemplazar con comentario simple
        reemplazo = f"# NOTA: La función {dup['nombre']} ya está definida anteriormente\n"
        contenido_limpio = contenido_limpio[:dup['start']] + reemplazo + contenido_limpio[dup['end']:]
        
        eliminaciones += 1
    
    # Guardar archivo limpio
    with open('app_inteligente_limpio.py', 'w', encoding='utf-8') as f:
        f.write(contenido_limpio)
    
    print(f"\n🎉 LIMPIEZA INTELIGENTE COMPLETADA!")
    print(f"✅ Eliminadas {eliminaciones} funciones duplicadas")
    print(f"✅ Archivo guardado como 'app_inteligente_limpio.py'")
    
    return True

if __name__ == "__main__":
    limpieza_inteligente()
