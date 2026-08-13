# -*- coding: utf-8 -*-
"""
Persistencia Kisvic: Firebase Firestore (nube) + JSON local (respaldo).
"""
from __future__ import annotations

import json
import os
import glob
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

# REST suele funcionar mejor que gRPC cuando hay problemas de DNS en Windows
os.environ.setdefault('GOOGLE_CLOUD_DISABLE_GRPC', 'true')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIREBASE_COLLECTION = os.environ.get('FIREBASE_COLLECTION', 'kisvic_datos')
CONFIG_FILE = os.path.join(BASE_DIR, 'firebase_config.json')
DEFAULT_CREDENTIALS = os.path.join(BASE_DIR, 'firebase_credentials.json')

CARPETAS_JSON = [
    'facturas_json',
    'cotizaciones_json',
    'notas_entrega_json',
]

ARCHIVOS_PRINCIPALES = [
    'clientes.json',
    'inventario.json',
    'facturas_json/facturas.json',
    'cotizaciones_json/cotizaciones.json',
    'notas_entrega_json/notas_entrega.json',
    'cuentas_por_cobrar.json',
    'ultima_tasa_bcv.json',
    'usuarios.json',
    'empresa.json',
    'control_numeracion_fiscal.json',
    'ordenes_servicio.json',
    'chatbot_config.json',
]

_firestore_db = None
_firebase_initialized = False
_use_firebase: Optional[bool] = None
_nube_pausada_hasta: float = 0.0
_aviso_offline_mostrado: bool = False
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='firebase-sync')
_sync_lock = threading.Lock()
_pending_sync: Dict[str, Any] = {}

T = TypeVar('T')

TIMEOUT_NUBE = float(os.environ.get('KISVIC_FIREBASE_TIMEOUT', '8'))
PAUSA_OFFLINE_MIN = float(os.environ.get('KISVIC_FIREBASE_OFFLINE_MIN', '5'))


def _leer_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'[almacenamiento] No se pudo leer {CONFIG_FILE}: {e}')
    return {}


def _ruta_credenciales() -> str:
    cfg = _leer_config()
    cred_path = (
        os.environ.get('FIREBASE_CREDENTIALS')
        or cfg.get('credentials_path')
        or DEFAULT_CREDENTIALS
    )
    if not os.path.isabs(cred_path):
        cred_path = os.path.join(BASE_DIR, cred_path)
    return cred_path


def _es_cuenta_servicio(ruta: str) -> bool:
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return (
            data.get('type') == 'service_account'
            and bool(data.get('private_key'))
            and bool(data.get('project_id'))
        )
    except Exception:
        return False


def descubrir_credenciales() -> Optional[str]:
    """Busca un JSON de cuenta de servicio de Firebase en el proyecto y carpetas del usuario."""
    if os.path.exists(DEFAULT_CREDENTIALS) and _es_cuenta_servicio(DEFAULT_CREDENTIALS):
        return DEFAULT_CREDENTIALS

    busqueda: List[str] = [
        os.path.join(BASE_DIR, '*.json'),
        os.path.join(BASE_DIR, 'credentials', '*.json'),
    ]
    user = os.environ.get('USERPROFILE') or os.environ.get('HOME') or ''
    if user:
        busqueda.extend([
            os.path.join(user, 'Downloads', '*.json'),
            os.path.join(user, 'Desktop', '*.json'),
            os.path.join(user, 'OneDrive', 'Downloads', '*.json'),
            os.path.join(user, 'OneDrive', 'Escritorio', '*.json'),
        ])

    vistos = set()
    for patron in busqueda:
        for ruta in glob.glob(patron):
            ruta = os.path.normpath(ruta)
            if ruta in vistos:
                continue
            vistos.add(ruta)
            nombre = os.path.basename(ruta).lower()
            if nombre in ('package.json', 'firebase_config.json', 'tsconfig.json'):
                continue
            if _es_cuenta_servicio(ruta):
                return ruta
    return None


def _project_id_desde_credenciales(ruta: str) -> Optional[str]:
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f).get('project_id')
    except Exception:
        return None


