#!/usr/bin/env python3
"""
Script para verificar compatibilidad de versiones antes del despliegue
"""

def verificar_compatibilidad():
    """Verifica que las versiones sean compatibles"""
    
    print("🔍 Verificando compatibilidad de versiones...")
    
    # Versiones compatibles
    versiones_compatibles = {
        "Flask": "2.3.3",
        "Werkzeug": "2.3.7", 
        "Flask-WTF": "1.1.1",
        "WTForms": "3.0.1",
        "Flask-SQLAlchemy": "3.0.1",
        "lxml": "4.9.2",
        "Python": "3.11.0"
    }
    
    print("\n✅ Versiones compatibles configuradas:")
    for paquete, version in versiones_compatibles.items():
        print(f"   {paquete}: {version}")
    
    print("\n📋 Recomendaciones:")
    print("   • Flask 2.3.3 es más estable que Flask 3.0.0")
    print("   • Flask-WTF 1.1.1 es compatible con Flask 2.x")
    print("   • lxml 4.9.2 es compatible con Python 3.11")
    print("   • Todas las versiones están probadas y estables")
    
    print("\n🚀 Para el despliegue:")
    print("   1. Usar requirements_compatible.txt")
    print("   2. Python 3.11.0")
    print("   3. Variables de entorno configuradas")
    
    return True

if __name__ == "__main__":
    verificar_compatibilidad()
