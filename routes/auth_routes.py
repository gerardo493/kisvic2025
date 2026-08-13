# -*- coding: utf-8 -*-
"""
Blueprint para rutas de autenticación (/login, /logout).
Cumple con el principio de responsabilidad única (SRP).
"""

from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.auth_decorators import verify_password, login_required
from services.bitacora_service import registrar_bitacora

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Maneja el formulario y la verificación de inicio de sesión."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Por favor ingrese usuario y contraseña", "warning")
            return render_template("login.html")

        if verify_password(username, password):
            session["usuario"] = username
            registrar_bitacora(username, "Inicio de sesión", "Inicio de sesión exitoso")
            flash("Bienvenido al sistema", "success")
            return redirect(url_for("index"))
        else:
            registrar_bitacora(username, "Intento fallido", "Intento fallido de inicio de sesión")
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Maneja el cierre de sesión del usuario."""
    usuario = session.get("usuario", "desconocido")
    registrar_bitacora(usuario, "Cierre de sesión", "Sesión finalizada")
    session.pop("usuario", None)
    flash("Sesión cerrada exitosamente", "info")
    return redirect(url_for("auth.login"))
