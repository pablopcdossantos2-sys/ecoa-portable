"""Formulário amplo e traduzido para criar ou editar lembretes."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import schedule
from ..i18n import day_names, tr
from ..models import AUDIO_EXTENSIONS, MODE_INTERVAL, MODE_LOOP, Reminder, resolve_audio
from . import theme as T
from .widgets import button, entry


class ReminderEditor(ctk.CTkToplevel):
    def __init__(self, app, reminder: Reminder | None, on_save):
        super().__init__(app)
        self.app, self.on_save = app, on_save
        self.language = app.language
        self.tr = lambda key, **values: tr(self.language, key, **values)
        self.draft = replace(reminder) if reminder else Reminder(name="")
        self.audio_path = self.draft.audio_path
        self.title(self.tr("editor_new") if reminder is None else self.tr("editor_edit"))
        self.configure(fg_color=T.BG)
        self.transient(app)

        # A grade de dias tem sete opções lado a lado. A janela é deliberadamente
        # larga para que nenhum rótulo ou controle fique comprimido.
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(960, max(860, screen_w - 80))
        height = min(760, max(640, screen_h - 100))
        x, y = max(0, (screen_w - width) // 2), max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(860, screen_w - 40), min(640, screen_h - 60))

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=18, pady=(14, 6))
        self.body.grid_columnconfigure(0, minsize=250)
        self.body.grid_columnconfigure(1, weight=1)
        self.body.grid_columnconfigure(2, minsize=150)

        d = self.draft
        row = 0

        def label(text: str):
            nonlocal row
            ctk.CTkLabel(self.body, text=text, font=T.font(13, "bold"), text_color=T.TEXT).grid(
                row=row, column=0, sticky="w", padx=10, pady=9
            )

        label(self.tr("name"))
        self.name = ctk.StringVar(value=d.name)
        entry(self.body, self.name, width=360).grid(row=row, column=1, columnspan=2, sticky="ew", padx=10, pady=9)
        row += 1

        label(self.tr("audio"))
        self.audio_label = ctk.CTkLabel(
            self.body,
            text=Path(self.audio_path).name if self.audio_path else self.tr("no_audio"),
            text_color=T.MUTED,
            anchor="w",
        )
        self.audio_label.grid(row=row, column=1, sticky="ew", padx=10, pady=8)
        button(self.body, self.tr("choose"), self._choose, width=110).grid(row=row, column=2, padx=10, pady=8)
        row += 1

        label(self.tr("mode"))
        self.mode_labels = {
            MODE_INTERVAL: self.tr("mode_interval"),
            MODE_LOOP: self.tr("mode_loop"),
        }
        self.mode_reverse = {value: key for key, value in self.mode_labels.items()}
        self.mode_display = ctk.StringVar(value=self.mode_labels[d.mode])
        ctk.CTkOptionMenu(
            self.body,
            variable=self.mode_display,
            values=list(self.mode_reverse),
            width=220,
            fg_color=T.ACCENT,
            button_color=T.ACCENT,
        ).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        label(self.tr("interval"))
        self.interval = ctk.StringVar(value=str(d.interval_value))
        entry(self.body, self.interval, width=100).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self.unit_labels = {"min": self.tr("minutes"), "h": self.tr("hours")}
        self.unit_reverse = {value: key for key, value in self.unit_labels.items()}
        self.unit_display = ctk.StringVar(value=self.unit_labels[d.interval_unit])
        ctk.CTkOptionMenu(
            self.body,
            variable=self.unit_display,
            values=list(self.unit_reverse),
            width=140,
            fg_color=T.SURFACE,
            button_color=T.ACCENT,
            text_color=T.TEXT,
        ).grid(row=row, column=2, sticky="w", padx=10, pady=8)
        row += 1

        label(self.tr("repeats"))
        self.repeats = ctk.StringVar(value=str(d.repeats))
        entry(self.body, self.repeats, width=100).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        label(self.tr("gap"))
        self.gap = ctk.StringVar(value=str(d.gap_seconds))
        entry(self.body, self.gap, width=100).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        label(self.tr("start"))
        self.start = ctk.StringVar(value=d.start)
        entry(self.body, self.start, width=120).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        label(self.tr("end"))
        self.end = ctk.StringVar(value=d.end)
        entry(self.body, self.end, width=120).grid(row=row, column=1, sticky="w", padx=10, pady=8)
        row += 1

        ctk.CTkLabel(self.body, text=self.tr("days"), font=T.font(13, "bold"), text_color=T.TEXT).grid(
            row=row, column=0, sticky="w", padx=10, pady=9
        )
        daybox = ctk.CTkFrame(self.body, fg_color="transparent")
        daybox.grid(row=row, column=1, columnspan=2, sticky="w", padx=6, pady=6)
        self.days = [ctk.BooleanVar(value=i in d.days) for i in range(7)]
        for i, name in enumerate(day_names(self.language)):
            ctk.CTkCheckBox(daybox, text=name, variable=self.days[i], width=62, font=T.font(12)).grid(
                row=0, column=i, padx=4, pady=4
            )
        row += 1

        label(self.tr("volume"))
        self.volume = ctk.CTkSlider(self.body, from_=0, to=100, number_of_steps=100)
        self.volume.set(d.volume)
        self.volume.grid(row=row, column=1, sticky="ew", padx=10, pady=10)
        self.volume_value = ctk.CTkLabel(self.body, text=f"{d.volume}%", text_color=T.MUTED, width=56)
        self.volume_value.grid(row=row, column=2, sticky="w", padx=10)
        self.volume.configure(command=lambda value: self.volume_value.configure(text=f"{round(value)}%"))
        row += 1

        self.allday = ctk.BooleanVar(value=schedule.is_full_day(d))
        ctk.CTkCheckBox(self.body, text=self.tr("all_day"), variable=self.allday, font=T.font(13)).grid(
            row=row, column=1, columnspan=2, sticky="w", padx=10, pady=10
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=18, pady=(6, 16))
        button(footer, self.tr("cancel"), self._close, width=120).pack(side="right", padx=6)
        button(footer, self.tr("save"), self._save, kind="primary", width=130).pack(side="right", padx=6)
        self.grab_set()

    def _choose(self):
        patterns = " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS)
        chosen = filedialog.askopenfilename(
            parent=self,
            title=self.tr("choose_audio_title"),
            filetypes=[
                (self.tr("audio_files"), patterns),
                (self.tr("all_files"), "*.*"),
            ],
        )
        if chosen:
            self.audio_path = chosen
            self.audio_label.configure(text=Path(chosen).name)

    def _close(self):
        self.app.player.stop("test:editor")
        self.destroy()

    def _save(self):
        if not self.audio_path or not resolve_audio(self.audio_path).is_file():
            messagebox.showwarning(self.tr("warning"), self.tr("choose_valid_audio"), parent=self)
            return
        try:
            value = int(self.interval.get())
            repeats = int(self.repeats.get())
            gap = int(self.gap.get())
        except ValueError:
            messagebox.showwarning(self.tr("warning"), self.tr("valid_numbers"), parent=self)
            return

        unit = self.unit_reverse[self.unit_display.get()]
        if not 1 <= value <= (24 if unit == "h" else 1440):
            messagebox.showwarning(self.tr("warning"), self.tr("interval_range"), parent=self)
            return
        if not 1 <= repeats <= 20 or not 0 <= gap <= 3600:
            messagebox.showwarning(self.tr("warning"), self.tr("repeats_range"), parent=self)
            return

        if self.allday.get():
            start = end = "00:00"
        else:
            start = schedule.normalize_hhmm(self.start.get())
            end = schedule.normalize_hhmm(self.end.get())
            if not start or not end or start == end:
                messagebox.showwarning(self.tr("warning"), self.tr("valid_times"), parent=self)
                return

        days = [i for i, var in enumerate(self.days) if var.get()]
        if not days:
            messagebox.showwarning(self.tr("warning"), self.tr("choose_day"), parent=self)
            return

        try:
            stored = self.app.store.import_audio(self.audio_path)
        except (OSError, RuntimeError) as exc:
            messagebox.showerror(self.tr("error"), self.tr("copy_audio_error", error=exc), parent=self)
            return

        result = replace(
            self.draft,
            name=self.name.get().strip() or Path(self.audio_path).stem,
            audio_path=stored,
            mode=self.mode_reverse[self.mode_display.get()],
            interval_value=value,
            interval_unit=unit,
            repeats=repeats,
            gap_seconds=gap,
            start=start,
            end=end,
            days=days,
            volume=round(self.volume.get()),
        )
        result.sanitize()
        self._close()
        self.on_save(result)
