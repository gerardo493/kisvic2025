#!/usr/bin/env python3
"""
Script de diagnóstico detallado para la API de Render
"""

import requests
import json

def test_render_detailed():
    """Prueba detallada de la API de Render"""
    
    # Configuración
    api_key = "rnd_HyV4gu4CFwlcZZTdRdIJd6ERDitM"
    service_id = "srv-d2ckh46r433s73appvug"
    
    print("DIAGNOSTICO DETALLADO DE RENDER API")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Service ID: {service_id}")
    print()
    
    # Headers
    headers = {
        'Authorization': f'Token {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 1. Probar endpoint básico de servicios
    print("1. PROBANDO ENDPOINT DE SERVICIOS...")
    try:
        response = requests.get("https://api.render.com/v1/services", headers=headers)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            services = response.json()
            print(f"   ✅ Servicios accesibles: {len(services)}")
            for service in services[:3]:  # Mostrar solo los primeros 3
                print(f"      - {service.get('name', 'N/A')} (ID: {service.get('id', 'N/A')})")
        elif response.status_code == 401:
            print("   ❌ No autorizado - API Key inválida o sin permisos")
            return False
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    print()
    
    # 2. Probar acceso al servicio específico
    print("2. PROBANDO ACCESO AL SERVICIO ESPECÍFICO...")
    try:
        service_url = f"https://api.render.com/v1/services/{service_id}"
        response = requests.get(service_url, headers=headers)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            service_info = response.json()
            print(f"   ✅ Servicio encontrado:")
            print(f"      Nombre: {service_info.get('name', 'N/A')}")
            print(f"      Tipo: {service_info.get('type', 'N/A')}")
            print(f"      Estado: {service_info.get('status', 'N/A')}")
            print(f"      URL: {service_info.get('serviceUrl', 'N/A')}")
        elif response.status_code == 404:
            print("   ❌ Servicio no encontrado - Service ID incorrecto")
            return False
        elif response.status_code == 401:
            print("   ❌ No autorizado para este servicio específico")
            return False
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    print()
    
    # 3. Probar permisos de despliegue
    print("3. PROBANDO PERMISOS DE DESPLIEGUE...")
    try:
        deploy_url = f"https://api.render.com/v1/services/{service_id}/deploys"
        response = requests.get(deploy_url, headers=headers)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            deploys = response.json()
            print(f"   ✅ Despliegues accesibles: {len(deploys)}")
            if deploys:
                latest = deploys[0]
                print(f"      Último despliegue: {latest.get('status', 'N/A')} - {latest.get('createdAt', 'N/A')}")
        else:
            print(f"   ❌ Error al acceder a despliegues: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        return False
    
    print()
    
    # 4. Probar creación de despliegue (solo GET, no POST)
    print("4. PROBANDO CAPACIDAD DE CREAR DESPLIEGUE...")
    try:
        # Solo verificamos que podemos acceder al endpoint, no creamos nada
        deploy_url = f"https://api.render.com/v1/services/{service_id}/deploys"
        response = requests.options(deploy_url, headers=headers)
        print(f"   OPTIONS Status Code: {response.status_code}")
        
        if response.status_code in [200, 204, 405]:
            print("   ✅ Endpoint de despliegue accesible")
        else:
            print(f"   ⚠️  Endpoint de despliegue: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    print()
    print("✅ DIAGNOSTICO COMPLETADO!")
    return True

if __name__ == "__main__":
    success = test_render_detailed()
    if not success:
        print("\n❌ HAY PROBLEMAS CON LA CONFIGURACIÓN")
        print("Revisa la API Key y Service ID")
        exit(1)
