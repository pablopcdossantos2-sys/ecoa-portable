"""Formulário para cadastrar e alterar lembretes sonoros."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import schedule
from ..models import AUDIO_EXTENSIONS, MODE_INTERVAL, MODE_LOOP, Reminder, resolve_audio
from . import theme as T
from .widgets import button, entry

class ReminderEditor(ctk.CTkToplevel):
    def __init__(self, app, reminder: Reminder | None, on_save):
        super().__init__(app)
        self.app, self.on_save = app, on_save
        self.draft = replace(reminder) if reminder else Reminder(name="")
        self.audio_path = self.draft.audio_path
        self.title("Novo lembrete" if reminder is None else "Editar lembrete")
        self.geometry("560x700")
        self.minsize(500, 600)
        self.configure(fg_color=T.BG)
        self.transient(app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.body.grid_columnconfigure(1, weight=1)
        d = self.draft
        row = 0
        def label(text):
            nonlocal row
            ctk.CTkLabel(self.body, text=text, font=T.font(13, "bold"), text_color=T.TEXT).grid(
                row=row, column=0, sticky="w", padx=8, pady=8)
        label("Nome")
        self.name = ctk.StringVar(value=d.name)
        entry(self.body, self.name, width=300).grid(row=row, column=1, sticky="ew", padx=8, pady=8)
        row += 1

        label("Áudio")
        self.audio_label = ctk.CTkLabel(self.body, text=Path(self.audio_path).name or "Nenhum áudio escolhido",
                                        text_color=T.MUTED, anchor="w")
        self.audio_label.grid(row=row, column=1, sticky="ew", padx=8)
        button(self.body, "Escolher", self._choose, width=90).grid(row=row, column=2, padx=8)
        row += 1

        label("Modo")
        self.mode = ctk.StringVar(value=d.mode)
        ctk.CTkOptionMenu(self.body, variable=self.mode, values=[MODE_INTERVAL, MODE_LOOP],
                          fg_color=T.ACCENT, button_color=T.ACCENT).grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        label("Intervalo")
        self.interval = ctk.StringVar(value=str(d.interval_value))
        entry(self.body, self.interval, width=80).grid(row=row, column=1, sticky="w", padx=8)
        self.unit = ctk.StringVar(value=d.interval_unit)
        ctk.CTkOptionMenu(self.body, variable=self.unit, values=["min", "h"], width=90).grid(row=row, column=2, padx=8)
        row += 1

        label("Repetições por disparo")
        self.repeats = ctk.StringVar(value=str(d.repeats))
        entry(self.body, self.repeats, width=80).grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        label("Pausa entre repetições (s)")
        self.gap = ctk.StringVar(value=str(d.gap_seconds))
        entry(self.body, self.gap, width=80).grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        label("Horário inicial")
        self.start = ctk.StringVar(value=d.start)
        entry(self.body, self.start, width=100).grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        label("Horário final")
        self.end = ctk.StringVar(value=d.end)
        entry(self.body, self.end, width=100).grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        self.days = [ctk.BooleanVar(value=i in d.days) for i in range(7)]
        ctk.CTkLabel(self.body, text="Dias da semana", font=T.font(13, "bold"), text_color=T.TEXT).grid(
            row=row, column=0, sticky="w", padx=8, pady=8)
        daybox = ctk.CTkFrame(self.body, fg_color="transparent")
        daybox.grid(row=row, column=1, columnspan=2, sticky="w")
        for i, name in enumerate(schedule.DAY_LABELS):
            ctk.CTkCheckBox(daybox, text=name, variable=self.days[i], width=55).grid(row=0, column=i, padx=2)
        row += 1

        label("Volume (%)")
        self.volume = ctk.CTkSlider(self.body, from_=0, to=100, number_of_steps=100)
        self.volume.set(d.volume)
        self.volume.grid(row=row, column=1, sticky="ew", padx=8, pady=8)
        row += 1

        self.allday = ctk.BooleanVar(value=schedule.is_full_day(d))
        ctk.CTkCheckBox(self.body, text="Dia todo (24 h)", variable=self.allday).grid(
            row=row, column=1, sticky="w", padx=8, pady=8)
        row += 1

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=12, pady=12)
        button(footer, "Cancelar", self._close).pack(side="right", padx=5)
        button(footer, "Salvar", self._save, kind="primary").pack(side="right", padx=5)
        self.grab_set()

    def _choose(self):
        patterns = " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS)
        chosen = filedialog.askopenfilename(parent=self, title="Escolher áudio",
            filetypes=[("Arquivos de áudio", patterns), ("Todos os arquivos", "*.*")])
        if chosen:
            self.audio_path = chosen
            self.audio_label.configure(text=Path(chosen).name)

    def _close(self):
        self.app.player.stop("test:editor")
        self.destroy()

    def _save(self):
        if not self.audio_path or not resolve_audio(self.audio_path).is_file():
            messagebox.showwarning("Ecoa", "Escolha um arquivo de áudio válido.", parent=self)
            return
        try:
            value, repeats, gap = int(self.interval.get()), int(self.repeats.get()), int(self.gap.get())
        except ValueError:
            messagebox.showwarning("Ecoa", "Informe números válidos para intervalo, repetições e pausa.", parent=self)
            return
        if not 1 <= value <= (24 if self.unit.get() == "h" else 1440):
            messagebox.showwarning("Ecoa", "Intervalo fora do limite permitido.", parent=self)
            return
        if not 1 <= repeats <= 20 or not 0 <= gap <= 3600:
            messagebox.showwarning("Ecoa", "Repetições devem ser 1–20 e pausa 0–3600 segundos.", parent=self)
            return
        if self.allday.get():
            start = end = "00:00"
        else:
            start, end = schedule.normalize_hhmm(self.start.get()), schedule.normalize_hhmm(self.end.get())
            if not start or not end or start == end:
                messagebox.showwarning("Ecoa", "Informe horários válidos e diferentes, ou marque Dia todo.", parent=self)
                return
        days = [i for i, var in enumerate(self.days) if var.get()]
        if not days:
            messagebox.showwarning("Ecoa", "Selecione ao menos um dia da semana.", parent=self)
            return
        try:
            stored = self.app.store.import_audio(self.audio_path)
        except OSError as exc:
            messagebox.showerror("Ecoa", f"Não foi possível copiar o áudio: {exc}", parent=self)
            return
        result = replace(self.draft, name=self.name.get().strip() or Path(self.audio_path).stem,
            audio_path=stored, mode=self.mode.get(), interval_value=value, interval_unit=self.unit.get(),
            repeats=repeats, gap_seconds=gap, start=start, end=end, days=days,
            volume=round(self.volume.get()))
        result.sanitize()
        self._close()
        self.on_save(result)
