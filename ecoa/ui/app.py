"""Janela principal do Ecoa."""
from __future__ import annotations

import logging
import queue
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .. import APP_NAME, APP_TAGLINE, __version__, autostart, paths
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
        ctk.CTkLabel(info, text=reminder.name, font=T.font(16, "bold"), text_color=T.TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(info, text=f"{reminder.mode} • {reminder.start}–{reminder.end} • {reminder.audio_path or 'sem áudio'}",
                     font=T.font(11), text_color=T.MUTED, wraplength=440).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.status = ctk.CTkLabel(info, text="", font=T.font(12), text_color=T.MUTED)
        self.status.grid(row=2, column=0, sticky="w", pady=(5, 0))
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=0, column=1, padx=12, pady=10)
        self.enabled = ctk.BooleanVar(value=reminder.enabled)
        switch(controls, "Ativo", self.enabled, self._toggle).grid(row=0, column=0, columnspan=3, sticky="e", pady=(0, 8))
        button(controls, "Testar", self._test, width=66).grid(row=1, column=0, padx=2)
        button(controls, "Editar", self._edit, width=66).grid(row=1, column=1, padx=2)
        button(controls, "Excluir", self._delete, kind="danger", width=66).grid(row=1, column=2, padx=2)
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
            messagebox.showwarning(APP_NAME, "O arquivo de áudio não foi encontrado.", parent=self.app)
            return
        self.app.engine.toggle_test(self.app.engine.test_key(self.reminder.id), str(audio), self.reminder.volume)

    def _edit(self):
        ReminderEditor(self.app, self.reminder, lambda r: self.app.store_reminder(r))

    def _delete(self):
        if messagebox.askyesno(APP_NAME, f"Excluir “{self.reminder.name}”?", parent=self.app):
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
        self.title(f"{APP_NAME} — {APP_TAGLINE} — {__version__}")
        self.geometry("960x680")
        self.minsize(760, 520)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_NAME, font=T.font(28, "bold"), text_color=T.TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Lembretes sonoros agendados", font=T.font(12), text_color=T.MUTED).grid(row=1, column=0, sticky="w")
        self.pause_btn = button(header, "Pausar tudo", self.toggle_pause, width=130)
        self.pause_btn.grid(row=0, column=1, rowspan=2, padx=6)
        button(header, "Novo lembrete", self.new_reminder, kind="primary", width=140).grid(row=0, column=2, rowspan=2, padx=6)
        self.listbox = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=10)
        self.listbox.grid_columnconfigure(0, weight=1)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 16))
        button(footer, "Abrir pasta de dados", self._open_data, width=150).pack(side="left")
        self.theme_menu = ctk.CTkOptionMenu(footer, values=["system", "dark", "light"], command=self._set_theme,
                                             fg_color=T.SURFACE, button_color=T.ACCENT, text_color=T.TEXT)
        self.theme_menu.set(store.settings.theme)
        self.theme_menu.pack(side="left", padx=8)
        self.close_label = ctk.CTkLabel(footer, text="Feche a janela para manter o app na bandeja (quando disponível).",
                                         font=T.font(11), text_color=T.MUTED)
        self.close_label.pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(250, self._set_icon)
        self.after(200, self._pump)
        self.after(1000, self._tick)
        self.refresh_reminders()

    def refresh_reminders(self):
        for child in self.listbox.winfo_children():
            child.destroy()
        reminders = self.store.snapshot()
        if not reminders:
            ctk.CTkLabel(self.listbox, text="Nenhum lembrete cadastrado. Clique em “Novo lembrete” para começar.",
                         text_color=T.MUTED, font=T.font(14)).grid(row=0, column=0, pady=40)
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
        self.pause_btn.configure(text="Retomar lembretes" if self.engine.paused else "Pausar tudo")
        if self.tray:
            self.tray.update()
        self.refresh_reminders()

    def _set_theme(self, value):
        self.store.settings.theme = value
        ctk.set_appearance_mode(value)
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
            log.exception("Não foi possível abrir a pasta de dados")

    def _set_icon(self):
        icon = ensure_ico(paths.icon_file())
        if icon:
            try:
                self.iconbitmap(str(icon))
            except Exception:
                log.debug("Ícone da janela indisponível", exc_info=True)

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
                self.tray.notify("O Ecoa continua na bandeja. Use o menu do ícone para sair.")
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
            messagebox.showerror(APP_NAME, f"Não foi possível salvar as configurações:\n{exc}", parent=self)

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
