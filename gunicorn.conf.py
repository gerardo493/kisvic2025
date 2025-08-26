#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración de Gunicorn optimizada para Render.
"""

import os
import multiprocessing

# Configuración del servidor
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
threads = 2
worker_class = "sync"

# Configuración de timeout
timeout = 180
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Configuración de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Configuración de workers
worker_connections = 1000
worker_tmp_dir = "/dev/shm"

# Configuración de seguridad
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Configuración de performance
preload_app = True
forwarded_allow_ips = "*"

# Configuración de health check
def when_ready(server):
    server.log.info("🚀 Servidor Gunicorn listo")

def on_starting(server):
    server.log.info("🔄 Iniciando servidor Gunicorn")

def on_reload(server):
    server.log.info("🔄 Recargando servidor Gunicorn")

def worker_int(worker):
    worker.log.info("⚠️ Worker interrumpido")

def pre_fork(server, worker):
    server.log.info(f"👷 Creando worker {worker.pid}")

def post_fork(server, worker):
    server.log.info(f"✅ Worker {worker.pid} creado")

def post_worker_init(worker):
    worker.log.info(f"🚀 Worker {worker.pid} inicializado")

def worker_abort(worker):
    worker.log.info(f"❌ Worker {worker.pid} abortado")
