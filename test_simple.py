import requests

def test_simple():
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Prueba simple de la aplicación")
    print("=" * 40)
    
    # Probar la URL problemática
    try:
        print("🔗 Probando POST /facturas//editar")
        response = requests.post(f"{base_url}/facturas//editar", allow_redirects=False)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 302:
            location = response.headers.get('Location', 'N/A')
            print(f"   ✅ Redirect a: {location}")
        else:
            print(f"   ⚠️ Status inesperado")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n✅ Prueba completada")

if __name__ == "__main__":
    test_simple()
