"""Regras de agendamento - lógica pura, sem dependências de interface ou áudio.

Conceitos:
* **Faixa de horário** (``start`` -> ``end``): intervalo meio-aberto [início, fim).
  Se ``end`` < ``start`` a faixa cruza a meia-noite (ex.: 22:00 -> 06:00).
  Se ``end`` == ``start`` a faixa é o dia todo (24 h) a partir de ``start``.
* **Dias da semana** (``days``): 0 = segunda ... 6 = domingo. Em faixas que cruzam
  a meia-noite, vale o dia em que a faixa *começa*.
* **Intervalo**: os disparos acontecem numa grade ancorada no início da faixa
  (ex.: 09:00 a cada 45 min -> 09:00, 09:45, 10:30...). Assim os horários são
  previsíveis e não "derivam" com o tempo.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Iterator

from .i18n import day_names, tr

DAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def normalize_hhmm(text) -> str | None:
    """Aceita '9', '900', '9:5', '09:00', '9h30'... e devolve 'HH:MM' (ou None)."""
    s = str(text).strip().lower().replace("h", ":")
    if not s:
        return None
    if ":" in s:
        hh, _, mm = s.partition(":")
        mm = mm or "0"
    else:
        if not s.isdigit() or len(s) > 4:
            return None
        if len(s) <= 2:
            hh, mm = s, "0"
        else:
            hh, mm = s[:-2], s[-2:]
    if not (hh.isdigit() and mm.isdigit()):
        return None
    h, m = int(hh), int(mm)
    if 0 <= h <= 23 and 0 <= m <= 59:
        return f"{h:02d}:{m:02d}"
    return None


def to_time(hhmm: str) -> time:
    h, m = hhmm.split(":")
    return time(int(h), int(m))


def _minutes(hhmm: str) -> int:
    t = to_time(hhmm)
    return t.hour * 60 + t.minute


def interval_delta(r) -> timedelta:
    value = max(1, int(r.interval_value))
    return timedelta(hours=value) if r.interval_unit == "h" else timedelta(minutes=value)


def window_duration(r) -> timedelta:
    diff = (_minutes(r.end) - _minutes(r.start)) % 1440
    return timedelta(minutes=diff or 1440)


def is_full_day(r) -> bool:
    return r.start == r.end


def iter_windows(r, ref: datetime, back: int = 1, ahead: int = 8) -> Iterator[tuple[datetime, datetime]]:
    """Gera (início, fim) das faixas ativas em ordem cronológica ao redor de ``ref``."""
    duration = window_duration(r)
    start_t = to_time(r.start)
    days = set(r.days)
    base = ref.date()
    for offset in range(-back, ahead + 1):
        day = base + timedelta(days=offset)
        if day.weekday() not in days:
            continue
        ws = datetime.combine(day, start_t)
        yield ws, ws + duration


def active_window(r, now: datetime) -> tuple[datetime, datetime] | None:
    for ws, we in iter_windows(r, now):
        if ws <= now < we:
            return ws, we
    return None


def next_window_start(r, after: datetime) -> datetime | None:
    for ws, _ in iter_windows(r, after):
        if ws > after:
            return ws
    return None


def next_trigger(r, after: datetime) -> datetime | None:
    """Próximo disparo (estritamente depois de ``after``) no modo intervalo."""
    step = interval_delta(r)
    for ws, we in iter_windows(r, after):
        if we <= after:
            continue
        if after < ws:
            candidate = ws
        else:
            candidate = ws + ((after - ws) // step + 1) * step
        if candidate < we:
            return candidate
    return None


# ---------------------------------------------------------------- textos


def fmt_when(dt: datetime, now: datetime, language: str = "pt_BR") -> str:
    hhmm = dt.strftime("%H:%M")
    delta = (dt.date() - now.date()).days
    if delta == 0:
        return tr(language, "today", time=hhmm)
    if delta == 1:
        return tr(language, "tomorrow", time=hhmm)
    return tr(language, "weekday_at", day=day_names(language)[dt.weekday()], time=hhmm)


def describe_days(days) -> str:
    d = sorted(set(days))
    if len(d) == 7:
        return "Todos os dias"
    if d == [0, 1, 2, 3, 4]:
        return "Seg a Sex"
    if d == [5, 6]:
        return "Fins de semana"
    if not d:
        return "Nenhum dia"
    return ", ".join(DAY_LABELS[i] for i in d)


def describe_window(r) -> str:
    if is_full_day(r):
        return "Dia todo"
    return f"{r.start} às {r.end}"


def describe_rule(r) -> str:
    if r.mode == "loop":
        return "Em loop contínuo"
    unit = "h" if r.interval_unit == "h" else "min"
    return f"A cada {int(r.interval_value)} {unit}"
