#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime

# Test constants
ULTIMA_TASA_BCV_FILE = "test_tasa.json"

def guardar_ultima_tasa_bcv(tasa):
    try:
        # Guardar tasa con fecha de actualización
        data = {
            'tasa': tasa,
            'fecha': datetime.now().isoformat(),
            'ultima_actualizacion': datetime.now().isoformat()
        }
        
        try:
            with open(ULTIMA_TASA_BCV_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            
            print(f"Tasa BCV guardada exitosamente: {tasa}")
            return True
                
        except Exception as e:
            print(f"Error guardando última tasa BCV: {e}")
            return False
    except Exception as e:
        print(f"Error general: {e}")
        return False

if __name__ == "__main__":
    print("Testing function...")
    result = guardar_ultima_tasa_bcv(135.0)
    print(f"Function result: {result}")
    print("Test completed successfully!")
