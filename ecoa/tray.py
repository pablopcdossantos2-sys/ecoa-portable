"""Ícone na bandeja do sistema (pystray), com menu multilíngue."""
from __future__ import annotations

import logging

from . import APP_NAME
from .icon import make_icon
from .i18n import tr

log = logging.getLogger("ecoa.tray")


class Tray:
    def __init__(self, on_open, on_toggle_pause, on_quit, is_paused, get_language=None):
        self._on_open = on_open
        self._on_toggle = on_toggle_pause
        self._on_quit = on_quit
        self._is_paused = is_paused
        self._get_language = get_language or (lambda: "pt_BR")
        self._icon = None
        self.active = False

    def _text(self, key: str) -> str:
        return tr(self._get_language(), key)

    def start(self) -> bool:
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem(lambda item: self._text("tray_open"),
                                 lambda icon, item: self._on_open(), default=True),
                pystray.MenuItem(
                    lambda item: self._text("tray_resume") if self._is_paused() else self._text("tray_pause"),
                    lambda icon, item: self._on_toggle(),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(lambda item: self._text("tray_quit"), lambda icon, item: self._on_quit()),
            )
            self._icon = pystray.Icon(APP_NAME, make_icon(64), self._text("tray_title"), menu)
            self._icon.run_detached()
            self.active = True
        except Exception:  # noqa: BLE001
            log.exception("System tray unavailable")
            self.active = False
        return self.active

    def update(self) -> None:
        if not self._icon:
            return
        try:
            paused = self._is_paused()
            self._icon.icon = make_icon(64, paused)
            state = self._text("tray_paused" if paused else "tray_active")
            self._icon.title = f"{APP_NAME} - {state}"
            self._icon.update_menu()
        except Exception:  # noqa: BLE001
            log.exception("Could not update the system tray icon")

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
