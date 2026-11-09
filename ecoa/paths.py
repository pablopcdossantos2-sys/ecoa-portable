"""Caminhos do aplicativo.

Modo portátil: tudo (configuração, áudios e log) fica na pasta ``dados`` ao lado do
executável (ou do ``main.py``, em desenvolvimento). Se essa pasta não for gravável
(por exemplo, dentro de ``C:\\Program Files``), usa ``%APPDATA%\\Ecoa\\dados``.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def app_dir() -> Path:
    """Pasta onde o executável (ou o main.py) está."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _is_writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


@lru_cache(maxsize=1)
def data_dir() -> Path:
    portable = app_dir() / "dados"
    if _is_writable(portable):
        return portable
    base = Path(os.environ.get("APPDATA") or Path.home())
    fallback = base / "Ecoa" / "dados"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def audio_dir() -> Path:
    folder = data_dir() / "audios"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def config_file() -> Path:
    return data_dir() / "config.json"


def log_file() -> Path:
    return data_dir() / "ecoa.log"


def icon_file() -> Path:
    return data_dir() / "icon.ico"
