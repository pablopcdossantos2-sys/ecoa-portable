"""Janela principal do Ecoa: um único painel, sem barra lateral."""
from __future__ import annotations

import logging
import queue
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .. import APP_NAME, __version__, autostart, paths
from ..i18n import LANGUAGES, language_from_label, language_label, theme_from_label, theme_label, theme_options, tr
from ..icon import ensure_ico
from ..models import Reminder
from . import theme as T
from .editor import ReminderEditor
from .widgets import button, switch

log = logging.getLogger("ecoa.ui")


class ReminderCard(ctk.CTkFrame):
    def __init__(self, master, app: "App", reminder: Reminder):
        super().__init__(master, fg_color=T.CARD, corner_radius=14, border_width=1, border_color=T.BORDER)
        self.app, self.reminder = app, reminder
        self.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=0, sticky="ew", padx=14, pady=12)
        info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(info, text=reminder.name, font=T.font(16, "bold"), text_color=T.TEXT).grid(
            row=0, column=0, sticky="w"
        )
        mode_key = "mode_loop" if reminder.mode == "loop" else "mode_interval"
        audio_name = Path(reminder.audio_path).name if reminder.audio_path else tr(app.language, "no_audio")
        detail = f"{tr(app.language, mode_key)}  •  {reminder.start}–{reminder.end}  •  {audio_name}"
        ctk.CTkLabel(info, text=detail, font=T.font(11), text_color=T.MUTED, wraplength=560).grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        self.status = ctk.CTkLabel(info, text="", font=T.font(12), text_color=T.MUTED)
        self.status.grid(row=2, column=0, sticky="w", pady=(5, 0))

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=0, column=1, padx=12, pady=10)
        self.enabled = ctk.BooleanVar(value=reminder.enabled)
        switch(controls, tr(app.language, "active"), self.enabled, self._toggle).grid(
            row=0, column=0, columnspan=3, sticky="e", pady=(0, 8)
        )
        button(controls, tr(app.language, "test"), self._test, width=76).grid(row=1, column=0, padx=2)
        button(controls, tr(app.language, "edit"), self._edit, width=76).grid(row=1, column=1, padx=2)
        button(controls, tr(app.language, "delete"), self._delete, kind="danger", width=76).grid(
            row=1, column=2, padx=2
        )
        self.refresh()

    def _toggle(self):
        from dataclasses import replace
        self.reminder = replace(self.reminder, enabled=bool(self.enabled.get()))
        self.app.store.upsert(self.reminder)
        self.app.save()
        self.app.engine.invalidate(self.reminder.id)
        self.refresh()

    def _test(self):
        audio = self.reminder.audio_file()
        if audio is None:
            messagebox.showwarning(APP_NAME, tr(self.app.language, "audio_missing"), parent=self.app)
            return
        self.app.engine.toggle_test(self.app.engine.test_key(self.reminder.id), str(audio), self.reminder.volume)

    def _edit(self):
        ReminderEditor(self.app, self.reminder, self.app.store_reminder)

    def _delete(self):
        if messagebox.askyesno(APP_NAME, tr(self.app.language, "delete_confirm", name=self.reminder.name),
                               parent=self.app):
            self.app.store.remove(self.reminder.id)
            self.app.save()
            self.app.engine.invalidate(self.reminder.id)
            self.app.refresh_reminders()

    def refresh(self):
        text, kind = self.app.engine.status(self.reminder)
        self.status.configure(text=text, text_color=T.STATUS_COLORS[kind])


