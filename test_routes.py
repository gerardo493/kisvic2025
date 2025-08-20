#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar las rutas de facturas
"""

import requests
import json

def test_factura_routes():
    """Prueba las rutas de facturas"""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 PROBANDO RUTAS DE FACTURAS")
    print("=" * 50)
    
    # Lista de rutas a probar
    test_routes = [
        "/facturas",  # Lista de facturas
        "/facturas/3",  # Ver factura específica
        "/facturas/3/editar",  # Editar factura
        "/facturas/3/imprimir",  # Imprimir factura
        "/facturas//editar",  # URL problemática (doble barra)
        "/facturas//",  # URL problemática (doble barra)
        "/facturas/",  # URL problemática (barra final)
    ]
    
    for route in test_routes:
        print(f"\n🔗 Probando: {route}")
        try:
            response = requests.get(f"{base_url}{route}", allow_redirects=False)
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code == 302:  # Redirect
                print(f"   Redirect a: {response.headers.get('Location', 'N/A')}")
            elif response.status_code == 200:
                print(f"   ✅ Éxito")
            elif response.status_code == 404:
                print(f"   ❌ No encontrado")
            elif response.status_code == 405:
                print(f"   ❌ Método no permitido")
            else:
                print(f"   ⚠️ Status inesperado")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ No se pudo conectar al servidor")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    test_factura_routes()
