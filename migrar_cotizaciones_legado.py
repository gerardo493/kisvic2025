#!/usr/bin/env python3
"""Migra cotizaciones del archivo legado cotizaciones.json al formato cotizacion_<numero>.json."""

import json
import os
import shutil
from datetime import datetime

ARCHIVO_LEGADO = 'cotizaciones_json/cotizaciones.json'
COTIZACIONES_DIR = 'cotizaciones_json'
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'


def cargar_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_total_usd(total_str):
    if isinstance(total_str, (int, float)):
        return float(total_str)
    if not total_str:
        return 0.0
    return float(str(total_str).replace('$', '').replace(',', '').strip())


def migrar():
    legado = cargar_json(ARCHIVO_LEGADO)
    if not legado:
        print('No hay cotizaciones legadas para migrar.')
        return 0

    clientes = cargar_json(ARCHIVO_CLIENTES)
    inventario = cargar_json(ARCHIVO_INVENTARIO)
    os.makedirs(COTIZACIONES_DIR, exist_ok=True)

    backup = f"{ARCHIVO_LEGADO}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(ARCHIVO_LEGADO, backup)
    print(f'Backup: {backup}')

    migradas = 0
    for key, cot in legado.items():
        if not isinstance(cot, dict):
            continue

        numero = str(cot.get('numero') or cot.get('numero_cotizacion') or key).strip()
        if not numero:
            numero = str(key)

        cliente_id = cot.get('cliente_id', '')
        cliente = clientes.get(cliente_id, {})
        if cliente_id and not cliente.get('id'):
            cliente = {**cliente, 'id': cliente_id}

        productos = cot.get('productos', [])
        cantidades = [str(c) for c in cot.get('cantidades', [])]
        precios = []
        subtotal_usd = 0.0
        for i, prod_id in enumerate(productos):
            try:
                cant = int(cantidades[i]) if i < len(cantidades) else 1
            except (TypeError, ValueError):
                cant = 1
            prod = inventario.get(str(prod_id), {})
            precio = float(prod.get('precio', 0) or 0)
            if cot.get('precios') and i < len(cot['precios']):
                try:
                    precio = float(cot['precios'][i])
                except (TypeError, ValueError):
                    pass
            precios.append(precio)
            subtotal_usd += precio * cant

        total_usd = parse_total_usd(cot.get('total_usd', cot.get('total', subtotal_usd)))
        if subtotal_usd <= 0 and total_usd > 0:
            subtotal_usd = total_usd

        validez_dias = int(cot.get('validez_dias', cot.get('validez', 3)) or 3)
        tasa_bcv = float(cot.get('tasa_bcv', 0) or 0)

        nueva = {
            'numero_cotizacion': numero,
            'fecha': cot.get('fecha', datetime.now().strftime('%Y-%m-%d')),
            'hora': cot.get('hora', '00:00'),
            'cliente': cliente,
            'productos': [str(p) for p in productos],
            'cantidades': cantidades,
            'precios': precios,
            'subtotal_usd': subtotal_usd,
            'subtotal_bs': subtotal_usd * tasa_bcv if tasa_bcv else 0,
            'descuento': float(cot.get('descuento', 0) or 0),
            'tipo_descuento': cot.get('tipo_descuento', 'bs'),
            'descuento_total': float(cot.get('descuento_total', 0) or 0),
            'iva': float(cot.get('iva', 16) or 16),
            'iva_total': float(cot.get('iva_total', 0) or 0),
            'total_usd': total_usd,
            'total_bs': float(cot.get('total_bs', 0) or 0),
            'tasa_bcv': tasa_bcv,
            'validez_dias': validez_dias,
            '_migrado_desde': f'legado:{key}',
        }

        base_name = f'cotizacion_{numero}.json'
        dest = os.path.join(COTIZACIONES_DIR, base_name)
        if os.path.exists(dest):
            dest = os.path.join(COTIZACIONES_DIR, f'cotizacion_{numero}_{key}.json')
            nueva['numero_cotizacion'] = f'{numero}_{key}'

        with open(dest, 'w', encoding='utf-8') as f:
            json.dump(nueva, f, ensure_ascii=False, indent=4)

        print(f'  OK -> {os.path.basename(dest)}')
        migradas += 1

    # Renombrar legado para que no interfiera con el listado
    legado_renombrado = os.path.join(COTIZACIONES_DIR, 'cotizaciones_legado_archivado.json')
    if os.path.exists(ARCHIVO_LEGADO):
        shutil.move(ARCHIVO_LEGADO, legado_renombrado)
        print(f'Archivo legado archivado: {legado_renombrado}')

    print(f'\nMigradas: {migradas} cotizacion(es)')
    return migradas


if __name__ == '__main__':
    migrar()
