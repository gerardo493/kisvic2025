# -*- coding: utf-8 -*-
import json
import os
import urllib3
import urllib.parse
import requests
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file, session, abort, send_from_directory
from werkzeug.utils import secure_filename
# SOLUCIÓN: Importar CSRFProtect de manera compatible
try:
    from flask_wtf.csrf import CSRFProtect
except ImportError:
    # Fallback para versiones más nuevas
    from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from config_maps import get_maps_config
from seguridad_fiscal import seguridad_fiscal
from numeracion_fiscal import control_numeracion
from comunicacion_seniat import comunicador_seniat
from exportacion_seniat import exportador_seniat
try:
    import pdfkit
except ImportError:
    pdfkit = None
from functools import wraps
import re
import uuid
import io
import zipfile
from io import StringIO
from uuid import uuid4
from flask_sqlalchemy import SQLAlchemy
import base64
import copy
import re

# --- Inicializar la Aplicación Flask ---
app = Flask(__name__)

# --- Configuración de la Aplicación ---
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# --- Inicializar CSRF ---
csrf = CSRFProtect(app)

# --- Constantes ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
IMAGENES_PRODUCTOS_FOLDER = os.path.join(BASE_DIR, 'static', 'imagenes_productos')
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_FACTURAS = 'facturas_json/facturas.json'
ARCHIVO_COTIZACIONES = 'cotizaciones_json/cotizaciones.json'
ARCHIVO_NOTAS_ENTREGA = 'notas_entrega_json/notas_entrega.json'
ARCHIVO_CUENTAS = 'cuentas_por_cobrar.json'
ULTIMA_TASA_BCV_FILE = 'ultima_tasa_bcv.json'
ALLOWED_EXTENSIONS = {'csv', 'jpg', 'jpeg', 'png', 'gif'}
BITACORA_FILE = 'bitacora.log'

# --- Ruta de prueba ---
@app.route('/')
def index():
    return "¡Sistema funcionando correctamente! 🚀"

@app.route('/test')
def test():
    return "Test de funcionamiento OK ✅"

# --- Iniciar la aplicación ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