class App(ctk.CTk):
    def __init__(self, store, engine, player, ui_queue: "queue.Queue"):
        ctk.set_appearance_mode(store.settings.theme)
        super().__init__(fg_color=T.BG)
        self.store, self.engine, self.player, self.ui_queue = store, engine, player, ui_queue
        self.tray = None
        self._quitting = False
        self._tray_hint_shown = False
        self.title(f"{APP_NAME} — {__version__}")
        self.geometry("1020x700")
        self.minsize(860, 560)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_interface()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(250, self._set_icon)
        self.after(200, self._pump)
        self.after(1000, self._tick)

    @property
    def language(self) -> str:
        return self.store.settings.language

    def tr(self, key: str, **values) -> str:
        return tr(self.language, key, **values)

    def _build_interface(self):
        """Reconstrói os textos e controles quando o idioma é alterado."""
        for child in self.winfo_children():
            child.destroy()

        root = ctk.CTkFrame(self, fg_color="transparent")
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_NAME, font=T.font(28, "bold"), text_color=T.TEXT).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(header, text=self.tr("subtitle"), font=T.font(12), text_color=T.MUTED).grid(
            row=1, column=0, sticky="w"
        )
        self.pause_btn = button(header, self.tr("resume_all") if self.engine.paused else self.tr("pause_all"),
                                self.toggle_pause, width=160)
        self.pause_btn.grid(row=0, column=1, rowspan=2, padx=6)
        button(header, self.tr("new_reminder"), self.new_reminder, kind="primary", width=165).grid(
            row=0, column=2, rowspan=2, padx=6
        )

        self.listbox = ctk.CTkScrollableFrame(root, fg_color="transparent")
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=8)
        self.listbox.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(root, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=26, pady=(6, 18))
        button(footer, self.tr("open_data"), self._open_data, width=170).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(footer, text=self.tr("theme"), text_color=T.MUTED, font=T.font(12)).pack(side="left", padx=(2, 5))
        self.theme_menu = ctk.CTkOptionMenu(
            footer,
            values=theme_options(self.language),
            command=self._set_theme,
            fg_color=T.SURFACE,
            button_color=T.ACCENT,
            text_color=T.TEXT,
            width=118,
        )
        self.theme_menu.set(theme_label(self.language, self.store.settings.theme))
        self.theme_menu.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(footer, text=self.tr("language"), text_color=T.MUTED, font=T.font(12)).pack(
            side="left", padx=(2, 5)
        )
        self.language_menu = ctk.CTkOptionMenu(
            footer,
            values=list(LANGUAGES.values()),
            command=self._set_language,
            fg_color=T.SURFACE,
            button_color=T.ACCENT,
            text_color=T.TEXT,
            width=155,
        )
        self.language_menu.set(language_label(self.language))
        self.language_menu.pack(side="left")
        ctk.CTkLabel(footer, text=self.tr("close_hint"), font=T.font(11), text_color=T.MUTED).pack(
            side="right", padx=(12, 0)
        )
        self.refresh_reminders()

    def _set_language(self, label: str):
        language = language_from_label(label)
        if language == self.store.settings.language:
            return
        self.store.settings.language = language
        self.save()
        self._build_interface()
        if self.tray:
            self.tray.update()

    def refresh_reminders(self):
        for child in self.listbox.winfo_children():
            child.destroy()
        reminders = self.store.snapshot()
        if not reminders:
            ctk.CTkLabel(
                self.listbox, text=self.tr("empty"), text_color=T.MUTED, font=T.font(14), justify="center"
            ).grid(row=0, column=0, pady=44)
        for row, reminder in enumerate(reminders):
            ReminderCard(self.listbox, self, reminder).grid(row=row, column=0, sticky="ew", padx=6, pady=6)

    def store_reminder(self, reminder):
        self.store.upsert(reminder)
        self.save()
        self.engine.invalidate(reminder.id)
        self.refresh_reminders()

    def new_reminder(self):
        ReminderEditor(self, None, self.store_reminder)

    def toggle_pause(self):
        self.engine.set_paused(not self.engine.paused)
        self.refresh_pause_ui()

    def refresh_pause_ui(self):
        self.pause_btn.configure(text=self.tr("resume_all") if self.engine.paused else self.tr("pause_all"))
        if self.tray:
            self.tray.update()
        self.refresh_reminders()

    def _set_theme(self, label):
        theme = theme_from_label(self.language, label)
        self.store.settings.theme = theme
        ctk.set_appearance_mode(theme)
        self.save()

    def _open_data(self):
        folder = paths.data_dir()
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(folder))
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError:
            log.exception("Could not open the data folder")

    def _set_icon(self):
        icon = ensure_ico(paths.icon_file())
        if icon:
            try:
                self.iconbitmap(str(icon))
            except Exception:
                log.debug("Window icon unavailable", exc_info=True)

    def show_window(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def on_close(self):
        if self.store.settings.close_to_tray and self.tray and self.tray.active:
            self.withdraw()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.notify(self.tr("tray_notice"))
        else:
            self.quit_app()

    def quit_app(self):
        if self._quitting:
            return
        self._quitting = True
        try:
            self.engine.stop()
            self.player.shutdown()
        finally:
            if self.tray:
                self.tray.stop()
            self.destroy()

    def save(self):
        try:
            self.store.save()
        except OSError as exc:
            messagebox.showerror(APP_NAME, self.tr("save_error", error=exc), parent=self)

    def _pump(self):
        try:
            while True:
                self.ui_queue.get_nowait()()
        except queue.Empty:
            pass
        if not self._quitting:
            self.after(200, self._pump)

    def _tick(self):
        if not self._quitting:
            self.refresh_reminders()
            self.after(1500, self._tick)
