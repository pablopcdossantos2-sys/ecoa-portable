"""Componentes reutilizáveis com o visual do Ecoa."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T


class Segmented(ctk.CTkFrame):
    """Seletor segmentado com contraste legível nos temas claro e escuro."""

    def __init__(self, master, values, command=None, width: int = 110, height: int = 34):
        super().__init__(master, fg_color=T.SURFACE, corner_radius=10)
        self._values = list(values)
        self._command = command
        self._value = self._values[0]
        self._buttons: dict[str, ctk.CTkButton] = {}
        for i, value in enumerate(self._values):
            button = ctk.CTkButton(
                self, text=value, width=width, height=height, corner_radius=8, border_width=0,
                command=lambda v=value: self._select(v, notify=True),
            )
            button.grid(row=0, column=i, padx=3, pady=3)
            self._buttons[value] = button
        self._paint()

    def _paint(self) -> None:
        for value, button in self._buttons.items():
            if value == self._value:
                button.configure(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER,
                                 text_color=T.ON_ACCENT, font=T.font(13, "bold"))
            else:
                button.configure(fg_color="transparent", hover_color=T.SURFACE_HOVER,
                                 text_color=T.TEXT, font=T.font(13))

    def _select(self, value: str, notify: bool) -> None:
        if value == self._value:
            return
        self._value = value
        self._paint()
        if notify and self._command:
            self._command(value)

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        if value in self._buttons:
            self._value = value
            self._paint()


def button(parent, text: str, command, kind: str = "secondary", **kw) -> ctk.CTkButton:
    styles = {
        "primary": dict(fg_color=T.ACCENT, hover_color=T.ACCENT_HOVER, text_color=T.ON_ACCENT,
                        font=T.font(13, "bold")),
        "secondary": dict(fg_color=T.SURFACE, hover_color=T.SURFACE_HOVER, text_color=T.TEXT,
                          font=T.font(13)),
        "danger": dict(fg_color=T.SURFACE, hover_color=T.DANGER_SOFT, text_color=T.DANGER,
                       font=T.font(13)),
    }
    options = dict(corner_radius=10, height=36)
    options.update(styles[kind])
    options.update(kw)
    return ctk.CTkButton(parent, text=text, command=command, **options)


def entry(parent, variable=None, width: int = 80, **kw) -> ctk.CTkEntry:
    options = dict(width=width, height=36, corner_radius=8, border_width=1, border_color=T.BORDER,
                   fg_color=T.SURFACE, text_color=T.TEXT, font=T.font(13))
    options.update(kw)
    return ctk.CTkEntry(parent, textvariable=variable, **options)


def chip(parent, text: str, color=None) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=f"  {text}  ", height=24, corner_radius=6, fg_color=T.SURFACE,
                        text_color=color or T.TEXT, font=T.font(12))


def switch(parent, text: str = "", variable=None, command=None, **kw) -> ctk.CTkSwitch:
    return ctk.CTkSwitch(parent, text=text, variable=variable, command=command,
                         progress_color=T.ACCENT, text_color=T.TEXT, font=T.font(13), **kw)
