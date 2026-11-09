"""Iniciar com o Windows via chave HKCU\\...\\Run (não exige administrador)."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import winreg
except ImportError:  # fora do Windows (desenvolvimento em outro SO)
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Ecoa"


def supported() -> bool:
    return winreg is not None


def command() -> str:
    """Comando gravado no registro. Sempre com --minimized para abrir na bandeja."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else Path(sys.executable)
    script = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{interpreter}" "{script}" --minimized'


def _read() -> str | None:
    if not supported():
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return value
    except FileNotFoundError:
        return None


def is_enabled() -> bool:
    return _read() is not None


def enable() -> None:
    if not supported():
        raise OSError("Iniciar com o Windows só está disponível no Windows.")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command())


def disable() -> None:
    if not supported():
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass


def refresh() -> None:
    """Se a pasta do app foi movida, atualiza o caminho gravado no registro."""
    current = _read()
    if current is not None and current != command():
        enable()
