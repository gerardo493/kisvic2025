#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar URLs válidas de facturas
"""

import requests
import json

def test_valid_urls():
    """Prueba URLs válidas de facturas"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 PROBANDO URLs VÁLIDAS DE FACTURAS")
    print("=" * 50)
    
    # Primero obtener una lista de facturas para obtener IDs válidos
    try:
        print("📋 Obteniendo lista de facturas...")
        response = requests.get(f"{base_url}/facturas", allow_redirects=False)
        
        if response.status_code == 302:
            print("   ⚠️ Redirigido (probablemente a login)")
            print("   💡 Necesitas estar logueado para probar")
            return
        elif response.status_code == 200:
            print("   ✅ Lista de facturas obtenida")
        else:
            print(f"   ❌ Error: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Error conectando: {e}")
        return
    
    # URLs válidas a probar (usando ID de ejemplo)
    test_urls = [
        ("/facturas/3", "GET", "Ver factura válida"),
        ("/facturas/3/editar", "GET", "Editar factura válida"),
        ("/facturas/3/imprimir", "GET", "Imprimir factura válida"),
    ]
    
    print("\n🔗 Probando URLs válidas:")
    for route, method, description in test_urls:
        print(f"\n   {method} {route}")
        print(f"   Descripción: {description}")
        
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{route}", allow_redirects=False)
            else:  # POST
                response = requests.post(f"{base_url}{route}", allow_redirects=False)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Éxito - URL válida procesada")
            elif response.status_code == 302:
                location = response.headers.get('Location', 'N/A')
                print(f"   ⚠️ Redirect a: {location}")
            elif response.status_code == 404:
                print(f"   ❌ No encontrado")
            elif response.status_code == 405:
                print(f"   ❌ Método no permitido")
            else:
                print(f"   ⚠️ Status inesperado: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Pruebas completadas")
    
    print("\n💡 RESULTADO ESPERADO:")
    print("- URLs válidas: Status 200 o 302 (redirect a login)")
    print("- No más mensajes de 'URL de factura inválida'")
    print("- Edición de facturas funcionando correctamente")

if __name__ == "__main__":
    test_valid_urls()
