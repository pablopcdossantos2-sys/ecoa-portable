"""Reprodução de áudio (pygame.mixer): mp3, wav, ogg e flac.

Cada reprodução roda em uma "tarefa" (thread) identificada por um ``rid``. Isso
permite parar um lembrete específico, repetir N vezes ou tocar em loop até ser
interrompido. O mixer é iniciado sob demanda e reiniciado se o dispositivo de
áudio falhar (comum logo após ligar o PC, quando o áudio ainda não está pronto).
"""
from __future__ import annotations

import logging
import os
import threading
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

log = logging.getLogger("ecoa.player")


class _Job:
    __slots__ = ("rid", "path", "volume", "repeats", "gap", "loop", "stop")

    def __init__(self, rid, path, volume, repeats, gap, loop):
        self.rid = rid
        self.path = path
        self.volume = volume
        self.repeats = repeats
        self.gap = gap
        self.loop = loop
        self.stop = threading.Event()


class Player:
    def __init__(self):
        self._lock = threading.RLock()
        self._jobs: dict[str, _Job] = {}
        self._sounds: dict[str, tuple[float, object]] = {}
        self.last_error = ""

    # ------------------------------------------------------------ mixer
    def _ensure_mixer(self):
        import pygame  # importado aqui para abrir a interface mais rápido

        with self._lock:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(44100, -16, 2, 1024)
                pygame.mixer.init()
                pygame.mixer.set_num_channels(32)
        return pygame

    def _reset_mixer(self) -> None:
        with self._lock:
            self._sounds.clear()
            try:
                import pygame

                pygame.mixer.quit()
            except Exception:  # noqa: BLE001
                pass

    def _load(self, pygame, path: str):
        mtime = os.path.getmtime(path)
        cached = self._sounds.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        sound = pygame.mixer.Sound(path)
        self._sounds[path] = (mtime, sound)
        return sound

    def clear_cache(self) -> None:
        with self._lock:
            self._sounds.clear()

    def reset_audio(self) -> None:
        """Para tudo e reinicia o dispositivo de áudio (ex.: trocou o fone/saída)."""
        self.stop_all()
        time.sleep(0.3)
        self._reset_mixer()

    # ------------------------------------------------------- reprodução
    def _play_once(self, job: _Job) -> bool:
        channel = None
        for attempt in (1, 2):
            try:
                pygame = self._ensure_mixer()
                sound = self._load(pygame, job.path)
                sound.set_volume(job.volume)
                channel = sound.play()
                break
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                log.warning("Falha ao tocar '%s' (tentativa %d): %s", job.path, attempt, exc)
                if attempt == 1:
                    self._reset_mixer()
                    time.sleep(0.5)
                else:
                    return False
        if channel is None:
            log.warning("Sem canal de áudio livre para '%s'", job.path)
            return False
        while channel.get_busy():
            if job.stop.wait(0.1):
                channel.fadeout(200)
                return False
        return True

    def _worker(self, job: _Job) -> None:
        try:
            done = 0
            while not job.stop.is_set():
                ok = self._play_once(job)
                if job.stop.is_set():
                    break
                done += 1
                if not job.loop and done >= job.repeats:
                    break
                pause = job.gap if ok else max(job.gap, 5)
                if job.stop.wait(pause):
                    break
        except Exception:  # noqa: BLE001
            log.exception("Erro inesperado na reprodução de '%s'", job.path)
        finally:
            with self._lock:
                if self._jobs.get(job.rid) is job:
                    del self._jobs[job.rid]

    def run(self, rid: str, path: str, volume: float, repeats: int = 1, gap: float = 0, loop: bool = False) -> bool:
        """Inicia uma reprodução. Devolve False se ``rid`` já estiver tocando."""
        with self._lock:
            if rid in self._jobs:
                return False
            job = _Job(rid, path, max(0.0, min(1.0, volume)), max(1, repeats), max(0, gap), loop)
            self._jobs[rid] = job
        threading.Thread(target=self._worker, args=(job,), daemon=True, name=f"play-{rid}").start()
        return True

    def is_playing(self, rid: str) -> bool:
        with self._lock:
            return rid in self._jobs

    def stop(self, rid: str) -> None:
        with self._lock:
            job = self._jobs.get(rid)
        if job:
            job.stop.set()

    def stop_all(self) -> None:
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            job.stop.set()

    def shutdown(self) -> None:
        self.stop_all()
        time.sleep(0.3)
        self._reset_mixer()
