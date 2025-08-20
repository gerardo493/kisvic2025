#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el decorador de validación de URLs
"""

import requests
import json

def test_url_validation():
    """Prueba la validación de URLs con el decorador"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 PROBANDO VALIDACIÓN DE URLs CON DECORADOR")
    print("=" * 60)
    
    # Lista de rutas problemáticas a probar
    test_routes = [
        # URLs válidas
        ("/facturas/3", "GET", "Ver factura válida"),
        ("/facturas/3/editar", "GET", "Editar factura válida"),
        ("/facturas/3/imprimir", "GET", "Imprimir factura válida"),
        
        # URLs problemáticas (doble barra)
        ("/facturas//editar", "GET", "GET con doble barra"),
        ("/facturas//editar", "POST", "POST con doble barra"),
        ("/facturas//", "GET", "GET con doble barra y barra final"),
        ("/facturas//", "POST", "POST con doble barra y barra final"),
        
        # URLs con barras extra
        ("/facturas///editar", "GET", "GET con triple barra"),
        ("/facturas///editar", "POST", "POST con triple barra"),
    ]
    
    for route, method, description in test_routes:
        print(f"\n🔗 Probando: {method} {route}")
        print(f"   Descripción: {description}")
        
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{route}", allow_redirects=False)
            else:  # POST
                response = requests.post(f"{base_url}{route}", allow_redirects=False)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 302:  # Redirect
                location = response.headers.get('Location', 'N/A')
                print(f"   ✅ Redirect a: {location}")
                if 'mostrar_facturas' in location:
                    print(f"   🎯 Redirigido correctamente a lista de facturas")
                else:
                    print(f"   ⚠️ Redirigido a ubicación inesperada")
            elif response.status_code == 200:
                print(f"   ✅ Éxito - URL válida procesada")
            elif response.status_code == 404:
                print(f"   ❌ No encontrado")
            elif response.status_code == 405:
                print(f"   ❌ Método no permitido")
            else:
                print(f"   ⚠️ Status inesperado: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ No se pudo conectar al servidor")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Pruebas completadas")
    
    print("\n💡 RESULTADO ESPERADO:")
    print("- URLs válidas: Status 200 o 302 (redirect a login)")
    print("- URLs con doble barra: Status 302 (redirect a /facturas)")
    print("- No más errores 405 (Method Not Allowed)")

if __name__ == "__main__":
    test_url_validation()
