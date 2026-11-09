"""Identidade visual do Ecoa.

Ideia: "sonar". Barra lateral sempre em azul-petróleo profundo, conteúdo claro ou
escuro conforme o sistema, um único acento verde-azulado (a onda do eco) e âmbar
reservado para o que está tocando agora. Todas as cores são pares (claro, escuro).
"""
from __future__ import annotations

from functools import lru_cache

import customtkinter as ctk

FONT_FAMILY = "Segoe UI"

# Superfícies
BG = ("#EBF1F1", "#0D151B")
CARD = ("#FFFFFF", "#15212A")
BORDER = ("#D3DFDF", "#243642")
SURFACE = ("#E2EBEB", "#1D2C37")
SURFACE_HOVER = ("#D2DFDF", "#283B49")

# Texto
TEXT = ("#10222B", "#E7F0F2")
MUTED = ("#586F78", "#8CA2AC")

# Acento (onda do eco)
ACCENT = ("#0B8A8A", "#2CC8C0")
ACCENT_HOVER = ("#097272", "#55DCD5")
ACCENT_SOFT = ("#D3ECEC", "#173A3F")
ON_ACCENT = ("#FFFFFF", "#04201F")

# Estados
LIVE = ("#C47A06", "#F2A93B")      # tocando agora
DANGER = ("#C23B33", "#EE6A62")
DANGER_SOFT = ("#F8E3E1", "#3A1D1D")
IDLE = ("#8497A0", "#667B86")

# Barra lateral (igual nos dois modos)
SIDEBAR = ("#0F2530", "#09121A")
SIDEBAR_TEXT = "#E7F0F2"
SIDEBAR_MUTED = "#8FA9B5"
SIDEBAR_ACTIVE = ("#1B4350", "#15303B")
SIDEBAR_HOVER = ("#173845", "#112832")

STATUS_COLORS = {
    "playing": LIVE,
    "waiting": ACCENT,
    "idle": IDLE,
    "off": IDLE,
    "error": DANGER,
}


@lru_cache(maxsize=None)
def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
