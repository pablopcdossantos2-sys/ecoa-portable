"""Ícone na bandeja do sistema (pystray)."""
from __future__ import annotations

import logging

from . import APP_NAME
from .icon import make_icon

log = logging.getLogger("ecoa.tray")


class Tray:
    def __init__(self, on_open, on_toggle_pause, on_quit, is_paused):
        self._on_open = on_open
        self._on_toggle = on_toggle_pause
        self._on_quit = on_quit
        self._is_paused = is_paused
        self._icon = None
        self.active = False

    def start(self) -> bool:
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem(f"Abrir {APP_NAME}", lambda icon, item: self._on_open(), default=True),
                pystray.MenuItem(
                    lambda item: "Retomar lembretes" if self._is_paused() else "Pausar lembretes",
                    lambda icon, item: self._on_toggle(),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Sair", lambda icon, item: self._on_quit()),
            )
            self._icon = pystray.Icon(APP_NAME, make_icon(64), f"{APP_NAME} - lembretes sonoros", menu)
            self._icon.run_detached()
            self.active = True
        except Exception:  # noqa: BLE001
            log.exception("Bandeja do sistema indisponível")
            self.active = False
        return self.active

    def update(self) -> None:
        if not self._icon:
            return
        try:
            paused = self._is_paused()
            self._icon.icon = make_icon(64, paused)
            self._icon.title = f"{APP_NAME} - {'pausado' if paused else 'ativo'}"
            self._icon.update_menu()
        except Exception:  # noqa: BLE001
            log.exception("Falha ao atualizar o ícone da bandeja")

    def notify(self, message: str) -> None:
        if self._icon and self.active:
            try:
                self._icon.notify(message, APP_NAME)
            except Exception:  # noqa: BLE001
                pass

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:  # noqa: BLE001
                pass
        self.active = False