def configurar_firebase_automatico() -> bool:
    """
    Crea firebase_config.json, copia credenciales si las encuentra
    y activa Firebase. Retorna True si quedó listo para usar la nube.
    """
    global _use_firebase
    _use_firebase = None

    cred = descubrir_credenciales()
    cfg = _leer_config()
    project_id = cfg.get('project_id') or os.environ.get('FIREBASE_PROJECT_ID')

    if cred and cred != DEFAULT_CREDENTIALS:
        try:
            import shutil
            shutil.copy2(cred, DEFAULT_CREDENTIALS)
            print(f'[almacenamiento] Credenciales copiadas desde: {cred}')
            cred = DEFAULT_CREDENTIALS
        except Exception as e:
            print(f'[almacenamiento] Usando credenciales en: {cred} ({e})')

    if cred:
        project_id = project_id or _project_id_desde_credenciales(cred)

    nueva_cfg = {
        'use_firebase': True,
        'project_id': project_id or 'kisvic-app',
        'credentials_path': 'firebase_credentials.json',
    }
    if cfg:
        nueva_cfg.update({k: v for k, v in cfg.items() if k not in nueva_cfg})
        nueva_cfg['use_firebase'] = True

    if not os.path.exists(DEFAULT_CREDENTIALS) and cred:
        nueva_cfg['credentials_path'] = os.path.relpath(cred, BASE_DIR)

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(nueva_cfg, f, ensure_ascii=False, indent=2)

    os.environ['KISVIC_USE_FIREBASE'] = '1'
    _use_firebase = None

    if os.path.exists(_ruta_credenciales()) and _es_cuenta_servicio(_ruta_credenciales()):
        print(f'[almacenamiento] Firebase configurado (proyecto: {project_id})')
        return True

    print('[almacenamiento] firebase_config.json creado; falta firebase_credentials.json')
    print('  Descarga la clave en Firebase Console > Cuentas de servicio > Generar clave')
    print(f'  y guárdala como: {DEFAULT_CREDENTIALS}')
    return False


def usar_firebase() -> bool:
    global _use_firebase
    if _use_firebase is not None:
        return _use_firebase

    cfg = _leer_config()
    env_flag = os.environ.get('KISVIC_USE_FIREBASE', '').strip().lower()
    if env_flag in ('1', 'true', 'yes', 'on'):
        quiere = True
    elif env_flag in ('0', 'false', 'no', 'off'):
        quiere = False
    else:
        quiere = bool(cfg.get('use_firebase', False))

    if quiere and os.path.exists(_ruta_credenciales()) and _es_cuenta_servicio(_ruta_credenciales()):
        _use_firebase = True
    elif quiere:
        print('[almacenamiento] Firebase activado en config pero sin credenciales válidas; solo JSON local.')
        _use_firebase = False
    else:
        _use_firebase = False

    return _use_firebase


def _ruta_absoluta(nombre_archivo: str) -> str:
    if os.path.isabs(nombre_archivo):
        return nombre_archivo
    return os.path.join(BASE_DIR, nombre_archivo)


def _doc_id(nombre_archivo: str) -> str:
    ruta = _ruta_absoluta(nombre_archivo)
    rel = os.path.relpath(ruta, BASE_DIR).replace('\\', '/')
    return rel.replace('/', '__').replace('.', '_')


def _timeout_nube() -> float:
    cfg = _leer_config()
    return float(cfg.get('timeout_nube_segundos', TIMEOUT_NUBE))


def _pausa_offline_seg() -> float:
    cfg = _leer_config()
    return float(cfg.get('pausa_offline_minutos', PAUSA_OFFLINE_MIN)) * 60


def _sync_segundo_plano() -> bool:
    cfg = _leer_config()
    return cfg.get('sync_nube_en_segundo_plano', True)


def _storage_mode() -> str:
    """
    Modo de persistencia:
    - firebase_primary: Firestore principal, JSON respaldo.
    - local_primary: JSON principal, Firestore respaldo.
    - local_only: solo JSON local.
    """
    cfg = _leer_config()
    modo = os.environ.get(
        'KISVIC_STORAGE_MODE',
        str(cfg.get('storage_mode', 'firebase_primary')),
    ).strip().lower()
    if modo not in ('firebase_primary', 'local_primary', 'local_only'):
        return 'firebase_primary'
    return modo


