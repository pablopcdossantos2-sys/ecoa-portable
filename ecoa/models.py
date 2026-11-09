"""Modelos (lembretes e configurações) e armazenamento em JSON."""
from __future__ import annotations

import filecmp
import json
import logging
import os
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import paths, schedule

log = logging.getLogger("ecoa.models")

MODE_INTERVAL = "interval"
MODE_LOOP = "loop"
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac")
CONFIG_VERSION = 1


def _clamp(value, low, high, default):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def resolve_audio(stored: str) -> Path:
    """Caminhos relativos são sempre relativos à pasta ``dados`` (portabilidade)."""
    p = Path(stored)
    return p if p.is_absolute() else paths.data_dir() / p


def to_stored_path(path: Path) -> str:
    """Se o arquivo está dentro de ``dados``, guarda o caminho relativo."""
    try:
        return path.resolve().relative_to(paths.data_dir().resolve()).as_posix()
    except ValueError:
        return str(path)


@dataclass
class Reminder:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = "Novo lembrete"
    audio_path: str = ""
    enabled: bool = True
    mode: str = MODE_INTERVAL          # "interval" | "loop"
    interval_value: int = 30
    interval_unit: str = "min"         # "min" | "h"
    repeats: int = 1                   # repetições a cada disparo (modo intervalo)
    gap_seconds: int = 2               # pausa entre repetições
    start: str = "09:00"
    end: str = "18:00"
    days: list = field(default_factory=lambda: list(ALL_DAYS))
    volume: int = 80                   # 0-100

    @classmethod
    def from_dict(cls, data: dict) -> "Reminder":
        known = {f.name for f in fields(cls)}
        reminder = cls(**{k: v for k, v in data.items() if k in known})
        reminder.sanitize()
        return reminder

    def to_dict(self) -> dict:
        return asdict(self)

    def sanitize(self) -> None:
        self.name = (str(self.name).strip() or "Lembrete")[:80]
        if self.mode not in (MODE_INTERVAL, MODE_LOOP):
            self.mode = MODE_INTERVAL
        if self.interval_unit not in ("min", "h"):
            self.interval_unit = "min"
        high = 24 if self.interval_unit == "h" else 1440
        self.interval_value = _clamp(self.interval_value, 1, high, 30)
        self.repeats = _clamp(self.repeats, 1, 20, 1)
        self.gap_seconds = _clamp(self.gap_seconds, 0, 3600, 2)
        self.volume = _clamp(self.volume, 0, 100, 80)
        self.start = schedule.normalize_hhmm(self.start) or "09:00"
        self.end = schedule.normalize_hhmm(self.end) or "18:00"
        days = {d for d in (self.days or []) if isinstance(d, int) and 0 <= d <= 6}
        self.days = sorted(days)
        self.enabled = bool(self.enabled)

    def audio_file(self) -> Path | None:
        if not self.audio_path:
            return None
        p = resolve_audio(self.audio_path)
        return p if p.is_file() else None


@dataclass
class Settings:
    autostart: bool = False
    start_minimized: bool = True       # ao iniciar com o Windows, abre na bandeja
    close_to_tray: bool = True         # o X da janela manda para a bandeja
    copy_audio: bool = True            # copia os áudios para dados/audios
    theme: str = "system"              # system | dark | light

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        known = {f.name for f in fields(cls)}
        s = cls(**{k: v for k, v in data.items() if k in known})
        if s.theme not in ("system", "dark", "light"):
            s.theme = "system"
        return s


class Store:
    """Guarda configurações e lembretes; seguro para uso entre threads."""

    def __init__(self, path: Path | None = None):
        self.path = path or paths.config_file()
        self.settings = Settings()
        self.reminders: list[Reminder] = []
        self._lock = threading.RLock()

    # ------------------------------------------------------------ disco
    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.settings = Settings.from_dict(raw.get("settings", {}))
                self.reminders = [Reminder.from_dict(d) for d in raw.get("reminders", [])]
            except (OSError, ValueError, TypeError) as exc:
                backup = self.path.with_name(f"config.corrompido-{int(time.time())}.json")
                log.error("Configuração inválida (%s). Backup em %s", exc, backup.name)
                try:
                    os.replace(self.path, backup)
                except OSError:
                    pass
                self.settings, self.reminders = Settings(), []

    def save(self) -> None:
        with self._lock:
            payload = {
                "version": CONFIG_VERSION,
                "settings": asdict(self.settings),
                "reminders": [r.to_dict() for r in self.reminders],
            }
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)

    # ------------------------------------------------------- lembretes
    def snapshot(self) -> list[Reminder]:
        with self._lock:
            return list(self.reminders)

    def upsert(self, reminder: Reminder) -> None:
        with self._lock:
            for i, current in enumerate(self.reminders):
                if current.id == reminder.id:
                    self.reminders[i] = reminder
                    return
            self.reminders.append(reminder)

    def remove(self, rid: str) -> None:
        with self._lock:
            self.reminders = [r for r in self.reminders if r.id != rid]

    # ----------------------------------------------------------- áudio
    def import_audio(self, source: str) -> str:
        """Devolve o caminho a guardar. Copia para ``dados/audios`` se configurado."""
        src = resolve_audio(source)
        if not self.settings.copy_audio:
            return to_stored_path(src)
        target_dir = paths.audio_dir()
        if src.resolve().parent == target_dir.resolve():
            return to_stored_path(src)
        dest = target_dir / src.name
        n = 1
        while dest.exists():
            if filecmp.cmp(src, dest, shallow=False):
                return to_stored_path(dest)
            dest = target_dir / f"{src.stem} ({n}){src.suffix}"
            n += 1
        shutil.copy2(src, dest)
        return to_stored_path(dest)
