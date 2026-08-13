# -*- coding: utf-8 -*-
"""Comprueba conexión a Firestore y estado de la configuración."""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)


def main():
    print('=' * 50)
    print('  VERIFICACIÓN FIREBASE - KISVIC')
    print('=' * 50)

    cred = os.path.join(BASE, 'firebase_credentials.json')
    cfg = os.path.join(BASE, 'firebase_config.json')

    if not os.path.exists(cfg):
        print('[X] Falta firebase_config.json')
        print('    Copia: copy firebase_config.json.example firebase_config.json')
        sys.exit(1)
    print('[OK] firebase_config.json')

    if not os.path.exists(cred):
        print('[X] Falta firebase_credentials.json')
        print('    Ejecuta: python configurar_firebase.py')
        sys.exit(1)
    print('[OK] firebase_credentials.json')

    os.environ['KISVIC_USE_FIREBASE'] = '1'
    from almacenamiento import usar_firebase, _nube_disponible_ahora, cargar_datos, guardar_datos

    if not usar_firebase():
        print('[X] Firebase no está activo en configuración')
        sys.exit(1)
    print('[OK] Firebase activado')

    if not _nube_disponible_ahora():
        print('[!] Sin internet o DNS (firestore.googleapis.com).')
        print('    El sistema usará archivos JSON locales.')
        sys.exit(0)

    prueba = {'verificacion': True}
    guardar_datos('_verificacion_firebase.json', prueba)
    leido = cargar_datos('_verificacion_firebase.json', crear_vacio=False)
    if leido and leido.get('verificacion'):
        print('[OK] Lectura/escritura en Firestore correcta')
        print()
        print('Proyecto: kisvic-facturacion')
        print('Colección: kisvic_datos')
        print('Consola: https://console.firebase.google.com/project/kisvic-facturacion/firestore')
    else:
        print('[X] No se pudo leer desde Firestore')
        sys.exit(1)


if __name__ == '__main__':
    main()
