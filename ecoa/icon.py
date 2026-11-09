"""Ícone do app desenhado por código (ondas de eco), sem arquivos de imagem."""
from __future__ import annotations

from pathlib import Path

BG = (15, 37, 48, 255)
WAVE = (44, 200, 192, 255)
BG_PAUSED = (60, 72, 80, 255)
WAVE_PAUSED = (140, 156, 164, 255)


def make_icon(size: int = 256, paused: bool = False):
    from PIL import Image, ImageDraw

    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg, wave = (BG_PAUSED, WAVE_PAUSED) if paused else (BG, WAVE)
    draw.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.24), fill=bg)

    cx, cy = s * 0.33, s * 0.5
    dot = s * 0.085
    draw.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=wave)
    for radius in (0.19, 0.30, 0.41):
        r = s * radius
        draw.arc((cx - r, cy - r, cx + r, cy + r), start=-48, end=48, fill=wave, width=int(s * 0.055))
    return img.resize((size, size), Image.LANCZOS)


def ensure_ico(path: Path) -> Path | None:
    """Gera um .ico (usado na janela e na barra de tarefas). None se falhar."""
    try:
        if not path.exists():
            sizes = [(n, n) for n in (16, 24, 32, 48, 64, 128, 256)]
            make_icon(256).save(path, format="ICO", sizes=sizes)
        return path
    except Exception:  # noqa: BLE001
        return None
