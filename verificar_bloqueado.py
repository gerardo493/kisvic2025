#!/usr/bin/env python3
"""
Script para verificar que las versiones bloqueadas estén instaladas correctamente
"""

def verificar_versiones_bloqueadas():
    """Verifica las versiones bloqueadas"""
    
    print("🔒 Verificando versiones BLOQUEADAS...")
    
    # Versiones esperadas (bloqueadas)
    versiones_bloqueadas = {
        "Flask": "2.2.5",
        "Flask-WTF": "1.0.1",
        "WTForms": "3.0.1",
        "lxml": "4.9.1",
        "Werkzeug": "2.2.3",
        "gunicorn": "20.1.0"
    }
    
    todas_correctas = True
    
    for paquete, version_esperada in versiones_bloqueadas.items():
        try:
            if paquete == "Flask":
                import flask
                version_actual = flask.__version__
            elif paquete == "Flask-WTF":
                import flask_wtf
                version_actual = flask_wtf.__version__
            elif paquete == "WTForms":
                import wtforms
                version_actual = wtforms.__version__
            elif paquete == "lxml":
                import lxml
                version_actual = lxml.__version__
            elif paquete == "Werkzeug":
                import werkzeug
                version_actual = werkzeug.__version__
            elif paquete == "gunicorn":
                import gunicorn
                version_actual = gunicorn.__version__
            else:
                continue
                
            if version_actual == version_esperada:
                print(f"✅ {paquete}: {version_actual} (CORRECTO)")
            else:
                print(f"❌ {paquete}: {version_actual} (ESPERADO: {version_esperada})")
                todas_correctas = False
                
        except ImportError as e:
            print(f"❌ {paquete}: No instalado - {e}")
            todas_correctas = False
    
    print(f"\n🎯 Resultado: {'✅ TODAS CORRECTAS' if todas_correctas else '❌ HAY PROBLEMAS'}")
    
    if not todas_correctas:
        print("\n💡 Solución:")
        print("   • Usar requirements_bloqueado.txt")
        print("   • Configuración agresiva en render.yaml")
        print("   • Limpiar completamente el entorno virtual")
    
    return todas_correctas

if __name__ == "__main__":
    verificar_versiones_bloqueadas()
