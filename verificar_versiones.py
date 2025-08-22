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
        
        try:
            import lxml
            print(f"✅ lxml: {lxml.__version__}")
        except ImportError:
            print("ℹ️  lxml: No instalado (se instalará en Render)")
        
        try:
            import gunicorn
            print(f"✅ Gunicorn: {gunicorn.__version__}")
        except ImportError:
            print("ℹ️  Gunicorn: No instalado (se instalará en Render)")
        
        print("\n🎯 Versiones esperadas (Ultra Estables en Render):")
        print("   Flask: 2.2.5")
        print("   Flask-WTF: 1.0.1")
        print("   WTForms: 3.0.1")
        print("   lxml: 4.9.1")
        print("   Python: 3.10.0")
        
        # Verificar compatibilidad
        if flask.__version__ == "2.2.5":
            print("\n✅ Flask 2.2.5 instalado correctamente")
        else:
            print(f"\n⚠️  NOTA: Flask {flask.__version__} en local (en Render será 2.2.5)")
            
        if flask_wtf.__version__ == "1.0.1":
            print("✅ Flask-WTF 1.0.1 instalado correctamente")
        else:
            print(f"⚠️  NOTA: Flask-WTF {flask_wtf.__version__} en local (en Render será 1.0.1)")
        
        print("\n💡 Información:")
        print("   • Las versiones locales pueden ser diferentes")
        print("   • En Render se instalarán las versiones ultra estables")
        print("   • lxml se instalará automáticamente en Render")
        print("   • Python 3.10 se usará en Render")
            
        return True
        
    except ImportError as e:
        print(f"❌ Error importando: {e}")
        return False

if __name__ == "__main__":
    verificar_versiones()