def _es_error_red(exc: BaseException) -> bool:
    msg = str(exc).lower()
    claves = (
        'unavailable', '503', 'timeout', 'timed out', 'getaddrinfo',
        'wsa error', '11001', 'name resolution', 'connection refused',
        'failed to connect', 'network', 'dns', 'grpc_status:14',
        'firestore.googleapis.com',
    )
    return any(k in msg for k in claves)


def _marcar_nube_offline(exc: Optional[BaseException] = None) -> None:
    global _nube_pausada_hasta, _aviso_offline_mostrado
    _nube_pausada_hasta = time.time() + _pausa_offline_seg()
    if not _aviso_offline_mostrado:
        _aviso_offline_mostrado = True
        mins = int(_pausa_offline_seg() / 60)
        detalle = f' ({exc})' if exc else ''
        print(
            f'[almacenamiento] Sin conexión a Firebase{detalle}. '
            f'Usando solo archivos locales durante ~{mins} min. '
            f'Los datos se guardan en disco; la nube se reintentará sola.'
        )


def _nube_disponible_ahora() -> bool:
    global _aviso_offline_mostrado
    if time.time() < _nube_pausada_hasta:
        return False
    if _nube_pausada_hasta > 0:
        _aviso_offline_mostrado = False
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo('firestore.googleapis.com', 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        _marcar_nube_offline()
        return False


def _ejecutar_con_timeout(fn: Callable[[], T], operacion: str) -> Optional[T]:
    if not _nube_disponible_ahora():
        return None
    timeout = _timeout_nube()
    fut = _executor.submit(fn)
    try:
        return fut.result(timeout=timeout)
    except FuturesTimeout:
        _marcar_nube_offline()
        print(f'[almacenamiento] Timeout ({timeout}s) en nube: {operacion}')
        return None
    except Exception as e:
        if _es_error_red(e):
            _marcar_nube_offline(e)
        else:
            print(f'[almacenamiento] Error en nube ({operacion}): {e}')
        return None


def _firestore_a_python(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _firestore_a_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_firestore_a_python(v) for v in value]
    module = type(value).__module__
    if module and module.startswith('google.cloud'):
        return str(value)
    return value


def _obtener_firestore():
    global _firestore_db, _firebase_initialized
    if _firestore_db is not None:
        return _firestore_db
    if not usar_firebase():
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print('[almacenamiento] pip install firebase-admin')
        return None

    cred_path = _ruta_credenciales()
    if not _es_cuenta_servicio(cred_path):
        return None

    if not _firebase_initialized:
        try:
            cred = credentials.Certificate(cred_path)
            if not firebase_admin._apps:
                cfg = _leer_config()
                options = {}
                project_id = (
                    _project_id_desde_credenciales(cred_path)
                    or cfg.get('project_id')
                    or os.environ.get('FIREBASE_PROJECT_ID')
                )
                if project_id:
                    options['projectId'] = project_id
                firebase_admin.initialize_app(cred, options or None)
            _firebase_initialized = True
            print('[almacenamiento] Conectado a Firebase Firestore')
        except Exception as e:
            print(f'[almacenamiento] Error inicializando Firebase: {e}')
            return None

    try:
        _firestore_db = firestore.client()
        return _firestore_db
    except Exception as e:
        print(f'[almacenamiento] Error Firestore: {e}')
        return None


def _cargar_firestore_sync(nombre_archivo: str) -> Optional[Any]:
    db = _obtener_firestore()
    if db is None:
        return None
    doc = db.collection(FIREBASE_COLLECTION).document(_doc_id(nombre_archivo)).get()
    if not doc.exists:
        return None
    payload = doc.to_dict() or {}
    if 'data' in payload:
        return _firestore_a_python(payload['data'])
    return _firestore_a_python(payload)


def _cargar_firestore(nombre_archivo: str) -> Optional[Any]:
    return _ejecutar_con_timeout(
        lambda: _cargar_firestore_sync(nombre_archivo),
        f'leer {nombre_archivo}',
    )


def _guardar_firestore_sync(nombre_archivo: str, datos: Any) -> bool:
    db = _obtener_firestore()
    if db is None:
        return False
    db.collection(FIREBASE_COLLECTION).document(_doc_id(nombre_archivo)).set({
        'data': datos,
        'archivo': nombre_archivo.replace('\\', '/'),
        'updated_at': datetime.utcnow().isoformat() + 'Z',
    })
    return True


def _guardar_firestore(nombre_archivo: str, datos: Any, en_segundo_plano: bool = False) -> bool:
    if en_segundo_plano:
        with _sync_lock:
            _pending_sync[nombre_archivo] = datos

        def _tarea():
            try:
                _guardar_firestore(nombre_archivo, datos, en_segundo_plano=False)
            finally:
                with _sync_lock:
                    _pending_sync.pop(nombre_archivo, None)

        threading.Thread(target=_tarea, daemon=True, name='firebase-save').start()
        return True

    resultado = _ejecutar_con_timeout(
        lambda: _guardar_firestore_sync(nombre_archivo, datos),
        f'guardar {nombre_archivo}',
    )
    return resultado is True


def existe_archivo(nombre_archivo: str) -> bool:
    return os.path.exists(_ruta_absoluta(nombre_archivo))


def _cargar_json_local(nombre_archivo: str, crear_vacio: bool = True) -> Any:
    ruta = _ruta_absoluta(nombre_archivo)
    try:
        directorio = os.path.dirname(ruta)
        if directorio:
            os.makedirs(directorio, exist_ok=True)

        if not os.path.exists(ruta):
            if not crear_vacio:
                return None
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            return {}

        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
            if not contenido.strip():
                return {}
            return json.loads(contenido)
    except json.JSONDecodeError as e:
        print(f'Error JSON en {nombre_archivo}: {e}')
        return {}
    except Exception as e:
        print(f'Error leyendo {nombre_archivo}: {e}')
        return {} if crear_vacio else None


def _guardar_json_local(nombre_archivo: str, datos: Any) -> bool:
    ruta = _ruta_absoluta(nombre_archivo)
    temp_file = ruta + '.tmp'
    try:
        directorio = os.path.dirname(ruta)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        json.dumps(datos)
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
        if os.path.exists(ruta):
            os.remove(ruta)
        os.rename(temp_file, ruta)
        return True
    except Exception as e:
        print(f'Error guardando {nombre_archivo}: {e}')
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        return False


def _cargar_sqlite(nombre_archivo: str) -> Optional[Any]:
    """Carga datos directamente desde la base de datos SQLite si el esquema coincide."""
    try:
        from database import (
            get_db_session, ClienteModel, ProductoModel, FacturaModel,
            CuentaPorCobrarModel, BitacoraModel, EmpresaModel
        )
        session = get_db_session()
        nombre_clean = os.path.basename(nombre_archivo)

        if nombre_clean == "clientes.json":
            rows = session.query(ClienteModel).all()
            if rows:
                res = {r.id: r.to_dict() for r in rows}
                session.close()
                return res

        elif nombre_clean == "inventario.json":
            rows = session.query(ProductoModel).all()
            if rows:
                res = {r.id: r.to_dict() for r in rows}
                session.close()
                return res

        elif nombre_clean == "facturas.json":
            rows = session.query(FacturaModel).all()
            if rows:
                res = {r.id: r.to_dict() for r in rows}
                session.close()
                return res

        elif nombre_clean.startswith("factura_") and nombre_clean.endswith(".json"):
            f_id = nombre_clean[len("factura_"):-len(".json")]
            row = session.query(FacturaModel).filter(
                (FacturaModel.id == f_id) | (FacturaModel.numero == f_id)
            ).first()
            if row:
                res = row.to_dict()
                session.close()
                return res

        elif nombre_clean == "cuentas_por_cobrar.json":
            rows = session.query(CuentaPorCobrarModel).all()
            if rows:
                res = {r.numero_factura: r.to_dict() for r in rows}
                session.close()
                return res

        elif nombre_clean == "empresa.json":
            row = session.query(EmpresaModel).filter_by(id=1).first()
            if row:
                res = row.to_dict()
                session.close()
                return res

        session.close()
    except Exception:
        pass
    return None


def _guardar_sqlite(nombre_archivo: str, datos: Any) -> bool:
    """Guarda o actualiza registros en la base de datos SQLite."""
    try:
        from database import (
            get_db_session, ClienteModel, ProductoModel, FacturaModel,
            CuentaPorCobrarModel, BitacoraModel, EmpresaModel
        )
        session = get_db_session()
        nombre_clean = os.path.basename(nombre_archivo)

        if nombre_clean == "clientes.json" and isinstance(datos, dict):
            for c_id, c in datos.items():
                if not isinstance(c, dict): continue
                cid = str(c.get("id") or c_id).strip()
                if not cid: continue
                obj = session.query(ClienteModel).filter_by(id=cid).first()
                if not obj:
                    obj = ClienteModel(id=cid)
                    session.add(obj)
                obj.nombre = str(c.get("nombre", ""))
                obj.rif = str(c.get("rif", ""))
                obj.telefono = str(c.get("telefono", ""))
                obj.direccion = str(c.get("direccion", ""))
                obj.email = str(c.get("email", ""))
                obj.estado = str(c.get("estado", "activo"))
                obj.fecha_registro = str(c.get("fecha_registro", ""))
            session.commit()
            session.close()
            return True

        elif nombre_clean == "inventario.json" and isinstance(datos, dict):
            for p_id, p in datos.items():
                if not isinstance(p, dict): continue
                pid = str(p.get("id") or p_id).strip()
                if not pid: continue
                obj = session.query(ProductoModel).filter_by(id=pid).first()
                if not obj:
                    obj = ProductoModel(id=pid)
                    session.add(obj)
                obj.codigo = str(p.get("codigo", pid))
                obj.nombre = str(p.get("nombre", ""))
                obj.descripcion = str(p.get("descripcion", ""))
                obj.precio_usd = float(p.get("precio_usd", 0.0) or 0.0)
                obj.precio_bs = float(p.get("precio_bs", 0.0) or 0.0)
                obj.stock = int(p.get("stock", 0) or 0)
                obj.stock_minimo = int(p.get("stock_minimo", 5) or 5)
                obj.categoria = str(p.get("categoria", "General"))
                obj.unidad_medida = str(p.get("unidad_medida", "UNID"))
                obj.historial_ajustes_json = json.dumps(p.get("historial_ajustes", []), ensure_ascii=False)
            session.commit()
            session.close()
            return True

        elif nombre_clean == "facturas.json" and isinstance(datos, dict):
            for f_id, f in datos.items():
                if not isinstance(f, dict): continue
                fid = str(f.get("id") or f_id).strip()
                if not fid: continue
                obj = session.query(FacturaModel).filter_by(id=fid).first()
                if not obj:
                    obj = FacturaModel(id=fid)
                    session.add(obj)
                obj.numero = str(f.get("numero", fid))
                obj.numero_secuencial = str(f.get("numero_secuencial", ""))
                obj.cliente_id = str(f.get("cliente_id", ""))
                obj.fecha = str(f.get("fecha", ""))
                obj.hora = str(f.get("hora", ""))
                obj.condicion_pago = str(f.get("condicion_pago", "contado"))
                obj.dias_credito = str(f.get("dias_credito", "30"))
                obj.tasa_bcv = float(f.get("tasa_bcv", 36.0) or 36.0)
                obj.subtotal_usd = float(f.get("subtotal_usd", 0.0) or 0.0)
                obj.descuento_total = float(f.get("descuento_total", 0.0) or 0.0)
                obj.iva_porcentaje = float(f.get("iva_porcentaje", 0.0) or 0.0)
                obj.iva_total = float(f.get("iva_total", 0.0) or 0.0)
                obj.total_usd = float(f.get("total_usd", 0.0) or 0.0)
                obj.total_bs = float(f.get("total_bs", 0.0) or 0.0)
                obj.total_abonado = float(f.get("total_abonado", 0.0) or 0.0)
                obj.saldo_pendiente = float(f.get("saldo_pendiente", 0.0) or 0.0)
                obj.estado = str(f.get("estado", "pendiente"))
                obj.firma_fiscal = str(f.get("firma_fiscal", ""))
                obj.creado_por = str(f.get("creado_por", "SISTEMA"))
                obj.fecha_creacion = str(f.get("fecha_creacion", ""))
                obj.productos_json = json.dumps(f.get("productos", []), ensure_ascii=False)
                obj.cantidades_json = json.dumps(f.get("cantidades", []), ensure_ascii=False)
                obj.precios_json = json.dumps(f.get("precios", []), ensure_ascii=False)
                obj.pagos_json = json.dumps(f.get("pagos", []), ensure_ascii=False)
            session.commit()
            session.close()
            return True

        elif nombre_clean.startswith("factura_") and nombre_clean.endswith(".json") and isinstance(datos, dict):
            f = datos
            fid = str(f.get("id") or nombre_clean[len("factura_"):-len(".json")]).strip()
            if fid:
                obj = session.query(FacturaModel).filter_by(id=fid).first()
                if not obj:
                    obj = FacturaModel(id=fid)
                    session.add(obj)
                obj.numero = str(f.get("numero", fid))
                obj.numero_secuencial = str(f.get("numero_secuencial", ""))
                obj.cliente_id = str(f.get("cliente_id", ""))
                obj.fecha = str(f.get("fecha", ""))
                obj.hora = str(f.get("hora", ""))
                obj.condicion_pago = str(f.get("condicion_pago", "contado"))
                obj.dias_credito = str(f.get("dias_credito", "30"))
                obj.tasa_bcv = float(f.get("tasa_bcv", 36.0) or 36.0)
                obj.subtotal_usd = float(f.get("subtotal_usd", 0.0) or 0.0)
                obj.descuento_total = float(f.get("descuento_total", 0.0) or 0.0)
                obj.iva_porcentaje = float(f.get("iva_porcentaje", 0.0) or 0.0)
                obj.iva_total = float(f.get("iva_total", 0.0) or 0.0)
                obj.total_usd = float(f.get("total_usd", 0.0) or 0.0)
                obj.total_bs = float(f.get("total_bs", 0.0) or 0.0)
                obj.total_abonado = float(f.get("total_abonado", 0.0) or 0.0)
                obj.saldo_pendiente = float(f.get("saldo_pendiente", 0.0) or 0.0)
                obj.estado = str(f.get("estado", "pendiente"))
                obj.firma_fiscal = str(f.get("firma_fiscal", ""))
                obj.creado_por = str(f.get("creado_por", "SISTEMA"))
                obj.fecha_creacion = str(f.get("fecha_creacion", ""))
                obj.productos_json = json.dumps(f.get("productos", []), ensure_ascii=False)
                obj.cantidades_json = json.dumps(f.get("cantidades", []), ensure_ascii=False)
                obj.precios_json = json.dumps(f.get("precios", []), ensure_ascii=False)
                obj.pagos_json = json.dumps(f.get("pagos", []), ensure_ascii=False)
                session.commit()
                session.close()
                return True

        elif nombre_clean == "cuentas_por_cobrar.json" and isinstance(datos, dict):
            for c_key, c in datos.items():
                if not isinstance(c, dict): continue
                num_fac = str(c.get("numero_factura") or c_key).strip()
                if not num_fac: continue
                obj = session.query(CuentaPorCobrarModel).filter_by(numero_factura=num_fac).first()
                if not obj:
                    obj = CuentaPorCobrarModel(numero_factura=num_fac)
                    session.add(obj)
                obj.cliente_id = str(c.get("cliente_id", ""))
                obj.monto_total = float(c.get("monto_total", 0.0) or 0.0)
                obj.monto_pendiente = float(c.get("monto_pendiente", 0.0) or 0.0)
                obj.fecha_emision = str(c.get("fecha_emision", ""))
                obj.estado = str(c.get("estado", "pendiente"))
            session.commit()
            session.close()
            return True

        elif nombre_clean == "empresa.json" and isinstance(datos, dict):
            emp = session.query(EmpresaModel).filter_by(id=1).first()
            if not emp:
                emp = EmpresaModel(id=1)
                session.add(emp)
            emp.nombre = str(datos.get("nombre", ""))
            emp.rif = str(datos.get("rif", ""))
            emp.telefono = str(datos.get("telefono", ""))
            emp.direccion = str(datos.get("direccion", ""))
            session.commit()
            session.close()
            return True

        session.close()
    except Exception as e:
        print(f"Error guardando SQLite {nombre_archivo}: {e}")
    return False


def cargar_datos(nombre_archivo: str, crear_vacio: bool = True) -> Any:
    """
    Carga datos priorizando la base de datos SQLite kisvic.db.
    Mantiene fallback a JSON local y Firestore.
    """
    # 1. Intentar cargar desde SQLite (Motor Primario)
    datos_sqlite = _cargar_sqlite(nombre_archivo)
    if datos_sqlite not in (None, {}):
        return datos_sqlite

    # 2. Fallback a JSON local si SQLite estuviera vacío
    datos_local = _cargar_json_local(nombre_archivo, crear_vacio=crear_vacio)
    return datos_local if datos_local is not None else ({} if crear_vacio else None)


def guardar_datos(nombre_archivo: str, datos: Any) -> bool:
    """
    Guarda datos simultáneamente en la base de datos SQLite kisvic.db
    y en el archivo JSON local de respaldo.
    """
    _guardar_sqlite(nombre_archivo, datos)
    ok_local = _guardar_json_local(nombre_archivo, datos)
    return ok_local


def sincronizar_pendientes_nube() -> int:
    """Reintenta subir a Firestore los archivos que fallaron por red."""
    if not usar_firebase() or not _nube_disponible_ahora():
        return 0
    ok = 0
    for archivo in listar_archivos_migrables():
        datos = _cargar_json_local(archivo, crear_vacio=False)
        if datos is not None and _guardar_firestore(archivo, datos, en_segundo_plano=False):
            ok += 1
    return ok


def listar_archivos_migrables() -> List[str]:
    encontrados: List[str] = []
    for archivo in ARCHIVOS_PRINCIPALES:
        if os.path.exists(_ruta_absoluta(archivo)):
            encontrados.append(archivo)
    for carpeta in CARPETAS_JSON:
        dir_path = _ruta_absoluta(carpeta)
        if not os.path.isdir(dir_path):
            continue
        for nombre in os.listdir(dir_path):
            if nombre.endswith('.json'):
                encontrados.append(f'{carpeta}/{nombre}'.replace('\\', '/'))
    return sorted(set(encontrados))


def migrar_todo_a_firebase() -> Dict[str, bool]:
    if not usar_firebase():
        return {}
    resultados: Dict[str, bool] = {}
    total = len(listar_archivos_migrables())
    for i, archivo in enumerate(listar_archivos_migrables(), 1):
        datos = _cargar_json_local(archivo, crear_vacio=False)
        if datos is None:
            continue
        ok = _guardar_firestore(archivo, datos)
        resultados[archivo] = ok
        if i % 20 == 0 or i == total:
            print(f'  Migrados {i}/{total}...')
    return resultados


def configurar_al_inicio() -> None:
    """Llamar al arrancar la app: configura Firebase y migra si hace falta."""
    if not os.path.exists(CONFIG_FILE):
        configurar_firebase_automatico()

    if usar_firebase() and _nube_disponible_ahora():
        marca = os.path.join(BASE_DIR, '.firebase_migrado')
        if not os.path.exists(marca):
            print('[almacenamiento] Primera ejecución con Firebase: migrando datos locales...')
            res = migrar_todo_a_firebase()
            ok = sum(1 for v in res.values() if v)
            print(f'[almacenamiento] Migración: {ok}/{len(res)} archivos en la nube')
            try:
                with open(marca, 'w', encoding='utf-8') as f:
                    f.write(datetime.now().isoformat())
            except OSError:
                pass
