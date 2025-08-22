#!/usr/bin/env python3
"""
Script para verificar que las versiones instaladas sean las correctas
"""

def verificar_versiones():
    """Verifica las versiones instaladas"""
    
    print("🔍 Verificando versiones instaladas...")
    
    try:
        import flask
        print(f"✅ Flask: {flask.__version__}")
        
        import flask_wtf
        print(f"✅ Flask-WTF: {flask_wtf.__version__}")
        
        import wtforms
        print(f"✅ WTForms: {wtforms.__version__}")
        
        import lxml
        print(f"✅ lxml: {lxml.__version__}")
        
        import gunicorn
        print(f"✅ Gunicorn: {gunicorn.__version__}")
        
        print("\n🎯 Versiones esperadas:")
        print("   Flask: 2.3.3")
        print("   Flask-WTF: 1.1.1")
        print("   WTForms: 3.0.1")
        print("   lxml: 4.9.2")
        
        # Verificar compatibilidad
        if flask.__version__ == "2.3.3":
            print("\n✅ Flask 2.3.3 instalado correctamente")
        else:
            print(f"\n❌ ERROR: Flask {flask.__version__} no es compatible")
            
        if flask_wtf.__version__ == "1.1.1":
            print("✅ Flask-WTF 1.1.1 instalado correctamente")
        else:
            print(f"❌ ERROR: Flask-WTF {flask_wtf.__version__} no es compatible")
            
        return True
        
    except ImportError as e:
        print(f"❌ Error importando: {e}")
        return False

if __name__ == "__main__":
    verificar_versiones()
