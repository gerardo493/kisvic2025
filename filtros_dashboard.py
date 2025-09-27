from datetime import datetime
import json
import os

# Constantes del sistema
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_FACTURAS = 'facturas_json/facturas.json'
ULTIMA_TASA_BCV_FILE = 'ultima_tasa_bcv.json'

def cargar_datos(archivo):
    """Carga datos desde un archivo JSON."""
    try:
        if os.path.exists(archivo):
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error cargando {archivo}: {e}")
        return {}

def obtener_tasa_bcv():
    """Obtiene la tasa BCV actual."""
    try:
        if not os.path.exists(ULTIMA_TASA_BCV_FILE):
            return 36.0  # Tasa por defecto
        
        with open(ULTIMA_TASA_BCV_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tasa = float(data.get('tasa', 36.0))
            return tasa if tasa > 10 else 36.0
    except Exception:
        return 36.0

def obtener_estadisticas_filtradas(filtro_tipo=None, filtro_valor=None, tarjeta=None):
    """Obtiene estadísticas para el dashboard con filtros opcionales por tarjeta."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    
    # Aplicar filtros de fecha si se especifican
    facturas_filtradas = facturas
    if filtro_tipo and filtro_valor:
        facturas_filtradas = {}
        try:
            for factura_id, factura in facturas.items():
                fecha_factura = datetime.strptime(factura['fecha'], '%Y-%m-%d')
                hoy = datetime.now()
                
                if filtro_tipo == 'año' and fecha_factura.year == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'mes' and fecha_factura.month == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'dia' and fecha_factura.day == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'hoy' and fecha_factura.date() == hoy.date():
                    facturas_filtradas[factura_id] = factura
        except (ValueError, KeyError) as e:
            print(f"Error aplicando filtro: {e}")
            facturas_filtradas = facturas
    
    mes_actual = datetime.now().month
    total_clientes = len(clientes)
    total_productos = len(inventario)
    facturas_mes = sum(1 for f in facturas_filtradas.values() if datetime.strptime(f['fecha'], '%Y-%m-%d').month == mes_actual)
    
    # Calcular cuentas por cobrar
    total_cobrar_usd = 0
    for f in facturas_filtradas.values():
        total_facturado = float(f.get('total_usd', 0))
        total_abonado = float(f.get('total_abonado', 0))
        saldo = max(0, total_facturado - total_abonado)
        if saldo > 0:  # Considerar cualquier saldo mayor a 0
            total_cobrar_usd += saldo
    
    # Obtener tasa BCV
    tasa_bcv = obtener_tasa_bcv()
    total_cobrar_bs = total_cobrar_usd * tasa_bcv
    
    # Crear lista de facturas con ID incluido para el dashboard
    facturas_con_id = []
    for factura_id, factura in facturas_filtradas.items():
        factura_copia = factura.copy()
        factura_copia['id'] = factura_id  # Agregar el ID a la factura
        facturas_con_id.append(factura_copia)
    
    ultimas_facturas = sorted(facturas_con_id, key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'), reverse=True)[:5]
    productos_bajo_stock = [p for p in inventario.values() if int(p.get('cantidad', p.get('stock', 0))) < 10]
    
    # Calcular pagos recibidos
    total_pagos_recibidos_usd = 0
    total_pagos_recibidos_bs = 0
    for f in facturas_filtradas.values():
        if 'pagos' in f and f['pagos']:
            for pago in f['pagos']:
                fecha_factura = f.get('fecha', '')
                try:
                    if fecha_factura and datetime.strptime(fecha_factura, '%Y-%m-%d').month == mes_actual:
                        monto = float(pago.get('monto', 0))
                        total_pagos_recibidos_usd += monto
                        total_pagos_recibidos_bs += monto * float(f.get('tasa_bcv', tasa_bcv))
                except Exception:
                    continue
    
    # Calcular total facturado
    total_facturado_usd = sum(float(f.get('total_usd', 0)) for f in facturas_filtradas.values())
    cantidad_facturas = len(facturas_filtradas)
    promedio_factura_usd = total_facturado_usd / cantidad_facturas if cantidad_facturas > 0 else 0
    
    return {
        'total_clientes': total_clientes,
        'total_productos': total_productos,
        'facturas_mes': facturas_mes,
        'total_cobrar': f"{total_cobrar_usd:,.2f}",
        'total_cobrar_usd': total_cobrar_usd,
        'total_cobrar_bs': total_cobrar_bs,
        'tasa_bcv': tasa_bcv,
        'ultimas_facturas': ultimas_facturas,
        'productos_bajo_stock': productos_bajo_stock,
        'total_pagos_recibidos_usd': total_pagos_recibidos_usd,
        'total_pagos_recibidos_bs': total_pagos_recibidos_bs,
        'total_facturado_usd': total_facturado_usd,
        'promedio_factura_usd': promedio_factura_usd,
        'cantidad_facturas': cantidad_facturas,
        'filtro_aplicado': {
            'tipo': filtro_tipo,
            'valor': filtro_valor
        } if filtro_tipo else None
    }

def obtener_metricas_tarjeta(tarjeta, filtro_tipo=None, filtro_valor=None):
    """Obtiene métricas específicas para una tarjeta individual."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    tasa_bcv = obtener_tasa_bcv()
    
    # Aplicar filtros de fecha si se especifican
    facturas_filtradas = facturas
    if filtro_tipo and filtro_valor:
        facturas_filtradas = {}
        try:
            for factura_id, factura in facturas.items():
                fecha_factura = datetime.strptime(factura['fecha'], '%Y-%m-%d')
                hoy = datetime.now()
                
                if filtro_tipo == 'año' and fecha_factura.year == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'mes' and fecha_factura.month == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'hoy' and fecha_factura.date() == hoy.date():
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'semana' and fecha_factura.isocalendar()[1] == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'mes_especifico' and fecha_factura.month == int(filtro_valor):
                    facturas_filtradas[factura_id] = factura
                elif filtro_tipo == 'fecha_especifica' and fecha_factura.date() == datetime.strptime(filtro_valor, '%Y-%m-%d').date():
                    facturas_filtradas[factura_id] = factura
        except (ValueError, KeyError) as e:
            print(f"Error aplicando filtro: {e}")
            facturas_filtradas = facturas
    
    if tarjeta == 'cobranza':
        # Calcular cuentas por cobrar
        total_cobrar_usd = 0
        for f in facturas_filtradas.values():
            total_facturado = float(f.get('total_usd', 0))
            total_abonado = float(f.get('total_abonado', 0))
            saldo = max(0, total_facturado - total_abonado)
            if saldo > 0:
                total_cobrar_usd += saldo
        
        total_cobrar_bs = total_cobrar_usd * tasa_bcv
        return {
            'total_cobrar_usd': total_cobrar_usd,
            'total_cobrar_bs': total_cobrar_bs,
            'cantidad_facturas': len(facturas_filtradas)
        }
    
    elif tarjeta == 'pagos':
        # Calcular pagos recibidos
        total_pagos_recibidos_usd = 0
        total_pagos_recibidos_bs = 0
        for f in facturas_filtradas.values():
            if 'pagos' in f and f['pagos']:
                for pago in f['pagos']:
                    monto = float(pago.get('monto', 0))
                    total_pagos_recibidos_usd += monto
                    total_pagos_recibidos_bs += monto * float(f.get('tasa_bcv', tasa_bcv))
        
        return {
            'total_pagos_recibidos_usd': total_pagos_recibidos_usd,
            'total_pagos_recibidos_bs': total_pagos_recibidos_bs,
            'cantidad_facturas': len(facturas_filtradas)
        }
    
    elif tarjeta == 'facturado':
        # Calcular total facturado
        total_facturado_usd = sum(float(f.get('total_usd', 0)) for f in facturas_filtradas.values())
        cantidad_facturas = len(facturas_filtradas)
        promedio_factura_usd = total_facturado_usd / cantidad_facturas if cantidad_facturas > 0 else 0
        
        return {
            'total_facturado_usd': total_facturado_usd,
            'promedio_factura_usd': promedio_factura_usd,
            'cantidad_facturas': cantidad_facturas
        }
    
    return {}

def obtener_opciones_filtro():
    """Obtiene las opciones disponibles para los filtros."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    
    años = set()
    meses = set()
    dias = set()
    semanas = set()
    
    for factura in facturas.values():
        try:
            fecha = datetime.strptime(factura['fecha'], '%Y-%m-%d')
            años.add(fecha.year)
            meses.add(fecha.month)
            dias.add(fecha.day)
            semanas.add(fecha.isocalendar()[1])  # Número de semana
        except (ValueError, KeyError):
            continue
    
    return {
        'años': sorted(list(años), reverse=True),
        'meses': sorted(list(meses)),
        'dias': sorted(list(dias)),
        'semanas': sorted(list(semanas))
    }

def obtener_opciones_filtro_avanzado():
    """Obtiene las opciones para filtros avanzados con menús anidados."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    
    # Obtener semanas del año actual
    semanas_actuales = set()
    for factura in facturas.values():
        try:
            fecha = datetime.strptime(factura['fecha'], '%Y-%m-%d')
            if fecha.year == datetime.now().year:
                semanas_actuales.add(fecha.isocalendar()[1])
        except (ValueError, KeyError):
            continue
    
    # Obtener meses con datos
    meses_con_datos = set()
    for factura in facturas.values():
        try:
            fecha = datetime.strptime(factura['fecha'], '%Y-%m-%d')
            meses_con_datos.add(fecha.month)
        except (ValueError, KeyError):
            continue
    
    # Generar opciones de semanas
    opciones_semanas = []
    for semana in sorted(semanas_actuales):
        opciones_semanas.append({
            'valor': semana,
            'texto': f'Semana {semana}'
        })
    
    # Generar opciones de meses
    nombres_meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    opciones_meses = []
    for mes in sorted(meses_con_datos):
        opciones_meses.append({
            'valor': mes,
            'texto': nombres_meses[mes]
        })
    
    return {
        'semanas': opciones_semanas,
        'meses': opciones_meses
    }
