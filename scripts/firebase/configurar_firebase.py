# -*- coding: utf-8 -*-
"""Configura Firebase automáticamente e instala dependencias."""
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)


def instalar_dependencias():
    print('Instalando firebase-admin...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'firebase-admin>=6.5.0', '-q'])


def main():
    print('=' * 50)
    print('  CONFIGURACIÓN FIREBASE - KISVIC')
    print('=' * 50)
    print()

    try:
        instalar_dependencias()
    except subprocess.CalledProcessError as e:
        print(f'Error instalando dependencias: {e}')
        sys.exit(1)

    from almacenamiento import (
        configurar_firebase_automatico,
        descubrir_credenciales,
        migrar_todo_a_firebase,
        usar_firebase,
        DEFAULT_CREDENTIALS,
    )

    listo = configurar_firebase_automatico()
    cred = descubrir_credenciales()

    if not listo and not cred:
        print('Intentando configuracion automatica en la nube (Firebase CLI)...')
        try:
            from setup_firebase_cloud import main as setup_cloud
            setup_cloud()
            listo = usar_firebase()
        except Exception as e:
            print(f'No se pudo configurar automaticamente: {e}')

    if not listo and not cred:
        print()
        print('PASO MANUAL (solo una vez):')
        print('  1. https://console.firebase.google.com/')
        print('  2. Tu proyecto > Configuración > Cuentas de servicio')
        print('  3. Generar nueva clave privada')
        print(f'  4. Guardar el archivo como: {DEFAULT_CREDENTIALS}')
        print('  5. Volver a ejecutar: python configurar_firebase.py')
        sys.exit(1)

    if usar_firebase():
        print()
        print('Migrando todos los JSON a Firestore...')
        res = migrar_todo_a_firebase()
        ok = sum(1 for v in res.values() if v)
        print(f'Listo: {ok}/{len(res)} archivos en la nube.')
        marca = os.path.join(BASE, '.firebase_migrado')
        with open(marca, 'w', encoding='utf-8') as f:
            f.write('ok')
    else:
        print('Config guardada. Añade credenciales y vuelve a ejecutar este script.')

    print()
    print('Inicia el sistema con: python app.py')
    print('o usa: iniciar_con_firebase.bat')


if __name__ == '__main__':
    main()
