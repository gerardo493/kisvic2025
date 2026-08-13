# -*- coding: utf-8 -*-
"""Backup diario de archivos clave con retención."""

from __future__ import annotations

import os
import zipfile
from datetime import datetime
from pathlib import Path

from almacenamiento import ARCHIVOS_PRINCIPALES, CARPETAS_JSON

import shutil

BASE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = BASE_DIR / "backups" / "diarios"
SECONDARY_BACKUP_DIR = os.environ.get("KISVIC_SECONDARY_BACKUP_DIR", str(BASE_DIR / "backups" / "respaldo_secundario"))
RETENCION_DIAS = int(os.environ.get("KISVIC_BACKUP_RETENTION_DAYS", "14"))


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _colectar_rutas() -> list[Path]:
    rutas: list[Path] = []

    for rel in ARCHIVOS_PRINCIPALES:
        p = (BASE_DIR / rel).resolve()
        if p.exists() and p.is_file():
            rutas.append(p)

    for carpeta in CARPETAS_JSON:
        d = (BASE_DIR / carpeta).resolve()
        if d.exists() and d.is_dir():
            for p in d.glob("*.json"):
                rutas.append(p.resolve())

    vistos = set()
    unicas: list[Path] = []
    for r in rutas:
        if r not in vistos:
            vistos.add(r)
            unicas.append(r)
    return unicas


def _crear_zip(rutas: list[Path]) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destino = BACKUP_DIR / f"backup_{_timestamp()}.zip"

    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for ruta in rutas:
            arcname = ruta.relative_to(BASE_DIR)
            zf.write(ruta, arcname.as_posix())
    return destino


def _aplicar_retencion(target_dir: Path) -> int:
    if not target_dir.exists():
        return 0
    eliminados = 0
    ahora = datetime.now().timestamp()
    umbral = RETENCION_DIAS * 86400

    for archivo in target_dir.glob("backup_*.zip"):
        edad = ahora - archivo.stat().st_mtime
        if edad > umbral:
            try:
                archivo.unlink()
                eliminados += 1
            except OSError:
                pass
    return eliminados


def main() -> int:
    rutas = _colectar_rutas()
    if not rutas:
        print("[backup] No hay archivos para respaldar.")
        return 1

    zip_path = _crear_zip(rutas)
    eliminados_primario = _aplicar_retencion(BACKUP_DIR)

    sec_path_str = None
    eliminados_secundario = 0
    if SECONDARY_BACKUP_DIR:
        try:
            sec_dir = Path(SECONDARY_BACKUP_DIR).resolve()
            sec_dir.mkdir(parents=True, exist_ok=True)
            sec_dest = sec_dir / zip_path.name
            shutil.copy2(zip_path, sec_dest)
            sec_path_str = str(sec_dest)
            eliminados_secundario = _aplicar_retencion(sec_dir)
        except Exception as e:
            print(f"[backup] Advertencia en copia secundaria: {e}")

    print("[backup] OK")
    print(f"[backup] Archivo primario: {zip_path}")
    if sec_path_str:
        print(f"[backup] Archivo secundario (USB/Disco): {sec_path_str}")
    print(f"[backup] Archivos incluidos: {len(rutas)}")
    print(f"[backup] Retención (días): {RETENCION_DIAS}")
    print(f"[backup] Backups antiguos eliminados: {eliminados_primario + eliminados_secundario}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

