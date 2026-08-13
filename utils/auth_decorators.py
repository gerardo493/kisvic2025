# -*- coding: utf-8 -*-
"""
Módulo de utilidades para decoradores de rutas y verificación de credenciales.
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash
from almacenamiento import cargar_datos

USUARIOS_FILE = "usuarios.json"


def login_required(f):
    """Decorador para restringir el acceso solo a usuarios con sesión activa."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorador para restringir el acceso solo a administradores."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        if session.get("usuario") != "admin":
            flash("No tiene permisos de administrador para acceder a esta página", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


def validar_url_factura(f):
    """Decorador para validar URLs de facturas y evitar malformaciones."""
    @wraps(f)
    def decorated_function(id, *args, **kwargs):
        if "//" in request.path or not id or str(id).strip() == "":
            flash("URL de factura inválida", "danger")
            return redirect(url_for("mostrar_facturas"))
        return f(id, *args, **kwargs)
    return decorated_function


def verify_password(username: str, password: str) -> bool:
    """Verifica el hash de la contraseña de un usuario."""
    try:
        usuarios = cargar_datos(USUARIOS_FILE, crear_vacio=False) or {}
        if username in usuarios and "password" in usuarios[username]:
            return check_password_hash(usuarios[username]["password"], password)
    except Exception as e:
        print(f"Error verificando contraseña de {username}: {e}")
    return False
