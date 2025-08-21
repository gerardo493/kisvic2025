#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple para verificar Git
"""

import subprocess
import sys

def test_git():
    print("🔍 Probando Git...")
    
    try:
        # Probar versión de Git
        result = subprocess.run(['git', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Git funciona: {result.stdout.strip()}")
        
        # Probar configuración de usuario
        try:
            name_result = subprocess.run(['git', 'config', 'user.name'], 
                                       capture_output=True, text=True, check=True)
            email_result = subprocess.run(['git', 'config', 'user.email'], 
                                        capture_output=True, text=True, check=True)
            
            print(f"👤 Usuario: {name_result.stdout.strip()}")
            print(f"📧 Email: {email_result.stdout.strip()}")
            
        except subprocess.CalledProcessError:
            print("⚠️  Git no tiene configuración de usuario")
            
        # Probar si hay repositorio
        try:
            status_result = subprocess.run(['git', 'status'], 
                                         capture_output=True, text=True, check=True)
            print("✅ Repositorio Git encontrado")
            print("Estado:", status_result.stdout[:200] + "...")
            
        except subprocess.CalledProcessError:
            print("⚠️  No hay repositorio Git en este directorio")
            
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Error con Git: {e}")
        print("Git no está instalado o no funciona")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_git()
    input("\nPresiona Enter para salir...")
