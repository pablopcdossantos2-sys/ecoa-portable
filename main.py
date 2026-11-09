"""Ecoa - ponto de entrada.

Uso:
    python main.py              abre a janela
    python main.py --minimized  inicia na bandeja (é assim que o Windows inicia o app)
"""
from __future__ import annotations

import argparse
import logging
import os
import queue
import sys
from logging.handlers import RotatingFileHandler


def _fix_std_streams() -> None:
    """Em modo --windowed o PyInstaller deixa stdout/stderr como None."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


def _setup_logging(log_path) -> None:
    handler = RotatingFileHandler(log_path, maxBytes=256_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def main(argv=None) -> int:
    _fix_std_streams()
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    parser = argparse.ArgumentParser(description="Ecoa - lembretes sonoros agendados")
    parser.add_argument("--minimized", action="store_true", help="inicia escondido na bandeja do sistema")
    args, _ = parser.parse_known_args(argv)

    from ecoa import autostart, paths
    from ecoa.engine import Engine
    from ecoa.models import Store
    from ecoa.player import Player
    from ecoa.singleton import SingleInstance
    from ecoa.tray import Tray

    _setup_logging(paths.log_file())
    log = logging.getLogger("ecoa")

    instance = SingleInstance("Ecoa")
    if not instance.acquire():
        return 0

    store = Store()
    store.load()
    if store.settings.autostart:
        try:
            autostart.refresh()
        except OSError:
            log.exception("Não foi possível atualizar a entrada de inicialização")

    from ecoa.ui.app import App

    player = Player()
    engine = Engine(store, player)
    ui_queue: queue.Queue = queue.Queue()
    app = App(store, engine, player, ui_queue)
    app.report_callback_exception = lambda exc, val, tb: log.error(
        "Erro na interface", exc_info=(exc, val, tb)
    )

    tray = Tray(
        on_open=lambda: ui_queue.put(app.show_window),
        on_toggle_pause=lambda: ui_queue.put(app.toggle_pause),
        on_quit=lambda: ui_queue.put(app.quit_app),
        is_paused=lambda: engine.paused,
        get_language=lambda: store.settings.language,
    )
    app.tray = tray
    tray.start()
    instance.listen(lambda: ui_queue.put(app.show_window))

    engine.start()
    log.info("Ecoa iniciado (minimizado=%s)", args.minimized)

    if args.minimized and store.settings.start_minimized:
        app.withdraw() if tray.active else app.iconify()

    try:
        app.mainloop()
    finally:
        engine.stop()
        player.shutdown()
        tray.stop()
        instance.close()
        log.info("Ecoa encerrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
