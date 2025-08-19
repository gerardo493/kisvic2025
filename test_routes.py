#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_routes():
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Probando rutas del servidor...")
    print("=" * 50)
    
    # Ruta 1: Ruta raíz
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ GET / -> {response.status_code}")
    except Exception as e:
        print(f"❌ GET / -> Error: {e}")
    
    # Ruta 2: Ruta de recordatorio
    try:
        response = requests.post(f"{base_url}/cuentas-por-cobrar/enviar_recordatorio_whatsapp", 
                               json={"cliente_id": "26369968"},
                               headers={"Content-Type": "application/json"})
        print(f"✅ POST /cuentas-por-cobrar/enviar_recordatorio_whatsapp -> {response.status_code}")
        if response.status_code == 200:
            print(f"   Respuesta: {response.json()}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ POST /cuentas-por-cobrar/enviar_recordatorio_whatsapp -> Error: {e}")
    
    # Ruta 3: Ruta alternativa con parámetros
    try:
        response = requests.post(f"{base_url}/cuentas-por-cobrar/26369968/enviar_recordatorio_whatsapp", 
                               json={"cliente_id": "26369968"},
                               headers={"Content-Type": "application/json"})
        print(f"✅ POST /cuentas-por-cobrar/26369968/enviar_recordatorio_whatsapp -> {response.status_code}")
        if response.status_code == 200:
            print(f"   Respuesta: {response.json()}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ POST /cuentas-por-cobrar/26369968/enviar_recordatorio_whatsapp -> Error: {e}")
    
    # Ruta 4: Ruta de facturas
    try:
        response = requests.get(f"{base_url}/facturas")
        print(f"✅ GET /facturas -> {response.status_code}")
    except Exception as e:
        print(f"❌ GET /facturas -> Error: {e}")
    
    # Ruta 5: Ruta de prueba simple
    try:
        response = requests.get(f"{base_url}/test-simple")
        print(f"✅ GET /test-simple -> {response.status_code}")
    except Exception as e:
        print(f"❌ GET /test-simple -> Error: {e}")

if __name__ == "__main__":
    test_routes()
