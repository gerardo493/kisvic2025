# -*- coding: utf-8 -*-
"""
Kisvic - Lanzador automatizado (un solo comando).

Uso:
  python kisvic.py              # Flask + tunel + verificaciones
  python kisvic.py run          # Igual que arriba
  python kisvic.py run --solo-local   # Solo Flask (sin tunel)
  python kisvic.py setup        # Crear .env.server y comprobar requisitos
  python kisvic.py backup       # Backup diario
  python kisvic.py health       # Probar /api/health (Flask debe estar corriendo)
  python kisvic.py schedule-backup   # Tarea Windows diaria 02:00
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


try:
    import requests
except ImportError:
    print("[X] Instala dependencias: pip install -r requirements.txt")
    sys.exit(1)

BASE = Path(__file__).resolve().parent
PUERTO = int(os.environ.get("KISVIC_PORT", "5000"))
URL_LOCAL = f"http://127.0.0.1:{PUERTO}"
ARCHIVO_URL_TUNEL = BASE / "ultima_url_tunel.txt"
CLOUDFLARED = BASE / "cloudflared.exe"
ENV_SERVER = BASE / ".env.server"
ENV_SERVER_EXAMPLE = BASE / ".env.server.example"
ENV_PRODUCTION = BASE / ".env.production"
ENV_PRODUCTION_EXAMPLE = BASE / ".env.production.example"


def _banner(titulo: str = "KISVIC - Automatizacion") -> None:
    print("=" * 62)
    print(f"  {titulo}")
    print("=" * 62)
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 62)


def cargar_env_archivo(ruta: Path, sobrescribir: bool = True) -> int:
    """Carga KEY=VALUE en os.environ. Retorna cantidad de claves cargadas."""
    if not ruta.is_file():
        return 0
    count = 0
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        if clave:
            if sobrescribir or clave not in os.environ:
                os.environ[clave] = valor
            count += 1
    return count


def aplicar_entorno_servidor() -> None:
    """Carga .env.server y valores por defecto de Kisvic."""
    n = cargar_env_archivo(ENV_SERVER)
    if n:
        print(f"[OK] Variables cargadas desde .env.server ({n} claves)")

    os.environ.setdefault("KISVIC_USE_FIREBASE", "1")
    os.environ.setdefault("KISVIC_ENV", "development")
    os.environ.setdefault("KISVIC_CSRF_MODE", "phase1")
    os.environ.setdefault("KISVIC_STORAGE_MODE", "firebase_primary")
    os.environ.setdefault("KISVIC_LOG_LEVEL", "INFO")
    os.environ.setdefault("KISVIC_COOKIE_SECURE", "0")


def cmd_setup(_args: argparse.Namespace) -> int:
    _banner("SETUP")
    if not ENV_SERVER.is_file() and ENV_SERVER_EXAMPLE.is_file():
        ENV_SERVER.write_text(ENV_SERVER_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print("[OK] Creado .env.server desde ejemplo")
        print("     Edita KISVIC_SECRET_KEY antes de usar en produccion.")
    elif ENV_SERVER.is_file():
        print("[OK] .env.server ya existe")
    else:
        print("[X] Falta .env.server.example")
        return 1

    if not ENV_PRODUCTION.is_file() and ENV_PRODUCTION_EXAMPLE.is_file():
        ENV_PRODUCTION.write_text(ENV_PRODUCTION_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        print("[OK] Creado .env.production desde ejemplo")

    aplicar_entorno_servidor()

    cred = BASE / "firebase_credentials.json"
    if cred.is_file():
        print("[OK] firebase_credentials.json encontrado")
    else:
        print("[!] Falta firebase_credentials.json")
        print("    Consola Firebase > Cuentas de servicio > Generar clave privada")

    if CLOUDFLARED.is_file():
        print("[OK] cloudflared.exe encontrado")
    else:
        print("[!] Falta cloudflared.exe (solo necesario para tunel)")

    print("\nSiguiente paso: python kisvic.py run")
    return 0


def cmd_backup(_args: argparse.Namespace) -> int:
    _banner("BACKUP DIARIO")
    aplicar_entorno_servidor()
    import backup_diario

    return backup_diario.main()


def flask_activo() -> bool:
    try:
        r = requests.get(f"{URL_LOCAL}/test", timeout=4)
        return r.status_code == 200
    except Exception:
        return False


def asegurar_firebase() -> bool:
    cred = BASE / "firebase_credentials.json"
    if cred.is_file():
        return True
    print("\n[!] Configurando Firebase...")
    r = subprocess.run([sys.executable, str(BASE / "scripts" / "firebase" / "configurar_firebase.py")], cwd=BASE)

    if r.returncode != 0 or not cred.is_file():
        print("[X] Coloca firebase_credentials.json y vuelve a ejecutar.")
        return False
    print("[OK] Firebase configurado")
    return True


def iniciar_flask() -> subprocess.Popen | None:
    if flask_activo():
        print(f"\n[OK] Flask ya activo: {URL_LOCAL}")
        return None

    print("\n[1/4] Iniciando Flask (ventana nueva)...")
    env = os.environ.copy()
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    try:
        proc = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=str(BASE),
            env=env,
            creationflags=flags,
        )
    except Exception as e:
        print(f"[X] No se pudo iniciar Flask: {e}")
        return None

    for i in range(90):
        if flask_activo():
            print(f"[OK] Flask listo: {URL_LOCAL}")
            return proc
        if proc.poll() is not None:
            print("[X] Flask se cerro. Revisa la otra ventana.")
            return None
        time.sleep(1)
        if i % 15 == 14:
            print(f"      ... esperando ({i + 1}s)")
    print("[X] Flask no respondio a tiempo.")
    return proc


def iniciar_tunel() -> tuple[subprocess.Popen | None, str | None]:
    if not CLOUDFLARED.is_file():
        print("[X] No hay cloudflared.exe")
        return None, None

    print("\n[2/4] Iniciando tunel Cloudflare...")
    try:
        proc = subprocess.Popen(
            [str(CLOUDFLARED), "tunnel", "--url", f"http://localhost:{PUERTO}"],
            cwd=str(BASE),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        print(f"[X] Error cloudflared: {e}")
        return None, None

    patron = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    for _ in range(120):
        line = proc.stdout.readline() if proc.stdout else ""
        if line:
            line = line.strip()
            if "trycloudflare.com" in line:
                print(f"      {line}")
            m = patron.search(line)
            if m:
                return proc, m.group(0)
        if proc.poll() is not None:
            break
        time.sleep(0.2)
    return proc, None


def actualizar_url_dashboard_publica(url_publica: str) -> None:
    """Guarda URL del tunel y sugiere VITE_DASHBOARD_API_URL."""
    ARCHIVO_URL_TUNEL.write_text(
        f"{url_publica}\nGenerada: {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )
    api_url = f"{url_publica.rstrip('/')}/api/dashboard/resumen"
    print(f"\n  Dashboard API: {api_url}")
    print("  (Para Hosting React, en .env.production usa:)")
    print(f"  VITE_DASHBOARD_API_URL={api_url}")


def verificar_salud(url_base: str) -> None:
    print("\n[3/4] Verificando APIs...")
    try:
        h = requests.get(f"{url_base}/api/health", timeout=8)
        print(f"      /api/health -> {h.status_code}")
    except Exception as e:
        print(f"      /api/health -> error: {e}")
    try:
        d = requests.get(f"{url_base}/api/dashboard/resumen", timeout=15)
        if d.status_code == 200:
            data = d.json()
            ok = data.get("success") and data.get("data", {}).get("stats")
            print(f"      /api/dashboard/resumen -> OK (stats: {bool(ok)})")
        else:
            print(f"      /api/dashboard/resumen -> HTTP {d.status_code}")
    except Exception as e:
        print(f"      /api/dashboard/resumen -> error: {e}")


def cmd_schedule_backup(args: argparse.Namespace) -> int:
    if os.name != "nt":
        print("[X] schedule-backup solo esta disponible en Windows.")
        return 1
    _banner("PROGRAMAR BACKUP DIARIO")
    hora = getattr(args, "hora", None) or "02:00"
    nombre = "KisvicBackupDiario"
    script = str((BASE / "kisvic.py").resolve())
    python_exe = str(Path(sys.executable).resolve())
    tr = f'"{python_exe}" "{script}" backup'
    cmd = [
        "schtasks",
        "/Create",
        "/TN",
        nombre,
        "/TR",
        tr,
        "/SC",
        "DAILY",
        "/ST",
        hora,
        "/F",
    ]
    print(f"Tarea: {nombre}")
    print(f"Hora:  {hora}")
    print(f"CMD:   {tr}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout or "[X] schtasks fallo")
        return 1
    print("[OK] Tarea programada. Verifica en Programador de tareas de Windows.")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    aplicar_entorno_servidor()
    base = args.url or URL_LOCAL
    verificar_salud(base.rstrip("/"))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    _banner("INICIO AUTOMATICO")
    aplicar_entorno_servidor()

    if args.backup:
        print("\n[0/4] Backup diario...")
        subprocess.run([sys.executable, str(BASE / "backup_diario.py")], cwd=str(BASE))

    if not asegurar_firebase():
        return 1

    if os.environ.get("KISVIC_VERIFICAR_FIREBASE", "1") == "1":
        print("\n[INFO] Verificando Firestore...")
        subprocess.run([sys.executable, str(BASE / "scripts" / "firebase" / "verificar_firebase.py")], cwd=str(BASE))


    flask_proc = iniciar_flask()
    if flask_proc is None and not flask_activo():
        return 1

    url_publica = URL_LOCAL
    tunel_proc = None

    if not args.solo_local:
        tunel_proc, url_tunel = iniciar_tunel()
        if url_tunel:
            url_publica = url_tunel
            actualizar_url_dashboard_publica(url_tunel)
        elif not args.solo_local:
            print("[!] Tunel no disponible; sigues solo en local.")

    verificar_salud(url_publica)

    print("\n" + "=" * 62)
    print("  LISTO")
    print("=" * 62)
    print(f"  LOCAL:    {URL_LOCAL}")
    if url_publica != URL_LOCAL:
        print(f"  INTERNET: {url_publica}")
        print(f"  URL guardada: {ARCHIVO_URL_TUNEL}")
    print(f"  Logs:       {BASE / 'logs' / 'app_events.log'}")
    print("  Ctrl+C cierra el tunel (Flask queda en su ventana)")
    print("=" * 62)

    if url_publica != URL_LOCAL:
        try:
            webbrowser.open(url_publica)
        except Exception:
            pass

    if tunel_proc:
        print("\n[4/4] Tunel activo. Ctrl+C para cerrar.\n")
        try:
            while tunel_proc.poll() is None:
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nCerrando tunel...")
            tunel_proc.terminate()
    else:
        input("\nPresiona Enter para salir...")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Kisvic - lanzador automatizado")
    sub = parser.add_subparsers(dest="comando")

    p_run = sub.add_parser("run", help="Iniciar Flask (+ tunel por defecto)")
    p_run.add_argument("--solo-local", action="store_true", help="Sin tunel Cloudflare")
    p_run.add_argument("--backup", action="store_true", help="Backup antes de iniciar")
    p_run.set_defaults(func=cmd_run)

    p_setup = sub.add_parser("setup", help="Crear .env y comprobar requisitos")
    p_setup.set_defaults(func=cmd_setup)

    p_backup = sub.add_parser("backup", help="Ejecutar backup diario")
    p_backup.set_defaults(func=cmd_backup)

    p_health = sub.add_parser("health", help="Probar /api/health y dashboard")
    p_health.add_argument("--url", default="", help="Base URL (default local)")
    p_health.set_defaults(func=cmd_health)

    p_sched = sub.add_parser("schedule-backup", help="Crear tarea Windows (backup 02:00)")
    p_sched.add_argument("--hora", default="02:00", help="Hora HH:MM (default 02:00)")
    p_sched.set_defaults(func=cmd_schedule_backup)

    args = parser.parse_args()
    if args.comando is None:
        aplicar_entorno_servidor()
        ns = argparse.Namespace(
            solo_local=False,
            backup=os.environ.get("KISVIC_AUTO_BACKUP", "0") == "1",
        )
        return cmd_run(ns)

    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        raise SystemExit(0)
