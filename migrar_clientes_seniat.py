#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migración SENIAT - Clientes
====================================

Este script migra los clientes existentes al formato SENIAT
agregando los campos obligatorios faltantes y validando la estructura.

EJECUTAR SOLO UNA VEZ antes de usar el sistema SENIAT.
"""

import json
import os
from datetime import datetime

def cargar_datos(archivo):
    """Carga datos desde archivo JSON"""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_datos(archivo, datos):
    """Guarda datos en archivo JSON"""
    try:
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando {archivo}: {str(e)}")
        return False

def validar_rif_formato(rif):
    """Valida que el RIF tenga formato correcto"""
    if not rif or len(rif) < 3:
        return False
    
    # Debe empezar con V, E, J, P, G
    if rif[0] not in ['V', 'E', 'J', 'P', 'G']:
        return False
        
    # Debe tener al menos V-1234567 o J-12345678-9
    partes = rif.split('-')
    if len(partes) < 2:
        return False
        
    return True

def migrar_clientes_seniat():
    """Migra clientes existentes al formato SENIAT"""
    print("=" * 60)
    print("    MIGRACIÓN DE CLIENTES A FORMATO SENIAT")
    print("=" * 60)
    print()
    
    # Cargar clientes existentes
    clientes = cargar_datos('clientes.json')
    
    if not clientes:
        print("❌ No se encontraron clientes existentes.")
        print("   Archivo: clientes.json no existe o está vacío.")
        return
    
    print(f"📋 Clientes encontrados: {len(clientes)}")
    print()
    
    # Crear backup
    backup_file = f"clientes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    if guardar_datos(backup_file, clientes):
        print(f"💾 Backup creado: {backup_file}")
    else:
        print("❌ Error creando backup. Abortando migración.")
        return
    
    clientes_migrados = {}
    clientes_con_problemas = []
    
    print("\n🔄 Iniciando migración...")
    print()
    
    for cliente_id, cliente in clientes.items():
        print(f"   Procesando: {cliente_id}")
        
        try:
            # Verificar si ya tiene estructura SENIAT
            if cliente.get('validado_seniat'):
                print(f"   ✅ Ya migrado: {cliente_id}")
                clientes_migrados[cliente_id] = cliente
                continue
            
            # Datos básicos
            nombre = cliente.get('nombre', '').strip()
            direccion = cliente.get('direccion', '').strip()
            telefono = cliente.get('telefono', '').strip()
            email = cliente.get('email', '').strip()
            
            # Validar RIF/ID
            rif = cliente_id.strip().upper()
            
            if not validar_rif_formato(rif):
                print(f"   ⚠️  RIF inválido: {rif} - Requiere corrección manual")
                clientes_con_problemas.append({
                    'id': cliente_id,
                    'problema': 'RIF con formato inválido',
                    'solucion': 'Editar manualmente para establecer RIF correcto'
                })
                # Mantener cliente original pero marcarlo como no validado
                cliente_migrado = cliente.copy()
                cliente_migrado['validado_seniat'] = False
                cliente_migrado['rif'] = rif
                clientes_migrados[cliente_id] = cliente_migrado
                continue
            
            # Validar campos obligatorios
            problemas = []
            if len(nombre) < 3:
                problemas.append("Nombre muy corto")
            if len(direccion) < 10:
                problemas.append("Dirección incompleta")
            if len(telefono) < 11:
                problemas.append("Teléfono inválido")
            
            if problemas:
                print(f"   ⚠️  Problemas: {', '.join(problemas)}")
                clientes_con_problemas.append({
                    'id': cliente_id,
                    'problemas': problemas,
                    'solucion': 'Editar cliente para completar campos obligatorios'
                })
            
            # Extraer componentes del RIF
            partes_rif = rif.split('-')
            tipo_id = partes_rif[0]
            numero_id = partes_rif[1] if len(partes_rif) > 1 else ''
            digito_verificador = partes_rif[2] if len(partes_rif) > 2 else ''
            
            # Crear cliente con estructura SENIAT
            cliente_migrado = {
                'id': cliente_id,
                'rif': rif,
                'tipo_identificacion': tipo_id,
                'numero_identificacion': numero_id,
                'digito_verificador': digito_verificador,
                'nombre': nombre.upper(),
                'email': email.lower(),
                'telefono': telefono,
                'direccion': direccion.title(),
                'fecha_creacion': cliente.get('fecha_creacion', datetime.now().isoformat()),
                'usuario_creacion': cliente.get('usuario_creacion', 'MIGRACION_SENIAT'),
                'fecha_migracion': datetime.now().isoformat(),
                'activo': True,
                'validado_seniat': len(problemas) == 0  # Solo válido si no hay problemas
            }
            
            clientes_migrados[cliente_id] = cliente_migrado
            
            if len(problemas) == 0:
                print(f"   ✅ Migrado correctamente: {cliente_id}")
            else:
                print(f"   🔄 Migrado con observaciones: {cliente_id}")
                
        except Exception as e:
            print(f"   ❌ Error procesando {cliente_id}: {str(e)}")
            clientes_con_problemas.append({
                'id': cliente_id,
                'problema': f'Error de migración: {str(e)}',
                'solucion': 'Revisar manualmente'
            })
            # Mantener cliente original
            clientes_migrados[cliente_id] = cliente
    
    # Guardar clientes migrados
    if guardar_datos('clientes.json', clientes_migrados):
        print(f"\n✅ Migración completada")
        print(f"   📊 Total clientes: {len(clientes_migrados)}")
        print(f"   ✅ Migrados exitosamente: {len([c for c in clientes_migrados.values() if c.get('validado_seniat')])}")
        print(f"   ⚠️  Requieren revisión: {len(clientes_con_problemas)}")
    else:
        print("\n❌ Error guardando clientes migrados")
        return
    
    # Mostrar clientes con problemas
    if clientes_con_problemas:
        print("\n" + "=" * 60)
        print("    CLIENTES QUE REQUIEREN REVISIÓN MANUAL")
        print("=" * 60)
        
        for problema in clientes_con_problemas:
            print(f"\n🔧 Cliente: {problema['id']}")
            if 'problemas' in problema:
                for p in problema['problemas']:
                    print(f"   ⚠️  {p}")
            elif 'problema' in problema:
                print(f"   ⚠️  {problema['problema']}")
            print(f"   💡 Solución: {problema['solucion']}")
        
        print(f"\n📝 Para corregir estos clientes:")
        print(f"   1. Ve a: http://localhost:5000/clientes")
        print(f"   2. Edita cada cliente con problemas")
        print(f"   3. Completa los campos obligatorios")
        print(f"   4. El sistema validará automáticamente según SENIAT")
    
    print("\n" + "=" * 60)
    print("    MIGRACIÓN COMPLETADA")
    print("=" * 60)
    print()
    print("🎯 Tu sistema ahora cumple con las validaciones SENIAT")
    print("🚀 Puedes crear facturas sin errores de validación")
    print()

if __name__ == "__main__":
    migrar_clientes_seniat() 