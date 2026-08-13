# -*- coding: utf-8 -*-
"""Sube los JSON locales del sistema a Firebase Firestore."""
import os
import sys

os.environ.setdefault('KISVIC_USE_FIREBASE', '1')

from almacenamiento import (
    configurar_firebase_automatico,
    listar_archivos_migrables,
    migrar_todo_a_firebase,
    usar_firebase,
)


def main():
    configurar_firebase_automatico()
    if not usar_firebase():
        print('Falta firebase_credentials.json — ejecuta: python configurar_firebase.py')
        sys.exit(1)

    archivos = listar_archivos_migrables()
    if not archivos:
        print('No se encontraron archivos JSON para migrar.')
        sys.exit(0)

    print(f'Migrando {len(archivos)} archivo(s) a Firestore...')
    for a in archivos:
        print(f'  - {a}')

    resultados = migrar_todo_a_firebase()
    ok = sum(1 for v in resultados.values() if v)
    fail = len(resultados) - ok
    print(f'\nListo: {ok} correctos, {fail} con error.')
    if fail:
        sys.exit(1)


if __name__ == '__main__':
    main()
