"""Oxco-spezifischer Duennwrapper um win_taskbar_icon.py."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import tkinter as tk

import win_taskbar_icon as wti

OXCO_APP_USER_MODEL_ID = "PepegaSan.Oxco.GUI.1"


def prepare_windows_taskbar_icon() -> None:
    wti.prepare(OXCO_APP_USER_MODEL_ID)


def _resolve_embedded_ico() -> Optional[Path]:
    try:
        from oxco_icon_embed import materialize_icon_ico

        return materialize_icon_ico()
    except (ImportError, OSError):
        return None


def ensure_stable_icon_path(asset_resolver: Callable[[str], Path]) -> Optional[Path]:
    src = asset_resolver("oxco_icon.ico")
    if not src.is_file():
        src = _resolve_embedded_ico()
    if src is None or not src.is_file():
        return None
    return wti.cache_icon(src, app_name="Oxco")


def resolve_windows_icon_source(asset_resolver: Callable[[str], Path]) -> Optional[str]:
    if getattr(__import__("sys"), "frozen", False):
        return wti.resolve_icon_path(
            asset_resolver("oxco_icon.ico"),
            app_name="Oxco",
            prefer_exe_when_frozen=True,
            use_cache=False,
        )
    ico = ensure_stable_icon_path(asset_resolver)
    if ico is not None:
        return str(ico.resolve())
    return None


def apply_windows_window_icon(root: tk.Misc, asset_resolver: Callable[[str], Path]) -> bool:
    import sys

    if getattr(sys, "frozen", False):
        return wti.apply(
            root,
            asset_resolver("oxco_icon.ico"),
            app_name="Oxco",
            prefer_exe_when_frozen=True,
            use_cache=False,
        )
    ico = ensure_stable_icon_path(asset_resolver)
    if ico is None:
        return False
    return wti.apply(root, ico, app_name="Oxco", use_cache=False)
