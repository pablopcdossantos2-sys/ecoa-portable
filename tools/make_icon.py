"""Gera assets/icon.ico (usado pelo PyInstaller). Uso: python tools/make_icon.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ecoa.icon import make_icon  # noqa: E402

target = ROOT / "assets" / "icon.ico"
target.parent.mkdir(exist_ok=True)
sizes = [(n, n) for n in (16, 24, 32, 48, 64, 128, 256)]
make_icon(256).save(target, format="ICO", sizes=sizes)
print(f"Ícone gerado em {target}")
