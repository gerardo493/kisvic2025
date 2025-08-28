#!/usr/bin/env python3
"""
Script de prueba para verificar la conectividad con la API de Render
"""

import requests
import json

def test_render_api():
    """Prueba la conectividad con la API de Render"""
    
    # Configuración
    api_key = "rnd_HyV4gu4CFwlcZZTdRdIJd6ERDitM"
    service_id = "srv-d2ckh46r433s73appvug"
    
    # Headers
    headers = {
        'Authorization': f'Token {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("PROBANDO CONECTIVIDAD CON RENDER API")
    print("=" * 50)
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Service ID: {service_id}")
    print()
    
    # 1. Probar acceso al servicio específico
    print("1. Probando acceso al servicio...")
    try:
        service_url = f"https://api.render.com/v1/services/{service_id}"
        response = requests.get(service_url, headers=headers)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            service_info = response.json()
            print(f"   Nombre del servicio: {service_info.get('name', 'N/A')}")
            print(f"   Tipo: {service_info.get('type', 'N/A')}")
            print(f"   Estado: {service_info.get('status', 'N/A')}")
            print("   ✅ Servicio accesible")
        elif response.status_code == 404:
            print("   ❌ Servicio no encontrado - verifica el Service ID")
            return False
        elif response.status_code == 401:
            print("   ❌ No autorizado - verifica la API Key")
            return False
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    print()
    
    # 2. Probar permisos de despliegue
    print("2. Probando permisos de despliegue...")
    try:
        deploy_url = f"https://api.render.com/v1/services/{service_id}/deploys"
        response = requests.get(deploy_url, headers=headers)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            deploys = response.json()
            print(f"   Despliegues disponibles: {len(deploys)}")
            print("   ✅ Permisos de despliegue confirmados")
        else:
            print(f"   ❌ Error al acceder a despliegues: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    print()
    print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    print("La API Key y Service ID son válidos y tienen los permisos correctos.")
    return True

if __name__ == "__main__":
    success = test_render_api()
    if not success:
        print("\n❌ HAY PROBLEMAS CON LA CONFIGURACIÓN")
        print("Revisa la API Key y Service ID")
        exit(1)
