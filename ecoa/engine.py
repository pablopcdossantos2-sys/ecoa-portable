"""Motor de agendamento: decide, a cada tick, o que deve tocar ou parar."""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from . import schedule
from .models import MODE_LOOP, Reminder, Store
from .i18n import tr
from .player import Player

log = logging.getLogger("ecoa.engine")

TICK_SECONDS = 0.5
# Se o PC estava suspenso/ocupado e o disparo atrasou mais que isso, ele é pulado.
LATE_TOLERANCE_SECONDS = 90


class _State:
    __slots__ = ("next_run",)

    def __init__(self):
        self.next_run: datetime | None = None


class Engine:
    def __init__(self, store: Store, player: Player):
        self.store = store
        self.player = player
        self.paused = False
        self._states: dict[str, _State] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # --------------------------------------------------------- ciclo de vida
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ecoa-engine")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.player.stop_all()

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        if paused:
            self.player.stop_all()

    def invalidate(self, rid: str) -> None:
        """Chame depois de editar/remover um lembrete: recalcula e para o áudio dele."""
        with self._lock:
            self._states.pop(rid, None)
        self.player.stop(rid)
        self.player.clear_cache()

    # ------------------------------------------------------------- testes
    def test_key(self, rid: str) -> str:
        return f"test:{rid}"

    def is_testing(self, rid: str) -> bool:
        return self.player.is_playing(self.test_key(rid))

    def toggle_test(self, key: str, path: str, volume_percent: int) -> None:
        """Toca uma vez (ou para, se já estiver tocando). Ignora faixa de horário."""
        if self.player.is_playing(key):
            self.player.stop(key)
        else:
            self.player.run(key, path, volume_percent / 100, repeats=1)

    # ------------------------------------------------------------ status UI
    def status(self, r: Reminder, now: datetime | None = None) -> tuple[str, str]:
        """Texto traduzido e tipo de status para a interface."""
        now = now or datetime.now()
        language = self.store.settings.language
        if not r.enabled:
            return tr(language, "status_disabled"), "off"
        if r.audio_file() is None:
            return tr(language, "status_audio_missing"), "error"
        if self.paused:
            return tr(language, "status_paused"), "off"
        if not r.days:
            return tr(language, "status_no_days"), "off"
        playing = self.player.is_playing(r.id)
        if r.mode == MODE_LOOP:
            window = schedule.active_window(r, now)
            if window:
                key = "status_loop_playing" if playing else "status_loop_waiting"
                return tr(language, key, end=window[1].strftime("%H:%M")), "playing" if playing else "waiting"
            nxt = schedule.next_window_start(r, now)
            return (tr(language, "status_starts", when=schedule.fmt_when(nxt, now, language)), "idle") if nxt else (
                tr(language, "status_no_runs"), "off"
            )
        if playing:
            return tr(language, "status_playing"), "playing"
        with self._lock:
            state = self._states.get(r.id)
            next_run = state.next_run if state else None
        if next_run:
            return tr(language, "status_next", when=schedule.fmt_when(next_run, now, language)), "idle"
        return tr(language, "status_no_scheduled"), "off"

    # ------------------------------------------------------------- loop
    def _run(self) -> None:
        while not self._stop.wait(TICK_SECONDS):
            try:
                self.tick(datetime.now())
            except Exception:  # noqa: BLE001
                log.exception("Erro no ciclo do agendador")

    def tick(self, now: datetime) -> None:
        reminders = self.store.snapshot()
        live = {r.id for r in reminders}
        with self._lock:
            for rid in [k for k in self._states if k not in live]:
                del self._states[rid]
                self.player.stop(rid)
        for r in reminders:
            self._tick_one(r, now)

    def _state(self, rid: str) -> _State:
        with self._lock:
            return self._states.setdefault(rid, _State())

    def _tick_one(self, r: Reminder, now: datetime) -> None:
        state = self._state(r.id)
        audio = r.audio_file()
        if self.paused or not r.enabled or audio is None or not r.days:
            state.next_run = None
            if r.mode == MODE_LOOP:
                self.player.stop(r.id)
            return

        if r.mode == MODE_LOOP:
            in_window = schedule.active_window(r, now) is not None
            playing = self.player.is_playing(r.id)
            if in_window and not playing:
                log.info("Loop iniciado: %s", r.name)
                self.player.run(r.id, str(audio), r.volume / 100, gap=r.gap_seconds, loop=True)
            elif not in_window and playing:
                log.info("Loop encerrado (fim da faixa): %s", r.name)
                self.player.stop(r.id)
            return

        if state.next_run is None:
            state.next_run = schedule.next_trigger(r, now)
        elif now >= state.next_run:
            late = (now - state.next_run).total_seconds()
            if late <= LATE_TOLERANCE_SECONDS:
                log.info("Disparo: %s", r.name)
                self.player.run(r.id, str(audio), r.volume / 100, repeats=r.repeats, gap=r.gap_seconds)
            else:
                log.info("Disparo atrasado %.0fs pulado: %s", late, r.name)
            state.next_run = schedule.next_trigger(r, now)
