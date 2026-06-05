#!/usr/bin/env python3
"""
Oxco — ein Fenster für Compare, Bitrate und Autotagger im selben Projektordner.
Tkinter/ttk, angelehnt an README_Robocopy_GUI (klare LabelFrames, persistente Geometrie).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import tkinter as tk
import configparser
import datetime as _dt
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Sequence, Set

import oxco_workers as ow
import oxco_i18n as oi
from oxco_player import OxcoTaggerPreview, OxcoVideoPreview

CONFIG_NAME = "oxco_config.json"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return app_dir() / CONFIG_NAME


def default_davinci_api_path() -> str:
    """Blackmagic-Standard: Ordner mit DaVinciResolveScript (Studio)."""
    if sys.platform == "win32":
        pd = os.environ.get("ProgramData", r"C:\ProgramData")
        return str(
            Path(pd)
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Developer"
            / "Scripting"
            / "Modules"
        )
    if sys.platform == "darwin":
        return (
            "/Library/Application Support/Blackmagic Design/"
            "DaVinci Resolve/Developer/Scripting/Modules"
        )
    return ""


def default_davinci_exe_path() -> str:
    """Optionaler Auto-Start: Resolve-Binary (Windows/macOS)."""
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        preferred = Path(pf) / "Blackmagic Design" / "DaVinci Resolve" / "Resolve.exe"
        if preferred.is_file():
            return str(preferred)
        bmd = Path(pf) / "Blackmagic Design"
        if bmd.is_dir():
            hits = sorted(
                bmd.glob("DaVinci Resolve*/Resolve.exe"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if hits:
                return str(hits[0])
        return str(preferred)
    if sys.platform == "darwin":
        for p in (
            Path("/Applications/DaVinci Resolve.app/Contents/MacOS/Resolve"),
            Path(
                "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/MacOS/Resolve"
            ),
        ):
            if p.is_file():
                return str(p)
        return "/Applications/DaVinci Resolve.app/Contents/MacOS/Resolve"
    return ""


def load_config() -> Dict[str, Any]:
    p = config_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: Dict[str, Any]) -> None:
    p = config_path()
    p.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def clamp_geometry(root: tk.Tk, w: int, h: int, x: int, y: int) -> str:
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w = max(720, min(w, sw - 40))
    h = max(520, min(h, sh - 60))
    x = max(0, min(x, sw - w - 20))
    y = max(0, min(y, sh - h - 40))
    return f"{w}x{h}+{x}+{y}"


class OxcoApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._cfg = load_config()
        self._geom_timer: Optional[str] = None

        self._compare_busy = False
        self._compare_proc: Optional[Any] = None
        self._compare_user_stopped = False
        self._compare_batch_queue: List[tuple[str, str]] = []
        self._compare_batch_index = 0
        self._compare_batch_mode = False
        self._compare_patched_ini: Optional[str] = None
        self._compare_orig_entries: List[ow.CompareFileEntry] = []
        self._compare_df_entries: List[ow.CompareFileEntry] = []
        self._compare_orig_by_iid: Dict[str, Path] = {}
        self._compare_df_by_iid: Dict[str, Path] = {}
        self._compare_probe_generation = 0
        self._compare_selected_orig_sig: Optional[str] = None
        self._compare_suppress_tree_select = False
        self._compare_orig_select_after: Optional[str] = None
        self._bitrate_rows: List[ow.VideoRow] = []
        self._bitrate_scan_folder: Optional[Path] = None
        self._bitrate_stop = threading.Event()
        self._bitrate_thread: Optional[threading.Thread] = None
        self._tagger_scan_paths: List[Path] = []
        self._pipe_canvas: Optional[tk.Canvas] = None
        self._pipe_win_id: Optional[int] = None
        self._video_preview: Optional[OxcoVideoPreview] = None
        self._tagger_preview: Optional[OxcoTaggerPreview] = None
        self._notebook: Optional[ttk.Notebook] = None
        self._settings_win: Optional[tk.Toplevel] = None
        self._tag_route_win: Optional[tk.Toplevel] = None
        self._tag_route_row_vars: List[tuple[tk.StringVar, tk.StringVar]] = []
        self._tag_route_busy = False

        # —— Variablen: Pfade ——
        # Compare-Export → Bitrate-Scan (wenn gekoppelt, siehe trace).
        # Autotagger-Quelle = Bitrate-Ausgabeordner (wenn gekoppelt, siehe trace).
        _ce = str(self._cfg.get("compare_export_dir", "")).strip()
        _bi_saved = str(self._cfg.get("bitrate_in_dir", "")).strip()
        _bo_saved = str(self._cfg.get("bitrate_out_dir", "")).strip()
        _ti_saved = str(self._cfg.get("tagger_in_dir", "")).strip()
        _to_saved = str(self._cfg.get("tagger_out_dir", "")).strip()

        self.var_compare_export = tk.StringVar(value=_ce)
        _bi_effective = _bi_saved or _ce
        self.var_bitrate_in = tk.StringVar(value=_bi_effective)
        self.var_bitrate_out = tk.StringVar(value=_bo_saved)
        self.var_tagger_in = tk.StringVar(value=_ti_saved or _bo_saved)
        self.var_tagger_out = tk.StringVar(value=_to_saved)

        self._suppress_path_sync = False
        self._path_refresh_bitrate_follows_export()
        self._path_refresh_tagger_follows_bitrate()
        self.var_compare_export.trace_add("write", self._on_path_compare_export_write)
        self.var_bitrate_in.trace_add("write", self._on_path_bitrate_in_write)
        self.var_bitrate_out.trace_add("write", self._on_path_bitrate_out_write)
        self.var_tagger_in.trace_add("write", self._on_path_tagger_in_write)

        # —— Compare Dateien ——
        self.var_source = tk.StringVar(value=str(self._cfg.get("last_source", "")))
        self.var_deepfake = tk.StringVar(value=str(self._cfg.get("last_deepfake", "")))

        # —— UI-Sprache + DaVinci (Einstellungen / settings.ini) ——
        _ui = str(self._cfg.get("ui_language", "")).strip().lower()
        if not _ui and "filter_lang" in self._cfg:
            _ui = str(self._cfg.get("filter_lang", "de")).strip().lower()
        if _ui not in ("de", "en"):
            _ui = "de"
        self.var_ui_lang = tk.StringVar(value=_ui)
        self._default_davinci_api = default_davinci_api_path()
        self._default_davinci_exe = default_davinci_exe_path()
        _api_saved = str(self._cfg.get("davinci_api_path", "")).strip()
        _exe_saved = str(self._cfg.get("davinci_exe_path", "")).strip()
        self.var_davinci_api = tk.StringVar(value=_api_saved or self._default_davinci_api)
        self.var_davinci_preset = tk.StringVar(
            value=str(self._cfg.get("davinci_render_preset", "AutoCutPreset"))
        )
        self.var_davinci_exe = tk.StringVar(value=_exe_saved or self._default_davinci_exe)
        _dsw = self._cfg.get("davinci_startup_wait_seconds", "20")
        self.var_davinci_startup_wait = tk.StringVar(value=str(_dsw).strip() or "20")
        self._sync_davinci_from_ini_if_needed()

        # —— Filter Compare ——
        self.var_buffer = tk.StringVar(value=str(self._cfg.get("filter_buffer", "2.0")))
        self.var_noise = tk.StringVar(value=str(self._cfg.get("filter_noise", "15")))
        self.var_pixel = tk.StringVar(value=str(self._cfg.get("filter_pixel", "200")))
        self.var_pixel_max = tk.StringVar(value=str(self._cfg.get("filter_pixel_max", "0")))
        self.var_ffmpeg = tk.BooleanVar(value=bool(self._cfg.get("filter_ffmpeg", True)))
        self.var_davinci = tk.BooleanVar(value=bool(self._cfg.get("filter_davinci", True)))
        self.var_ffmpeg_target = tk.StringVar(value=str(self._cfg.get("filter_ffmpeg_target", "deepfake")))
        self.var_davinci_timeout = tk.StringVar(value=str(self._cfg.get("filter_davinci_timeout", "1800")))
        self.var_export_unique = tk.BooleanVar(value=bool(self._cfg.get("filter_export_unique", True)))

        # —— Bitrate ——
        self.var_br_recursive = tk.BooleanVar(value=bool(self._cfg.get("br_recursive", True)))
        self.var_br_only_lower = tk.BooleanVar(value=bool(self._cfg.get("br_only_lower", True)))
        self.var_br_suffix = tk.StringVar(value=str(self._cfg.get("br_suffix", "_bitrate")))
        self.var_br_mp4 = tk.BooleanVar(value=bool(self._cfg.get("br_output_mp4", False)))
        self.var_br_codec = tk.StringVar(value=str(self._cfg.get("br_codec", "libx264")))
        self.var_br_audio = tk.StringVar(value=str(self._cfg.get("br_audio", "copy")))
        self.var_br_delete_source = tk.BooleanVar(value=bool(self._cfg.get("br_delete_source_after_ok", False)))
        self.var_br_preset = tk.StringVar(value=str(self._cfg.get("br_preset", "Standard")))
        self._br_rule_vars: Dict[int, tk.StringVar] = {
            t: tk.StringVar(value=str(ow.BUILTIN_PRESETS["Standard"][t])) for t in ow.RULE_ORDER
        }
        for t in ow.RULE_ORDER:
            key = f"br_rule_{t}"
            if key in self._cfg:
                self._br_rule_vars[t].set(str(self._cfg[key]))

        # —— Tagger ——
        self.var_tag = tk.StringVar(value=str(self._cfg.get("tagger_tag", "[Stash]")))
        self.var_tag_profile = tk.StringVar(value=str(self._cfg.get("tagger_profile_name", "Schritt1")))
        self.var_keep = tk.StringVar(value=str(self._cfg.get("tagger_keep", "_hyb,_pro,_exp")))
        self.var_ignore = tk.StringVar(value=str(self._cfg.get("tagger_ignore", "_p")))
        self.var_drop = tk.StringVar(value=str(self._cfg.get("tagger_drop", "")))
        self.var_pattern = tk.StringVar(value=str(self._cfg.get("tagger_pattern", "YYMMDDHHmmSS")))
        self._tag_route_rules: List[Dict[str, str]] = self._parse_tag_route_rules_cfg(
            self._cfg.get("tagger_route_rules")
        )
        self.var_tagger_route_auto = tk.BooleanVar(value=bool(self._cfg.get("tagger_route_auto", False)))

        self.var_compare_source_dir = tk.StringVar(
            value=str(self._cfg.get("compare_source_dir", "")).strip()
        )
        self.var_compare_deepfake_dir = tk.StringVar(
            value=str(self._cfg.get("compare_deepfake_dir", "")).strip()
        )
        self.var_compare_recursive = tk.BooleanVar(value=bool(self._cfg.get("compare_recursive", True)))
        self.var_compare_sort = tk.StringVar(value=str(self._cfg.get("compare_sort", "date_desc")))
        self.var_compare_group = tk.StringVar(value=str(self._cfg.get("compare_group", "folder")))

        self._ensure_oxco_compare_settings()
        self._build_ui()
        self._apply_window_title()
        self.root.minsize(720, 560)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Configure>", self._on_configure)

        self.root.after(150, lambda: self._tagger_refresh_list(log_count=True))

        self.root.update_idletasks()
        geom = str(self._cfg.get("window_geometry", "")).strip()
        if geom:
            try:
                self.root.geometry(geom)
            except tk.TclError:
                self.root.geometry(clamp_geometry(self.root, 1180, 820, 80, 60))
        else:
            self.root.geometry(clamp_geometry(self.root, 1180, 820, 80, 60))

    def _ensure_oxco_compare_settings(self) -> None:
        root = app_dir()
        ini = root / "settings.ini"
        example = root / "settings.example.ini"
        if not ini.is_file() and example.is_file():
            try:
                shutil.copy2(example, ini)
            except OSError:
                pass

    def _sync_davinci_from_ini_if_needed(self) -> None:
        def _missing_cfg(key: str) -> bool:
            return not str(self._cfg.get(key, "")).strip()

        ini = app_dir() / "settings.ini"
        if not ini.is_file():
            return
        try:
            cp = configparser.ConfigParser()
            cp.read(ini, encoding="utf-8")
            if _missing_cfg("davinci_api_path") and cp.has_section("PATHS") and cp.has_option(
                "PATHS", "davinci_api_path"
            ):
                v = cp.get("PATHS", "davinci_api_path").strip()
                if v:
                    self.var_davinci_api.set(v)
            if _missing_cfg("davinci_render_preset") and cp.has_section("SETTINGS") and cp.has_option(
                "SETTINGS", "davinci_render_preset"
            ):
                p = cp.get("SETTINGS", "davinci_render_preset").strip()
                if p:
                    self.var_davinci_preset.set(p)
            if _missing_cfg("davinci_exe_path") and cp.has_section("PATHS") and cp.has_option(
                "PATHS", "davinci_exe_path"
            ):
                e = cp.get("PATHS", "davinci_exe_path").strip()
                if e:
                    self.var_davinci_exe.set(e)
            if _missing_cfg("davinci_startup_wait_seconds") and cp.has_section("SETTINGS") and cp.has_option(
                "SETTINGS", "davinci_startup_wait_seconds"
            ):
                s = cp.get("SETTINGS", "davinci_startup_wait_seconds").strip()
                if s:
                    self.var_davinci_startup_wait.set(s)
        except (configparser.Error, OSError, ValueError):
            pass

    def _path_refresh_bitrate_follows_export(self) -> None:
        ce = self.var_compare_export.get().strip()
        bi = self.var_bitrate_in.get().strip()
        self._bitrate_in_follows_compare_export = (not bi) or (bi == ce)

    def _path_refresh_tagger_follows_bitrate(self) -> None:
        bo = self.var_bitrate_out.get().strip()
        ti = self.var_tagger_in.get().strip()
        self._tagger_in_follows_bitrate = (not ti) or (ti == bo)

    def _path_apply_bitrate_in_from_export_if_linked(self) -> None:
        if not getattr(self, "_bitrate_in_follows_compare_export", False):
            return
        ce = self.var_compare_export.get().strip()
        if self.var_bitrate_in.get().strip() == ce:
            return
        self._suppress_path_sync = True
        try:
            self.var_bitrate_in.set(ce)
        finally:
            self._suppress_path_sync = False
        self._path_refresh_bitrate_follows_export()

    def _path_apply_tagger_in_from_bitrate_if_linked(self) -> None:
        if not getattr(self, "_tagger_in_follows_bitrate", False):
            return
        bo = self.var_bitrate_out.get().strip()
        if not bo:
            return
        if self.var_tagger_in.get().strip() == bo:
            return
        self._suppress_path_sync = True
        try:
            self.var_tagger_in.set(bo)
        finally:
            self._suppress_path_sync = False
        self._path_refresh_tagger_follows_bitrate()

    def _on_path_compare_export_write(self, *_args: Any) -> None:
        if getattr(self, "_suppress_path_sync", False):
            return
        self._path_apply_bitrate_in_from_export_if_linked()
        self._path_refresh_bitrate_follows_export()

    def _on_path_bitrate_in_write(self, *_args: Any) -> None:
        if getattr(self, "_suppress_path_sync", False):
            return
        self._path_refresh_bitrate_follows_export()
        if self._bitrate_in_follows_compare_export and self.var_compare_export.get().strip():
            self._path_apply_bitrate_in_from_export_if_linked()

    def _on_path_bitrate_out_write(self, *_args: Any) -> None:
        if getattr(self, "_suppress_path_sync", False):
            return
        self._path_refresh_tagger_follows_bitrate()
        self._path_apply_tagger_in_from_bitrate_if_linked()

    def _on_path_tagger_in_write(self, *_args: Any) -> None:
        if getattr(self, "_suppress_path_sync", False):
            return
        self._path_refresh_tagger_follows_bitrate()
        self.root.after(150, lambda: self._tagger_refresh_list(log_count=False))

    def tr(self, key: str, **kwargs: Any) -> str:
        return oi.tr(self.var_ui_lang.get(), key, **kwargs)

    def _apply_window_title(self) -> None:
        self.root.title(self.tr("app.title"))

    def _apply_ui_i18n(self) -> None:
        self._apply_window_title()
        if self._notebook is not None:
            tabs = ("tab.flow", "tab.preview", "tab.paths", "tab.filters")
            for i, key in enumerate(tabs):
                try:
                    self._notebook.tab(i, text=self.tr(key))
                except tk.TclError:
                    pass
        if getattr(self, "_log_frame", None) is not None:
            self._log_frame.configure(text=self.tr("log.title"))
        for w, k in getattr(self, "_paths_lfs", ()):
            w.configure(text=self.tr(k))
        for w, k in getattr(self, "_pipe_lfs", ()):
            w.configure(text=self.tr(k))
        for w, k in getattr(self, "_pipe_btns", ()):
            w.configure(text=self.tr(k))
        for w, k in getattr(self, "_filters_lfs", ()):
            w.configure(text=self.tr(k))
        for w, k in getattr(self, "_i18n_labeled", ()):
            try:
                w.configure(text=self.tr(k))
            except tk.TclError:
                pass
        if getattr(self, "_lbl_filters_lang_note", None) is not None:
            self._lbl_filters_lang_note.configure(text=self.tr("filters.lang_note"))
        if getattr(self, "_chk_ffmpeg", None) is not None:
            self._chk_ffmpeg.configure(text=self.tr("filters.ffmpeg_on"))
        if getattr(self, "_chk_davinci", None) is not None:
            self._chk_davinci.configure(text=self.tr("filters.davinci_on"))
        if getattr(self, "_chk_export_unique", None) is not None:
            self._chk_export_unique.configure(text=self.tr("filters.export_unique"))
        if getattr(self, "_chk_br_sub", None) is not None:
            self._chk_br_sub.configure(text=self.tr("filters.subfolders"))
        if getattr(self, "_chk_br_lower", None) is not None:
            self._chk_br_lower.configure(text=self.tr("filters.only_lower"))
        if getattr(self, "_chk_br_mp4", None) is not None:
            self._chk_br_mp4.configure(text=self.tr("filters.mp4"))
        if getattr(self, "_chk_br_delete_src", None) is not None:
            self._chk_br_delete_src.configure(text=self.tr("filters.br_delete_source"))
        if getattr(self, "_chk_tagger_route_auto", None) is not None:
            self._chk_tagger_route_auto.configure(text=self.tr("flow.tag_route_auto"))
        if getattr(self, "_chk_compare_recursive", None) is not None:
            self._chk_compare_recursive.configure(text=self.tr("flow.compare_recursive"))
        if hasattr(self, "_compare_sort_values"):
            self._compare_sort_labels = [self.tr(f"flow.compare_sort.{k}") for k in self._compare_sort_values]
            if getattr(self, "_cb_compare_sort", None) is not None:
                cur = self.var_compare_sort.get().strip() or "date_desc"
                self._cb_compare_sort.configure(values=self._compare_sort_labels)
                self._sync_compare_sort_combo_from_var()
        if hasattr(self, "_compare_group_values"):
            self._compare_group_labels = [self.tr(f"flow.compare_group.{k}") for k in self._compare_group_values]
            if getattr(self, "_cb_compare_group", None) is not None:
                self._cb_compare_group.configure(values=self._compare_group_labels)
                self._sync_compare_group_combo_from_var()
        if getattr(self, "tree_compare_orig", None) is not None:
            self._compare_setup_tree_columns(self.tree_compare_orig)
            self._compare_setup_tree_columns(self.tree_compare_df)
        if getattr(self, "_btn_br_preset", None) is not None:
            self._btn_br_preset.configure(text=self.tr("filters.apply_preset"))
        for lb, k in getattr(self, "_tagger_labels", []):
            lb.configure(text=self.tr(k))
        self._refresh_tree_headings()
        if self._video_preview is not None:
            self._video_preview.apply_i18n()
        if self._tagger_preview is not None:
            self._tagger_preview.apply_i18n()

    def _refresh_tree_headings(self) -> None:
        if not hasattr(self, "tree"):
            return
        self.tree.heading("datei", text=self.tr("flow.tree.file"))
        self.tree.heading("wh", text=self.tr("flow.tree.res"))
        self.tree.heading("src_k", text=self.tr("flow.tree.src_k"))
        self.tree.heading("ziel_k", text=self.tr("flow.tree.tgt_k"))
        self.tree.heading("aktion", text=self.tr("flow.tree.action"))
        if getattr(self, "tree_tagger", None) is not None:
            self.tree_tagger.heading("tf", text=self.tr("flow.tagger_tree_file"))

    def _open_settings(self) -> None:
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return
        win = tk.Toplevel(self.root)
        self._settings_win = win
        win.title(self.tr("settings.title"))
        win.transient(self.root)
        win.grab_set()
        fr = ttk.Frame(win, padding=12)
        fr.grid(row=0, column=0, sticky="nsew")
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)

        r = 0
        ttk.Label(fr, text=self.tr("settings.lang")).grid(row=r, column=0, sticky="w", pady=4)
        v_lang = tk.StringVar(
            value=self.tr("settings.lang_en")
            if self.var_ui_lang.get() == "en"
            else self.tr("settings.lang_de")
        )
        cb_lang = ttk.Combobox(
            fr,
            textvariable=v_lang,
            values=(self.tr("settings.lang_de"), self.tr("settings.lang_en")),
            width=24,
            state="readonly",
        )
        cb_lang.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        r += 1

        ttk.Label(fr, text=self.tr("settings.davinci_api")).grid(row=r, column=0, sticky="nw", pady=4)
        api_fr = ttk.Frame(fr)
        api_fr.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        api_fr.columnconfigure(0, weight=1)
        v_api = tk.StringVar(value=self.var_davinci_api.get())
        ttk.Entry(api_fr, textvariable=v_api).grid(row=0, column=0, sticky="ew")
        ttk.Button(api_fr, text="…", width=3, command=lambda: self._browse_dir_to_var(v_api)).grid(
            row=0, column=1, padx=(4, 0)
        )
        r += 1

        ttk.Label(fr, text=self.tr("settings.davinci_preset")).grid(row=r, column=0, sticky="w", pady=4)
        v_preset = tk.StringVar(value=self.var_davinci_preset.get())
        ttk.Entry(fr, textvariable=v_preset, width=40).grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        r += 1

        ttk.Label(fr, text=self.tr("settings.davinci_exe")).grid(row=r, column=0, sticky="nw", pady=4)
        exe_fr = ttk.Frame(fr)
        exe_fr.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))
        exe_fr.columnconfigure(0, weight=1)
        v_exe = tk.StringVar(value=self.var_davinci_exe.get())
        ttk.Entry(exe_fr, textvariable=v_exe).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            exe_fr,
            text="…",
            width=3,
            command=lambda: self._browse_exe_to_var(v_exe),
        ).grid(row=0, column=1, padx=(4, 0))
        r += 1

        ttk.Label(fr, text=self.tr("settings.davinci_startup_wait")).grid(row=r, column=0, sticky="w", pady=4)
        v_startup = tk.StringVar(value=self.var_davinci_startup_wait.get())
        ttk.Entry(fr, textvariable=v_startup, width=12).grid(row=r, column=1, sticky="w", pady=4, padx=(8, 0))
        r += 1

        btn_fr = ttk.Frame(fr)
        btn_fr.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        fr.columnconfigure(1, weight=1)

        def save() -> None:
            pick = v_lang.get()
            if pick == self.tr("settings.lang_en"):
                self.var_ui_lang.set("en")
            else:
                self.var_ui_lang.set("de")
            self.var_davinci_api.set(v_api.get().strip() or self._default_davinci_api)
            self.var_davinci_preset.set(v_preset.get().strip() or "AutoCutPreset")
            self.var_davinci_exe.set(v_exe.get().strip())
            try:
                dsw = max(0, min(600, int(float((v_startup.get().strip() or "20").replace(",", ".")))))
            except ValueError:
                dsw = 20
            self.var_davinci_startup_wait.set(str(dsw))
            ini = app_dir() / "settings.ini"
            ok = True
            if ini.is_file():
                ok = ow.update_compare_ini_language_and_davinci(
                    ini,
                    language=self.var_ui_lang.get(),
                    davinci_api_path=self.var_davinci_api.get(),
                    davinci_render_preset=self.var_davinci_preset.get(),
                    davinci_exe_path=self.var_davinci_exe.get(),
                    davinci_startup_wait_seconds=dsw,
                )
            self._save()
            self._apply_ui_i18n()
            if not ok:
                messagebox.showwarning(self.tr("settings.title"), self.tr("settings.ini_write_warn"))
            else:
                messagebox.showinfo(self.tr("settings.title"), self.tr("settings.saved"))
            win.destroy()
            self._settings_win = None

        def cancel() -> None:
            win.destroy()
            self._settings_win = None

        ttk.Button(btn_fr, text=self.tr("settings.save"), command=save).pack(side="left", padx=(0, 8))
        ttk.Button(btn_fr, text=self.tr("settings.cancel"), command=cancel).pack(side="left")

        win.update_idletasks()
        self._place_settings_window(win)

    def _place_settings_window(self, win: tk.Toplevel) -> None:
        """Dialog nahe dem Hauptfenster (unter dem Zahnrad) platzieren."""
        try:
            win.update_idletasks()
            self.root.update_idletasks()
            rw = win.winfo_reqwidth()
            rh = win.winfo_reqheight()
            rx = self.root.winfo_rootx()
            ry = self.root.winfo_rooty()
            rww = self.root.winfo_width()

            if getattr(self, "_btn_settings", None) is not None:
                try:
                    bx = self._btn_settings.winfo_rootx()
                    by = self._btn_settings.winfo_rooty()
                    bh = self._btn_settings.winfo_height()
                    bw = self._btn_settings.winfo_width()
                    # rechts am Button ausrichten, direkt darunter
                    x = bx + bw - rw
                    y = by + bh + 6
                except tk.TclError:
                    x = rx + rww - rw - 16
                    y = ry + 48
            else:
                x = rx + rww - rw - 16
                y = ry + 48

            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = max(8, min(int(x), sw - rw - 8))
            y = max(8, min(int(y), sh - rh - 48))
            win.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _browse_dir_to_var(self, var: tk.StringVar) -> None:
        p = filedialog.askdirectory(title=self.tr("dlg.folder"))
        if p:
            var.set(p)

    def _browse_exe_to_var(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(
            title=self.tr("settings.davinci_exe_browse"),
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if p:
            var.set(p)

    def _create_xy_scroll_area(self, host: ttk.Frame) -> ttk.Frame:
        """Liefert einen inneren Rahmen mit horizontalem und vertikalem Scroll — nichts wird abgeschnitten."""
        host.columnconfigure(0, weight=1)
        host.rowconfigure(0, weight=1)
        canvas = tk.Canvas(host, highlightthickness=0)
        vsb = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        hsb = ttk.Scrollbar(host, orient="horizontal", command=canvas.xview)
        inner = ttk.Frame(canvas, padding=8)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        def sync(_evt: Optional[tk.Event] = None) -> None:
            canvas.update_idletasks()
            inner.update_idletasks()
            cw = max(int(canvas.winfo_width()), 1)
            ch = max(int(canvas.winfo_height()), 1)
            iw = max(int(inner.winfo_reqwidth()), cw)
            ih = max(int(inner.winfo_reqheight()), ch)
            canvas.itemconfig(win_id, width=iw, height=ih)
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)

        inner.bind("<Configure>", lambda e: sync())
        canvas.bind("<Configure>", lambda e: sync() if e.widget == canvas else None)

        def wheel(e: tk.Event) -> str:
            if (e.state & 0x0001) != 0:
                canvas.xview_scroll(int(-e.delta / 120), "units")
            else:
                canvas.yview_scroll(int(-e.delta / 120), "units")
            return "break"

        canvas.bind("<MouseWheel>", wheel)
        inner.bind("<MouseWheel>", wheel)

        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        inner.columnconfigure(0, weight=1)
        inner.after(1, sync)
        return inner

    def _build_ui(self) -> None:
        self._i18n_labeled: list[tuple[tk.Misc, str]] = []
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        topbar = ttk.Frame(self.root)
        topbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        topbar.columnconfigure(0, weight=1)
        self._btn_settings = ttk.Button(topbar, text="⚙", width=3, command=self._open_settings)
        self._btn_settings.grid(row=0, column=1, sticky="e")

        nb = ttk.Notebook(self.root)
        nb.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 4))
        self._notebook = nb

        tab_paths = ttk.Frame(nb)
        tab_pipe = ttk.Frame(nb, padding=0)
        tab_filt = ttk.Frame(nb)
        tab_prev = ttk.Frame(nb)
        nb.add(tab_pipe, text=self.tr("tab.flow"))
        nb.add(tab_prev, text=self.tr("tab.preview"))
        nb.add(tab_paths, text=self.tr("tab.paths"))
        nb.add(tab_filt, text=self.tr("tab.filters"))

        paths_inner = self._create_xy_scroll_area(tab_paths)
        filt_inner = self._create_xy_scroll_area(tab_filt)
        prev_inner = self._create_xy_scroll_area(tab_prev)
        self._build_tab_paths(paths_inner)
        self._build_tab_pipeline(tab_pipe)
        self._build_tab_filters(filt_inner)
        prev_inner.columnconfigure(0, weight=1)
        prev_inner.rowconfigure(0, weight=1)
        self._video_preview = OxcoVideoPreview(prev_inner, host_app=self)
        self._video_preview.grid(row=0, column=0, sticky="nsew")

        log_fr = ttk.LabelFrame(self.root, text=self.tr("log.title"))
        log_fr.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._log_frame = log_fr
        log_fr.columnconfigure(0, weight=1)
        log_fr.rowconfigure(0, weight=1)
        self.log = tk.Text(log_fr, height=10, state="disabled", wrap="word", font=("Consolas", 10))
        self.log.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        sb = ttk.Scrollbar(log_fr, orient="vertical", command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=6)
        self.log.configure(yscrollcommand=sb.set)

    def _build_tab_paths(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        r = 0

        lf = ttk.LabelFrame(parent, text=self.tr("paths.compare_export"))
        lf.grid(row=r, column=0, sticky="ew", pady=(0, 8))
        lf.columnconfigure(1, weight=1, minsize=160)
        lf.columnconfigure(2, minsize=36)
        r += 1
        pl1 = ttk.Label(lf, text=self.tr("paths.compare_export_hint"))
        pl1.grid(row=0, column=0, sticky="nw", padx=6, pady=6)
        self._i18n_labeled.append((pl1, "paths.compare_export_hint"))
        ttk.Entry(lf, textvariable=self.var_compare_export).grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(lf, text="…", width=3, command=lambda: self._browse_dir(self.var_compare_export)).grid(
            row=0, column=2, padx=4, pady=6
        )

        lf2 = ttk.LabelFrame(parent, text=self.tr("paths.bitrate"))
        lf2.grid(row=r, column=0, sticky="ew", pady=(0, 8))
        lf2.columnconfigure(1, weight=1, minsize=160)
        lf2.columnconfigure(2, minsize=36)
        r += 1
        pl2 = ttk.Label(lf2, text=self.tr("paths.bitrate_in"))
        pl2.grid(row=0, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((pl2, "paths.bitrate_in"))
        ttk.Entry(lf2, textvariable=self.var_bitrate_in).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(lf2, text="…", width=3, command=lambda: self._browse_dir(self.var_bitrate_in)).grid(row=0, column=2, padx=4)
        pl3 = ttk.Label(lf2, text=self.tr("paths.bitrate_out"))
        pl3.grid(row=1, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((pl3, "paths.bitrate_out"))
        ttk.Entry(lf2, textvariable=self.var_bitrate_out).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(lf2, text="…", width=3, command=lambda: self._browse_dir(self.var_bitrate_out)).grid(row=1, column=2, padx=4)

        r += 1
        lf3 = ttk.LabelFrame(parent, text=self.tr("paths.tagger"))
        lf3.grid(row=r, column=0, sticky="ew")
        lf3.columnconfigure(1, weight=1, minsize=160)
        lf3.columnconfigure(2, minsize=36)
        pl4 = ttk.Label(lf3, text=self.tr("paths.tagger_in"))
        pl4.grid(row=0, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((pl4, "paths.tagger_in"))
        ttk.Entry(lf3, textvariable=self.var_tagger_in).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(lf3, text="…", width=3, command=lambda: self._browse_dir(self.var_tagger_in)).grid(row=0, column=2, padx=4)
        pl5 = ttk.Label(lf3, text=self.tr("paths.tagger_out"))
        pl5.grid(row=1, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((pl5, "paths.tagger_out"))
        ttk.Entry(lf3, textvariable=self.var_tagger_out).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(lf3, text="…", width=3, command=lambda: self._browse_dir(self.var_tagger_out)).grid(row=1, column=2, padx=4)
        self._paths_lfs = ((lf, "paths.compare_export"), (lf2, "paths.bitrate"), (lf3, "paths.tagger"))

    def _build_tab_pipeline(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)
        inner = ttk.Frame(canvas, padding=10)
        self._pipe_canvas = canvas
        self._pipe_inner = inner
        self._pipe_hsb = hsb
        self._pipe_win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", self._on_pipe_inner_configure)
        canvas.bind("<Configure>", self._on_pipe_canvas_configure)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        def _wheel(event: tk.Event) -> str:
            if (event.state & 0x0001) != 0:
                canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        canvas.bind("<MouseWheel>", _wheel)
        inner.bind("<MouseWheel>", _wheel)

        inner.columnconfigure(0, weight=1)
        row = 0

        c = ttk.LabelFrame(inner, text=self.tr("flow.step1"))
        c.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        c.columnconfigure(1, weight=1, minsize=100)
        c.columnconfigure(2, minsize=88)
        row += 1
        lab_o = ttk.Label(c, text=self.tr("flow.original"))
        lab_o.grid(row=0, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((lab_o, "flow.original"))
        ttk.Entry(c, textvariable=self.var_source).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self._btn_pipe_src = ttk.Button(c, text=self.tr("flow.file_btn"), command=self._browse_source)
        self._btn_pipe_src.grid(row=0, column=2, padx=4, pady=4, sticky="e")
        self._i18n_labeled.append((self._btn_pipe_src, "flow.file_btn"))
        lab_df = ttk.Label(c, text=self.tr("flow.deepfake"))
        lab_df.grid(row=1, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((lab_df, "flow.deepfake"))
        ttk.Entry(c, textvariable=self.var_deepfake).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        self._btn_pipe_df = ttk.Button(c, text=self.tr("flow.file_btn"), command=self._browse_df)
        self._btn_pipe_df.grid(row=1, column=2, padx=4, pady=4, sticky="e")
        self._i18n_labeled.append((self._btn_pipe_df, "flow.file_btn"))

        scan_fr = ttk.Frame(c)
        scan_fr.grid(row=2, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 2))
        scan_fr.columnconfigure(1, weight=1)
        scan_fr.columnconfigure(3, weight=1)
        cr = 0
        lab_csd = ttk.Label(scan_fr, text=self.tr("flow.compare_src_dir"))
        lab_csd.grid(row=cr, column=0, sticky="w", padx=(2, 4), pady=2)
        self._i18n_labeled.append((lab_csd, "flow.compare_src_dir"))
        ttk.Entry(scan_fr, textvariable=self.var_compare_source_dir).grid(
            row=cr, column=1, sticky="ew", padx=2, pady=2
        )
        ttk.Button(scan_fr, text="…", width=3, command=lambda: self._browse_dir(self.var_compare_source_dir)).grid(
            row=cr, column=2, padx=2, pady=2
        )
        lab_cdd = ttk.Label(scan_fr, text=self.tr("flow.compare_df_dir"))
        lab_cdd.grid(row=cr, column=3, sticky="w", padx=(8, 4), pady=2)
        self._i18n_labeled.append((lab_cdd, "flow.compare_df_dir"))
        ttk.Entry(scan_fr, textvariable=self.var_compare_deepfake_dir).grid(
            row=cr, column=4, sticky="ew", padx=2, pady=2
        )
        ttk.Button(scan_fr, text="…", width=3, command=lambda: self._browse_dir(self.var_compare_deepfake_dir)).grid(
            row=cr, column=5, padx=2, pady=2
        )
        cr += 1
        scan_tool = ttk.Frame(scan_fr)
        scan_tool.grid(row=cr, column=0, columnspan=6, sticky="ew", pady=(4, 2))
        self._chk_compare_recursive = ttk.Checkbutton(
            scan_tool, text=self.tr("flow.compare_recursive"), variable=self.var_compare_recursive
        )
        self._chk_compare_recursive.pack(side="left", padx=(0, 8))
        self.btn_compare_load = ttk.Button(
            scan_tool, text=self.tr("flow.compare_load_lists"), command=self._compare_scan_lists
        )
        self.btn_compare_load.pack(side="left", padx=(0, 8))
        lab_sort = ttk.Label(scan_tool, text=self.tr("flow.compare_sort"))
        lab_sort.pack(side="left", padx=(0, 4))
        self._i18n_labeled.append((lab_sort, "flow.compare_sort"))
        self._compare_sort_values = (
            "date_desc",
            "date_asc",
            "duration_desc",
            "duration_asc",
            "size_desc",
            "size_asc",
            "name_asc",
            "name_desc",
        )
        self._compare_sort_labels = [self.tr(f"flow.compare_sort.{k}") for k in self._compare_sort_values]
        self._cb_compare_sort = ttk.Combobox(
            scan_tool,
            values=self._compare_sort_labels,
            width=22,
            state="readonly",
        )
        self._cb_compare_sort.pack(side="left", padx=(0, 8))
        self._cb_compare_sort.bind("<<ComboboxSelected>>", lambda _e: self._compare_on_sort_group_change())
        self._sync_compare_sort_combo_from_var()
        lab_grp = ttk.Label(scan_tool, text=self.tr("flow.compare_group"))
        lab_grp.pack(side="left", padx=(0, 4))
        self._i18n_labeled.append((lab_grp, "flow.compare_group"))
        self._compare_group_values = ("none", "folder", "date", "duration", "letter")
        self._compare_group_labels = [self.tr(f"flow.compare_group.{k}") for k in self._compare_group_values]
        self._cb_compare_group = ttk.Combobox(
            scan_tool,
            values=self._compare_group_labels,
            width=16,
            state="readonly",
        )
        self._cb_compare_group.pack(side="left")
        self._cb_compare_group.bind("<<ComboboxSelected>>", lambda _e: self._compare_on_sort_group_change())
        self._sync_compare_group_combo_from_var()

        dual_fr = ttk.Frame(c)
        dual_fr.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=4, pady=4)
        c.rowconfigure(3, weight=1)
        dual_fr.columnconfigure(0, weight=1)
        dual_fr.columnconfigure(1, weight=1)
        dual_fr.rowconfigure(1, weight=1)
        lab_lo = ttk.Label(dual_fr, text=self.tr("flow.original"))
        lab_lo.grid(row=0, column=0, sticky="w", padx=2)
        lab_ld = ttk.Label(dual_fr, text=self.tr("flow.deepfake"))
        lab_ld.grid(row=0, column=1, sticky="w", padx=2)
        cmp_cols = ("name", "rel", "duration", "res", "size", "mtime")
        left_wrap = ttk.Frame(dual_fr)
        left_wrap.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        left_wrap.columnconfigure(0, weight=1)
        left_wrap.rowconfigure(0, weight=1)
        self.tree_compare_orig = ttk.Treeview(
            left_wrap, columns=cmp_cols, show="tree headings", height=8, selectmode="browse"
        )
        self.tree_compare_orig.grid(row=0, column=0, sticky="nsew")
        osb = ttk.Scrollbar(left_wrap, orient="vertical", command=self.tree_compare_orig.yview)
        osb.grid(row=0, column=1, sticky="ns")
        self.tree_compare_orig.configure(yscrollcommand=osb.set)
        right_wrap = ttk.Frame(dual_fr)
        right_wrap.grid(row=1, column=1, sticky="nsew", padx=(4, 0))
        right_wrap.columnconfigure(0, weight=1)
        right_wrap.rowconfigure(0, weight=1)
        self.tree_compare_df = ttk.Treeview(
            right_wrap, columns=cmp_cols, show="tree headings", height=8, selectmode="extended"
        )
        self.tree_compare_df.grid(row=0, column=0, sticky="nsew")
        dsb = ttk.Scrollbar(right_wrap, orient="vertical", command=self.tree_compare_df.yview)
        dsb.grid(row=0, column=1, sticky="ns")
        self.tree_compare_df.configure(yscrollcommand=dsb.set)
        self._compare_setup_tree_columns(self.tree_compare_orig)
        self._compare_setup_tree_columns(self.tree_compare_df)
        self._compare_configure_tree_tags(self.tree_compare_orig)
        self._compare_configure_tree_tags(self.tree_compare_df)
        self.tree_compare_orig.bind("<<TreeviewSelect>>", self._compare_on_orig_select)
        self.tree_compare_orig.bind("<ButtonRelease-1>", self._compare_on_orig_select)
        self.tree_compare_df.bind("<<TreeviewSelect>>", self._compare_on_df_select)
        hint_color = ttk.Label(c, text=self.tr("flow.compare_color_hint"), foreground="gray", wraplength=640)
        hint_color.grid(row=4, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 2))
        self._i18n_labeled.append((hint_color, "flow.compare_color_hint"))
        hint_batch = ttk.Label(c, text=self.tr("flow.compare_batch_hint"), foreground="gray", wraplength=640)
        hint_batch.grid(row=5, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 2))
        self._i18n_labeled.append((hint_batch, "flow.compare_batch_hint"))

        cf = ttk.Frame(c)
        cf.grid(row=6, column=0, columnspan=3, padx=6, pady=8, sticky="w")
        self.btn_compare = ttk.Button(cf, text=self.tr("flow.run_compare"), command=self._run_compare)
        self.btn_compare.pack(side="left", padx=(0, 6))
        self.btn_compare_stop = ttk.Button(
            cf, text=self.tr("flow.compare_stop"), command=self._compare_stop, state="disabled"
        )
        self.btn_compare_stop.pack(side="left", padx=(0, 6))
        self.btn_compare_retry = ttk.Button(
            cf, text=self.tr("flow.compare_retry"), command=self._retry_compare, state="disabled"
        )
        self.btn_compare_retry.pack(side="left", padx=(0, 6))
        self.btn_compare_batch = ttk.Button(
            cf, text=self.tr("flow.compare_run_batch"), command=self._run_compare_batch
        )
        self.btn_compare_batch.pack(side="left")

        thr_row = ttk.Frame(c)
        thr_row.grid(row=7, column=0, columnspan=3, sticky="ew", padx=6, pady=(0, 6))
        thr_row.columnconfigure(2, weight=1)
        fl_pm_flow = ttk.Label(thr_row, text=self.tr("filters.pixel_max"))
        fl_pm_flow.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._i18n_labeled.append((fl_pm_flow, "filters.pixel_max"))
        ttk.Entry(thr_row, textvariable=self.var_pixel_max, width=12).grid(row=0, column=1, sticky="w")
        hint_more = ttk.Label(thr_row, text=self.tr("flow.compare_more_filters"), foreground="gray")
        hint_more.grid(row=0, column=2, sticky="w", padx=(12, 0))
        self._i18n_labeled.append((hint_more, "flow.compare_more_filters"))

        b = ttk.LabelFrame(inner, text=self.tr("flow.step2"))
        b.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        b.columnconfigure(0, weight=1)
        row += 1
        tree_fr = ttk.Frame(b)
        tree_fr.grid(row=0, column=0, sticky="nsew", pady=4)
        tree_fr.columnconfigure(0, weight=1)
        cols = ("datei", "wh", "src_k", "ziel_k", "aktion")
        self.tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=8, selectmode="extended")
        self._refresh_tree_headings()
        self.tree.column("datei", width=360, minwidth=80)
        self.tree.column("wh", width=90, minwidth=60)
        self.tree.column("src_k", width=80, minwidth=50)
        self.tree.column("ziel_k", width=80, minwidth=50)
        self.tree.column("aktion", width=100, minwidth=70)
        self.tree.grid(row=0, column=0, sticky="nsew")
        tsb = ttk.Scrollbar(tree_fr, orient="vertical", command=self.tree.yview)
        tsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tsb.set)
        self.tree.bind("<Button-3>", self._bitrate_tree_context_menu)

        bf = ttk.Frame(b)
        bf.grid(row=1, column=0, sticky="ew", pady=4)
        for col in range(3):
            bf.columnconfigure(col, weight=0, minsize=1)
        self.btn_scan = ttk.Button(bf, text=self.tr("flow.scan"), command=self._bitrate_scan)
        self.btn_scan.grid(row=0, column=0, padx=(0, 6), pady=2, sticky="w")
        self.btn_conv = ttk.Button(bf, text=self.tr("flow.convert"), command=self._bitrate_convert)
        self.btn_conv.grid(row=0, column=1, padx=(0, 6), pady=2, sticky="w")
        self.btn_stop_br = ttk.Button(bf, text=self.tr("flow.stop"), command=self._bitrate_stop_click, state="disabled")
        self.btn_stop_br.grid(row=0, column=2, padx=(0, 6), pady=2, sticky="w")

        t = ttk.LabelFrame(inner, text=self.tr("flow.step3"))
        t.grid(row=row, column=0, sticky="ew")
        t.columnconfigure(1, weight=1, minsize=80)
        t.columnconfigure(2, minsize=28)
        tr = 0
        lab_tag = ttk.Label(t, text=self.tr("flow.tag"))
        lab_tag.grid(row=tr, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((lab_tag, "flow.tag"))
        self.cmb_tag = ttk.Combobox(t, textvariable=self.var_tag, values=self._tag_route_tag_choices())
        self.cmb_tag.grid(row=tr, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(t, text="(i)", width=3, command=self._help_tag_text).grid(row=tr, column=2, padx=4, pady=4)
        tr += 1
        lab_prof = ttk.Label(t, text=self.tr("flow.profile"))
        lab_prof.grid(row=tr, column=0, sticky="nw", padx=6, pady=4)
        self._i18n_labeled.append((lab_prof, "flow.profile"))
        ttk.Entry(t, textvariable=self.var_tag_profile).grid(row=tr, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(t, text="(i)", width=3, command=self._help_profile_name).grid(row=tr, column=2, padx=4, pady=4)
        tr += 1
        tgf = ttk.Frame(t)
        tgf.grid(row=tr, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 0))
        tgf.columnconfigure(0, weight=1)
        self.btn_tagger_refresh = ttk.Button(
            tgf, text=self.tr("flow.tagger_refresh"), command=lambda: self._tagger_refresh_list(log_count=True)
        )
        self.btn_tagger_refresh.pack(side="right", padx=(8, 6), pady=2)
        tr += 1
        tag_tree_fr = ttk.Frame(t)
        tag_tree_fr.grid(row=tr, column=0, columnspan=3, sticky="nsew", padx=4, pady=4)
        tag_tree_fr.columnconfigure(0, weight=1)
        tag_tree_fr.columnconfigure(1, weight=0)
        tag_tree_fr.rowconfigure(0, weight=1)
        t.rowconfigure(tr, weight=1)
        self.tree_tagger = ttk.Treeview(
            tag_tree_fr, columns=("tf",), show="headings", height=6, selectmode="extended"
        )
        self.tree_tagger.column("tf", width=380, minwidth=120)
        self.tree_tagger.grid(row=0, column=0, sticky="nsew")
        ttsb = ttk.Scrollbar(tag_tree_fr, orient="vertical", command=self.tree_tagger.yview)
        ttsb.grid(row=0, column=1, sticky="ns")
        self.tree_tagger.configure(yscrollcommand=ttsb.set)
        self.tree_tagger.heading("tf", text=self.tr("flow.tagger_tree_file"))
        self.tree_tagger.bind("<<TreeviewSelect>>", self._on_tagger_tree_select)
        self._tagger_preview = OxcoTaggerPreview(tag_tree_fr, host_app=self)
        self._tagger_preview.grid(row=0, column=2, rowspan=1, sticky="n", padx=(8, 0))
        tr += 1
        hint_tg = ttk.Label(t, text=self.tr("flow.tagger_hint"), foreground="gray", wraplength=640)
        hint_tg.grid(row=tr, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))
        self._i18n_labeled.append((hint_tg, "flow.tagger_hint"))
        tr += 1
        self.btn_tagger = ttk.Button(t, text=self.tr("flow.process"), command=self._run_tagger)
        self.btn_tagger.grid(row=tr, column=0, columnspan=3, padx=6, pady=(8, 4), sticky="w")
        tr += 1
        trf = ttk.Frame(t)
        trf.grid(row=tr, column=0, columnspan=3, sticky="ew", padx=6, pady=(0, 8))
        self.btn_tag_route_setup = ttk.Button(trf, text=self.tr("flow.tag_route_setup"), command=self._open_tag_route_dialog)
        self.btn_tag_route_setup.pack(side="left", padx=(0, 6))
        ttk.Button(trf, text="(i)", width=3, command=self._help_tag_route).pack(side="left", padx=(0, 8))
        self._chk_tagger_route_auto = ttk.Checkbutton(
            trf, text=self.tr("flow.tag_route_auto"), variable=self.var_tagger_route_auto
        )
        self._chk_tagger_route_auto.pack(side="left", padx=(0, 8))
        self.btn_tag_route_distribute = ttk.Button(
            trf, text=self.tr("flow.tag_route_distribute"), command=self._run_tag_distribute
        )
        self.btn_tag_route_distribute.pack(side="left")

        self._pipe_lfs = ((c, "flow.step1"), (b, "flow.step2"), (t, "flow.step3"))
        self._pipe_btns = (
            (self.btn_compare, "flow.run_compare"),
            (self.btn_compare_stop, "flow.compare_stop"),
            (self.btn_compare_retry, "flow.compare_retry"),
            (self.btn_compare_batch, "flow.compare_run_batch"),
            (self.btn_compare_load, "flow.compare_load_lists"),
            (self.btn_scan, "flow.scan"),
            (self.btn_conv, "flow.convert"),
            (self.btn_stop_br, "flow.stop"),
            (self.btn_tagger_refresh, "flow.tagger_refresh"),
            (self.btn_tagger, "flow.process"),
            (self.btn_tag_route_setup, "flow.tag_route_setup"),
            (self.btn_tag_route_distribute, "flow.tag_route_distribute"),
        )
        inner.after(1, self._sync_pipe_canvas)

    def _on_pipe_inner_configure(self, event: tk.Event) -> None:
        self._sync_pipe_canvas()

    def _on_pipe_canvas_configure(self, event: tk.Event) -> None:
        if event.widget != self._pipe_canvas:
            return
        self._sync_pipe_canvas()

    def _sync_pipe_canvas(self) -> None:
        if self._pipe_canvas is None or self._pipe_win_id is None:
            return
        c = self._pipe_canvas
        c.update_idletasks()
        self._pipe_inner.update_idletasks()
        cw = max(int(c.winfo_width()), 4)
        ch = max(int(c.winfo_height()), 4)
        iw = max(int(self._pipe_inner.winfo_reqwidth()), cw)
        ih = max(int(self._pipe_inner.winfo_reqheight()), ch)
        c.itemconfig(self._pipe_win_id, width=iw, height=ih)
        bb = c.bbox("all")
        if bb:
            c.configure(scrollregion=bb)

    def _build_tab_filters(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        row = 0

        f1 = ttk.LabelFrame(parent, text=self.tr("filters.group_compare"))
        f1.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        f1.columnconfigure(1, weight=0)
        f1.columnconfigure(2, minsize=28)
        row += 1
        r = 0
        self._lbl_filters_lang_note = ttk.Label(f1, text=self.tr("filters.lang_note"), foreground="gray")
        self._lbl_filters_lang_note.grid(row=r, column=0, columnspan=3, sticky="w", padx=6, pady=(2, 6))
        r += 1
        fl_buf = ttk.Label(f1, text=self.tr("filters.buffer"))
        fl_buf.grid(row=r, column=0, sticky="w", padx=6, pady=2)
        self._i18n_labeled.append((fl_buf, "filters.buffer"))
        ttk.Entry(f1, textvariable=self.var_buffer, width=14).grid(row=r, column=1, sticky="w", padx=4)
        ttk.Button(f1, text="(i)", width=3, command=self._help_compare_thresholds).grid(
            row=r, column=2, rowspan=5, sticky="ne", padx=4, pady=2
        )
        r += 1
        fl_noise = ttk.Label(f1, text=self.tr("filters.noise"))
        fl_noise.grid(row=r, column=0, sticky="w", padx=6, pady=2)
        self._i18n_labeled.append((fl_noise, "filters.noise"))
        ttk.Entry(f1, textvariable=self.var_noise, width=14).grid(row=r, column=1, sticky="w", padx=4)
        r += 1
        fl_pix = ttk.Label(f1, text=self.tr("filters.pixel"))
        fl_pix.grid(row=r, column=0, sticky="w", padx=6, pady=2)
        self._i18n_labeled.append((fl_pix, "filters.pixel"))
        ttk.Entry(f1, textvariable=self.var_pixel, width=14).grid(row=r, column=1, sticky="w", padx=4)
        r += 1
        fl_pix_max = ttk.Label(f1, text=self.tr("filters.pixel_max"))
        fl_pix_max.grid(row=r, column=0, sticky="w", padx=6, pady=2)
        self._i18n_labeled.append((fl_pix_max, "filters.pixel_max"))
        ttk.Entry(f1, textvariable=self.var_pixel_max, width=14).grid(row=r, column=1, sticky="w", padx=4)
        r += 1
        fl_dvt = ttk.Label(f1, text=self.tr("filters.davinci_timeout"))
        fl_dvt.grid(row=r, column=0, sticky="w", padx=6, pady=2)
        self._i18n_labeled.append((fl_dvt, "filters.davinci_timeout"))
        ttk.Entry(f1, textvariable=self.var_davinci_timeout, width=14).grid(row=r, column=1, sticky="w", padx=4)
        r += 1
        self._chk_ffmpeg = ttk.Checkbutton(f1, text=self.tr("filters.ffmpeg_on"), variable=self.var_ffmpeg)
        self._chk_ffmpeg.grid(row=r, column=0, columnspan=2, sticky="w", padx=6)
        ttk.Button(f1, text="(i)", width=3, command=self._help_compare_export).grid(row=r, column=2, sticky="ne", padx=4, pady=2)
        r += 1
        self._chk_davinci = ttk.Checkbutton(f1, text=self.tr("filters.davinci_on"), variable=self.var_davinci)
        self._chk_davinci.grid(row=r, column=0, columnspan=2, sticky="w", padx=6)
        r += 1
        fl_ff = ttk.Label(f1, text=self.tr("filters.ffmpeg_renders"))
        fl_ff.grid(row=r, column=0, sticky="w", padx=6)
        self._i18n_labeled.append((fl_ff, "filters.ffmpeg_renders"))
        ttk.Combobox(
            f1,
            textvariable=self.var_ffmpeg_target,
            values=("both", "source", "deepfake"),
            width=12,
            state="readonly",
        ).grid(row=r, column=1, sticky="w")
        r += 1
        self._chk_export_unique = ttk.Checkbutton(
            f1, text=self.tr("filters.export_unique"), variable=self.var_export_unique
        )
        self._chk_export_unique.grid(row=r, column=0, columnspan=2, sticky="w", padx=6)

        f2 = ttk.LabelFrame(parent, text=self.tr("filters.br_group"))
        f2.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        f2.columnconfigure(2, minsize=28)
        row += 1
        pr = ttk.Frame(f2)
        pr.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=4)
        fl_preset = ttk.Label(pr, text=self.tr("filters.preset"))
        fl_preset.pack(side="left")
        self._i18n_labeled.append((fl_preset, "filters.preset"))
        presets = list(ow.BUILTIN_PRESETS.keys())
        cb = ttk.Combobox(pr, textvariable=self.var_br_preset, values=presets, width=18, state="readonly")
        cb.pack(side="left", padx=8)
        self._btn_br_preset = ttk.Button(pr, text=self.tr("filters.apply_preset"), command=self._apply_br_preset)
        self._btn_br_preset.pack(side="left", padx=(0, 8))
        ttk.Button(pr, text="(i)", width=3, command=self._help_bitrate_rules).pack(side="left")
        gf = ttk.Frame(f2)
        gf.grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=4)
        for i, th in enumerate(ow.RULE_ORDER):
            ttk.Label(gf, text=f"≥{th}px").grid(row=i // 3, column=(i % 3) * 2, padx=4, pady=2, sticky="e")
            ttk.Entry(gf, textvariable=self._br_rule_vars[th], width=8).grid(row=i // 3, column=(i % 3) * 2 + 1, padx=4, pady=2)

        self._chk_br_sub = ttk.Checkbutton(f2, text=self.tr("filters.subfolders"), variable=self.var_br_recursive)
        self._chk_br_sub.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=2)
        self._chk_br_lower = ttk.Checkbutton(f2, text=self.tr("filters.only_lower"), variable=self.var_br_only_lower)
        self._chk_br_lower.grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=2)
        sfx_fr = ttk.Frame(f2)
        sfx_fr.grid(row=4, column=0, columnspan=3, sticky="ew", padx=6, pady=2)
        sfx_fr.columnconfigure(1, weight=0)
        fl_sfx = ttk.Label(sfx_fr, text=self.tr("filters.suffix_out"))
        fl_sfx.grid(row=0, column=0, sticky="w")
        self._i18n_labeled.append((fl_sfx, "filters.suffix_out"))
        ttk.Entry(sfx_fr, textvariable=self.var_br_suffix, width=18).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Button(sfx_fr, text="(i)", width=3, command=self._help_bitrate_suffix).grid(row=0, column=2, padx=4)
        self._chk_br_mp4 = ttk.Checkbutton(f2, text=self.tr("filters.mp4"), variable=self.var_br_mp4)
        self._chk_br_mp4.grid(row=5, column=0, columnspan=3, sticky="w", padx=6)
        self._chk_br_delete_src = ttk.Checkbutton(
            f2, text=self.tr("filters.br_delete_source"), variable=self.var_br_delete_source
        )
        self._chk_br_delete_src.grid(row=6, column=0, columnspan=3, sticky="w", padx=6)
        fl_codec = ttk.Label(f2, text=self.tr("filters.codec"))
        fl_codec.grid(row=7, column=0, sticky="w", padx=6)
        self._i18n_labeled.append((fl_codec, "filters.codec"))
        ttk.Combobox(
            f2,
            textvariable=self.var_br_codec,
            values=("libx264", "libx265", "h264_nvenc", "hevc_nvenc"),
            width=14,
            state="readonly",
        ).grid(row=7, column=1, sticky="w", padx=4)
        fl_audio = ttk.Label(f2, text=self.tr("filters.audio"))
        fl_audio.grid(row=8, column=0, sticky="w", padx=6)
        self._i18n_labeled.append((fl_audio, "filters.audio"))
        ttk.Combobox(
            f2, textvariable=self.var_br_audio, values=("copy", "aac_128k"), width=12, state="readonly"
        ).grid(row=8, column=1, sticky="w", padx=4)

        f3 = ttk.LabelFrame(parent, text=self.tr("filters.tag_group"))
        f3.grid(row=row, column=0, sticky="ew")
        f3.columnconfigure(1, weight=0)
        f3.columnconfigure(2, minsize=28)
        self._tagger_labels: list[tuple[ttk.Label, str]] = []
        rr = 0
        for key, var, help_cmd in (
            ("filters.keep", self.var_keep, self._help_suffix_keep),
            ("filters.ignore", self.var_ignore, self._help_suffix_ignore),
            ("filters.drop", self.var_drop, self._help_suffix_drop),
            ("filters.pattern", self.var_pattern, self._help_pattern),
        ):
            lb = ttk.Label(f3, text=self.tr(key))
            self._tagger_labels.append((lb, key))
            lb.grid(row=rr, column=0, sticky="nw", padx=6, pady=4)
            ttk.Entry(f3, textvariable=var, width=52).grid(row=rr, column=1, sticky="w", padx=4, pady=4)
            ttk.Button(f3, text="(i)", width=3, command=help_cmd).grid(row=rr, column=2, padx=4, pady=4)
            rr += 1

        self._filters_lfs = ((f1, "filters.group_compare"), (f2, "filters.br_group"), (f3, "filters.tag_group"))

    def _help_compare_thresholds(self) -> None:
        messagebox.showinfo(self.tr("help.thresholds.title"), self.tr("help.thresholds.body"))

    def _help_compare_export(self) -> None:
        messagebox.showinfo(self.tr("help.export.title"), self.tr("help.export.body"))

    def _help_bitrate_rules(self) -> None:
        messagebox.showinfo(self.tr("help.bitrate.title"), self.tr("help.bitrate.body"))

    def _help_bitrate_suffix(self) -> None:
        messagebox.showinfo(self.tr("help.suffix.title"), self.tr("help.suffix.body"))

    def _help_suffix_keep(self) -> None:
        messagebox.showinfo(self.tr("help.keep.title"), self.tr("help.keep.body"))

    def _help_suffix_ignore(self) -> None:
        messagebox.showinfo(self.tr("help.ignore.title"), self.tr("help.ignore.body"))

    def _help_suffix_drop(self) -> None:
        messagebox.showinfo(self.tr("help.drop.title"), self.tr("help.drop.body"))

    def _help_tag_route(self) -> None:
        messagebox.showinfo(self.tr("help.tag_route.title"), self.tr("help.tag_route.body"))

    @staticmethod
    def _parse_tag_route_rules_cfg(raw: object) -> List[Dict[str, str]]:
        return [{"tag": t, "folder": f} for t, f in ow.normalize_tag_route_rules(raw)]

    def _tag_route_rules_as_tuples(self) -> List[tuple[str, str]]:
        return [(str(r.get("tag", "")).strip(), str(r.get("folder", "")).strip()) for r in self._tag_route_rules]

    def _tag_route_tag_choices(self) -> List[str]:
        """Eindeutige Tags aus Tag-Verteilung (+ aktueller Wert) für die Combobox."""
        seen: Set[str] = set()
        out: List[str] = []
        for rule in self._tag_route_rules:
            tag = str(rule.get("tag") or "").strip()
            key = tag.casefold()
            if tag and key not in seen:
                seen.add(key)
                out.append(tag)
        cur = self.var_tag.get().strip()
        if cur and cur.casefold() not in seen:
            out.insert(0, cur)
        return out

    def _refresh_tag_combobox_values(self) -> None:
        if getattr(self, "cmb_tag", None) is None:
            return
        self.cmb_tag["values"] = self._tag_route_tag_choices()

    def _open_tag_route_dialog(self) -> None:
        if self._tag_route_win is not None and self._tag_route_win.winfo_exists():
            self._tag_route_win.lift()
            return
        win = tk.Toplevel(self.root)
        self._tag_route_win = win
        win.title(self.tr("flow.tag_route_title"))
        win.transient(self.root)
        win.grab_set()
        win.geometry("640x380")
        outer = ttk.Frame(win, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        hdr = ttk.Frame(outer)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(hdr, text=self.tr("flow.tag_route_col_tag")).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(hdr, text=self.tr("flow.tag_route_col_folder")).grid(row=0, column=1, sticky="w")

        scroll_host = ttk.Frame(outer)
        scroll_host.grid(row=1, column=0, sticky="nsew")
        scroll_host.columnconfigure(0, weight=1)
        scroll_host.rowconfigure(0, weight=1)
        canvas = tk.Canvas(scroll_host, highlightthickness=0, height=220)
        vsb = ttk.Scrollbar(scroll_host, orient="vertical", command=canvas.yview)
        rows_fr = ttk.Frame(canvas)
        rows_win = canvas.create_window((0, 0), window=rows_fr, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        def sync_scroll(_evt: Optional[tk.Event] = None) -> None:
            canvas.update_idletasks()
            rows_fr.update_idletasks()
            cw = max(int(canvas.winfo_width()), 1)
            canvas.itemconfig(rows_win, width=cw)
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)

        rows_fr.bind("<Configure>", lambda e: sync_scroll())
        canvas.bind("<Configure>", lambda e: sync_scroll() if e.widget == canvas else None)

        self._tag_route_row_vars = []

        def add_row(tag: str = "", folder: str = "") -> None:
            v_tag = tk.StringVar(value=tag)
            v_folder = tk.StringVar(value=folder)
            self._tag_route_row_vars.append((v_tag, v_folder))
            ri = len(self._tag_route_row_vars) - 1
            row_fr = ttk.Frame(rows_fr)
            row_fr.grid(row=ri, column=0, sticky="ew", pady=2)
            row_fr.columnconfigure(1, weight=1)
            ttk.Entry(row_fr, textvariable=v_tag, width=18).grid(row=0, column=0, sticky="w", padx=(0, 6))
            ent_f = ttk.Entry(row_fr, textvariable=v_folder)
            ent_f.grid(row=0, column=1, sticky="ew", padx=(0, 4))
            ttk.Button(
                row_fr,
                text="…",
                width=3,
                command=lambda v=v_folder: self._browse_dir_to_var(v),
            ).grid(row=0, column=2, padx=(0, 4))

            def remove_row() -> None:
                try:
                    self._tag_route_row_vars.remove((v_tag, v_folder))
                except ValueError:
                    pass
                row_fr.destroy()
                sync_scroll()

            ttk.Button(row_fr, text=self.tr("flow.tag_route_remove"), command=remove_row).grid(
                row=0, column=3, padx=(0, 0)
            )
            sync_scroll()

        for rule in self._tag_route_rules:
            add_row(str(rule.get("tag", "")), str(rule.get("folder", "")))
        if not self._tag_route_rules:
            add_row()

        btn_fr = ttk.Frame(outer)
        btn_fr.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        def save_close() -> None:
            collected: List[Dict[str, str]] = []
            for v_tag, v_folder in self._tag_route_row_vars:
                tag = v_tag.get().strip()
                folder = v_folder.get().strip()
                if tag and folder:
                    collected.append({"tag": tag, "folder": folder})
            self._tag_route_rules = collected
            self._refresh_tag_combobox_values()
            self._save()
            win.destroy()
            self._tag_route_win = None
            self._tag_route_row_vars = []

        def cancel() -> None:
            win.destroy()
            self._tag_route_win = None
            self._tag_route_row_vars = []

        ttk.Button(btn_fr, text=self.tr("flow.tag_route_add"), command=lambda: add_row()).pack(side="left", padx=(0, 8))
        ttk.Button(btn_fr, text=self.tr("flow.tag_route_save"), command=save_close).pack(side="left", padx=(0, 8))
        ttk.Button(btn_fr, text=self.tr("settings.cancel"), command=cancel).pack(side="left")
        sync_scroll()
        win.update_idletasks()
        self._place_settings_window(win)

    def _run_tag_distribute(self) -> None:
        if self._tag_route_busy:
            return
        outp = self.var_tagger_out.get().strip()
        if not outp:
            messagebox.showerror(self.tr("err.input"), self.tr("err.tagger_folders"))
            return
        rules = self._tag_route_rules_as_tuples()
        if not rules:
            messagebox.showerror(self.tr("err.input"), self.tr("err.tag_route_no_rules"))
            return
        src = Path(outp)
        if not src.is_dir():
            messagebox.showerror(self.tr("err.input"), self.tr("err.tag_route_out_missing"))
            return

        lang = (self.var_ui_lang.get().strip() or "de").lower()
        if lang not in ("de", "en"):
            lang = "de"

        def log(s: str) -> None:
            self.root.after(0, lambda m=s: self._log(m))

        self._tag_route_busy = True
        self.btn_tag_route_distribute.configure(state="disabled")

        def work() -> None:
            self.root.after(0, lambda: self._log(self.tr("log.tag_route_start")))
            moved, nomatch, err = ow.tagger_distribute_by_rules(src, rules, log=log, ui_lang=lang)
            self.root.after(0, lambda: self._tag_distribute_done(moved, nomatch, err))

        threading.Thread(target=work, daemon=True).start()

    def _tag_distribute_done(self, moved: int, nomatch: int, err: int) -> None:
        self._tag_route_busy = False
        self.btn_tag_route_distribute.configure(state="normal")
        self._log(self.tr("log.tag_route_done", moved=moved, nomatch=nomatch, err=err))
        self._save()

    def _maybe_auto_tag_distribute(self) -> None:
        if not self.var_tagger_route_auto.get():
            return
        if not self._tag_route_rules_as_tuples():
            return
        if not self.var_tagger_out.get().strip():
            return
        self._run_tag_distribute()

    def _help_pattern(self) -> None:
        messagebox.showinfo(self.tr("help.pattern.title"), self.tr("help.pattern.body"))

    def _help_tag_text(self) -> None:
        messagebox.showinfo(self.tr("help.tag.title"), self.tr("help.tag.body"))

    def _help_profile_name(self) -> None:
        messagebox.showinfo(self.tr("help.profile.title"), self.tr("help.profile.body"))

    def _apply_br_preset(self) -> None:
        name = self.var_br_preset.get().strip()
        preset = ow.BUILTIN_PRESETS.get(name)
        if not preset:
            return
        for t in ow.RULE_ORDER:
            self._br_rule_vars[t].set(str(preset[t]))

    def _browse_dir(self, var: tk.StringVar) -> None:
        p = filedialog.askdirectory(title=self.tr("dlg.folder"))
        if p:
            var.set(p)

    def _browse_source(self) -> None:
        p = filedialog.askopenfilename(
            title=self.tr("dlg.video_orig"), filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi")]
        )
        if p:
            self.var_source.set(p)

    def _browse_df(self) -> None:
        p = filedialog.askopenfilename(
            title=self.tr("dlg.video_df"), filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi")]
        )
        if p:
            self.var_deepfake.set(p)

    def _log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _gather_cfg(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "window_geometry": self.root.geometry(),
            "compare_export_dir": self.var_compare_export.get().strip(),
            "bitrate_in_dir": self.var_bitrate_in.get().strip(),
            "bitrate_out_dir": self.var_bitrate_out.get().strip(),
            "tagger_in_dir": self.var_tagger_in.get().strip(),
            "tagger_out_dir": self.var_tagger_out.get().strip(),
            "last_source": self.var_source.get().strip(),
            "last_deepfake": self.var_deepfake.get().strip(),
            "ui_language": self.var_ui_lang.get().strip(),
            "davinci_api_path": self.var_davinci_api.get().strip(),
            "davinci_render_preset": self.var_davinci_preset.get().strip(),
            "davinci_exe_path": self.var_davinci_exe.get().strip(),
            "davinci_startup_wait_seconds": self.var_davinci_startup_wait.get().strip(),
            "filter_buffer": self.var_buffer.get().strip(),
            "filter_noise": self.var_noise.get().strip(),
            "filter_pixel": self.var_pixel.get().strip(),
            "filter_pixel_max": self.var_pixel_max.get().strip(),
            "filter_ffmpeg": self.var_ffmpeg.get(),
            "filter_davinci": self.var_davinci.get(),
            "filter_ffmpeg_target": self.var_ffmpeg_target.get().strip(),
            "filter_davinci_timeout": self.var_davinci_timeout.get().strip(),
            "filter_export_unique": self.var_export_unique.get(),
            "br_recursive": self.var_br_recursive.get(),
            "br_only_lower": self.var_br_only_lower.get(),
            "br_suffix": self.var_br_suffix.get().strip(),
            "br_output_mp4": self.var_br_mp4.get(),
            "br_codec": self.var_br_codec.get().strip(),
            "br_audio": self.var_br_audio.get().strip(),
            "br_delete_source_after_ok": self.var_br_delete_source.get(),
            "br_preset": self.var_br_preset.get().strip(),
            "tagger_tag": self.var_tag.get().strip(),
            "tagger_profile_name": self.var_tag_profile.get().strip(),
            "tagger_keep": self.var_keep.get(),
            "tagger_ignore": self.var_ignore.get(),
            "tagger_drop": self.var_drop.get(),
            "tagger_pattern": self.var_pattern.get().strip(),
            "tagger_route_auto": self.var_tagger_route_auto.get(),
            "tagger_route_rules": list(self._tag_route_rules),
            "compare_source_dir": self.var_compare_source_dir.get().strip(),
            "compare_deepfake_dir": self.var_compare_deepfake_dir.get().strip(),
            "compare_recursive": self.var_compare_recursive.get(),
            "compare_sort": self.var_compare_sort.get().strip() or "date_desc",
            "compare_group": self.var_compare_group.get().strip() or "folder",
        }
        for t in ow.RULE_ORDER:
            d[f"br_rule_{t}"] = self._br_rule_vars[t].get().strip()
        return d

    def _save(self) -> None:
        save_config(self._gather_cfg())

    def _on_close(self) -> None:
        if self._video_preview is not None:
            self._video_preview.shutdown()
        if self._tagger_preview is not None:
            self._tagger_preview.shutdown()
        self._save()
        self.root.destroy()

    def _on_configure(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        if self._geom_timer:
            self.root.after_cancel(self._geom_timer)
        self._geom_timer = self.root.after(500, self._flush_geom)

    def _flush_geom(self) -> None:
        self._geom_timer = None
        self._save()

    def _parse_rules(self) -> Optional[Dict[int, int]]:
        rules: Dict[int, int] = {}
        for t in ow.RULE_ORDER:
            raw = self._br_rule_vars[t].get().strip()
            if not raw:
                messagebox.showerror(self.tr("err.input"), self.tr("err.br_rule", h=t))
                return None
            try:
                v = int(raw)
            except ValueError:
                messagebox.showerror(self.tr("err.input"), self.tr("err.br_rule_num", h=t, raw=raw))
                return None
            if v <= 0:
                messagebox.showerror(self.tr("err.input"), self.tr("err.br_rule_pos", h=t))
                return None
            rules[t] = v
        return rules

    def _fmt_file_size(self, nbytes: int) -> str:
        n = int(nbytes)
        if n >= 1024**3:
            return f"{n / 1024**3:.1f} GB"
        if n >= 1024**2:
            return f"{n / 1024**2:.1f} MB"
        if n >= 1024:
            return f"{n / 1024:.0f} KB"
        return f"{n} B"

    def _fmt_mtime(self, mtime: float) -> str:
        return _dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    def _sync_compare_sort_combo_from_var(self) -> None:
        key = self.var_compare_sort.get().strip() or "date_desc"
        if not hasattr(self, "_compare_sort_values"):
            return
        if key not in self._compare_sort_values:
            key = "date_desc"
            self.var_compare_sort.set(key)
        idx = self._compare_sort_values.index(key)
        if getattr(self, "_cb_compare_sort", None) is not None:
            self._cb_compare_sort.current(idx)

    def _sync_compare_group_combo_from_var(self) -> None:
        key = self.var_compare_group.get().strip() or "folder"
        if not hasattr(self, "_compare_group_values"):
            return
        if key not in self._compare_group_values:
            key = "folder"
            self.var_compare_group.set(key)
        idx = self._compare_group_values.index(key)
        if getattr(self, "_cb_compare_group", None) is not None:
            self._cb_compare_group.current(idx)

    def _compare_on_sort_group_change(self) -> None:
        if getattr(self, "_cb_compare_sort", None) is not None:
            si = self._cb_compare_sort.current()
            if 0 <= si < len(self._compare_sort_values):
                self.var_compare_sort.set(self._compare_sort_values[si])
        if getattr(self, "_cb_compare_group", None) is not None:
            gi = self._cb_compare_group.current()
            if 0 <= gi < len(self._compare_group_values):
                self.var_compare_group.set(self._compare_group_values[gi])
        self._compare_rebuild_trees()

    def _compare_setup_tree_columns(self, tree: ttk.Treeview) -> None:
        tree.heading("#0", text="")
        tree.column("#0", width=100, minwidth=50)
        tree.heading("name", text=self.tr("flow.compare_tree_name"))
        tree.heading("rel", text=self.tr("flow.compare_tree_rel"))
        tree.heading("duration", text=self.tr("flow.compare_tree_duration"))
        tree.heading("res", text=self.tr("flow.compare_tree_res"))
        tree.heading("size", text=self.tr("flow.compare_tree_size"))
        tree.heading("mtime", text=self.tr("flow.compare_tree_date"))
        tree.column("name", width=140, minwidth=70)
        tree.column("rel", width=120, minwidth=50)
        tree.column("duration", width=56, minwidth=44)
        tree.column("res", width=72, minwidth=52)
        tree.column("size", width=64, minwidth=44)
        tree.column("mtime", width=108, minwidth=72)

    def _compare_configure_tree_tags(self, tree: ttk.Treeview) -> None:
        tree.tag_configure(ow.COMPARE_TAG_UNKNOWN, background="#ececec")
        tree.tag_configure(ow.COMPARE_TAG_MATCH, background="#fff3b0")
        for i, color in enumerate(ow.COMPARE_SIGNATURE_PALETTE):
            tree.tag_configure(f"cmp_sig_{i}", background=color)

    def _compare_extra_sig_color(self, index: int) -> str:
        r = 200 + (index * 17) % 48
        g = 200 + (index * 29) % 48
        b = 200 + (index * 41) % 48
        return f"#{r:02x}{g:02x}{b:02x}"

    def _compare_apply_signature_tags(
        self,
        tree: ttk.Treeview,
        sig_map: Dict[str, str],
    ) -> None:
        for tag in set(sig_map.values()):
            idx = int(tag.rsplit("_", 1)[-1])
            if idx < len(ow.COMPARE_SIGNATURE_PALETTE):
                color = ow.COMPARE_SIGNATURE_PALETTE[idx]
            else:
                color = self._compare_extra_sig_color(idx)
            tree.tag_configure(tag, background=color)

    def _compare_entry_for_path(
        self, path: Path, entries: List[ow.CompareFileEntry]
    ) -> Optional[ow.CompareFileEntry]:
        for e in entries:
            if ow.compare_paths_equal(e.path, path):
                return e
        name_matches = [e for e in entries if e.path.name == path.name]
        if len(name_matches) == 1:
            return name_matches[0]
        return None

    def _compare_resolve_orig_path(self, evt: Optional[tk.Event]) -> Optional[Path]:
        tree = self.tree_compare_orig
        if evt is not None and getattr(evt, "y", None) is not None:
            try:
                iid = str(tree.identify_row(evt.y))
            except tk.TclError:
                iid = ""
            if iid and not iid.startswith("grp_"):
                p = self._compare_orig_by_iid.get(iid)
                if p is not None:
                    return p
        return self._compare_single_selected_path(tree, self._compare_orig_by_iid)

    def _compare_row_tags(
        self,
        entry: ow.CompareFileEntry,
        sig_map: Dict[str, str],
        *,
        match_signature: Optional[str],
    ) -> tuple[str, ...]:
        sig = ow.compare_match_key(entry)
        tags: List[str] = []
        if sig and sig in sig_map:
            tags.append(sig_map[sig])
        elif not entry.probe_ok:
            tags.append(ow.COMPARE_TAG_UNKNOWN)
        if match_signature and sig and sig == match_signature:
            tags.append(ow.COMPARE_TAG_MATCH)
        return tuple(tags)

    def _compare_make_group_iid(self, prefix: str, grp_name: str, used: Set[str]) -> str:
        safe = (
            grp_name.replace("\\", "_")
            .replace("/", "_")
            .replace(":", "_")
            .replace(" ", "_")
        )
        base = f"grp_{prefix}_{safe}"
        iid = base
        n = 0
        while iid in used:
            n += 1
            iid = f"{base}_{n}"
        used.add(iid)
        return iid

    def _compare_fill_tree(
        self,
        tree: ttk.Treeview,
        entries: List[ow.CompareFileEntry],
        by_iid: Dict[str, Path],
        prefix: str,
        sig_map: Dict[str, str],
        *,
        match_signature: Optional[str] = None,
    ) -> None:
        tree.delete(*tree.get_children())
        by_iid.clear()
        sort_key = self.var_compare_sort.get().strip() or "date_desc"
        group_key = self.var_compare_group.get().strip() or "folder"
        sorted_entries = ow.sort_compare_entries(entries, sort_key)
        groups = ow.group_compare_entries(sorted_entries, group_key, sort_mode=sort_key)
        empty_vals = ("", "", "", "", "", "")
        file_idx = 0
        used_group_iids: Set[str] = set()
        for grp_name, grp_items in groups:
            parent_iid = ""
            if grp_name and group_key != "none":
                parent_iid = self._compare_make_group_iid(prefix, grp_name, used_group_iids)
                tree.insert(
                    "",
                    "end",
                    iid=parent_iid,
                    text=grp_name,
                    values=empty_vals,
                    open=True,
                )
            for e in grp_items:
                iid = f"f_{prefix}_{file_idx}"
                file_idx += 1
                by_iid[iid] = e.path
                row_tags = self._compare_row_tags(
                    e, sig_map, match_signature=match_signature
                )
                insert_kw: Dict[str, Any] = {
                    "iid": iid,
                    "text": "",
                    "values": (
                        e.path.name,
                        e.rel,
                        ow.fmt_compare_duration(e.duration_sec),
                        ow.fmt_compare_resolution(e.width, e.height),
                        self._fmt_file_size(e.size),
                        self._fmt_mtime(e.mtime),
                    ),
                }
                if row_tags:
                    insert_kw["tags"] = row_tags
                tree.insert(parent_iid, "end", **insert_kw)

    def _compare_rebuild_trees(self) -> None:
        if not getattr(self, "tree_compare_orig", None):
            return
        sig_map = ow.compare_signature_tag_map(
            self._compare_orig_entries, self._compare_df_entries
        )
        self._compare_apply_signature_tags(self.tree_compare_orig, sig_map)
        self._compare_apply_signature_tags(self.tree_compare_df, sig_map)
        self._compare_fill_tree(
            self.tree_compare_orig,
            self._compare_orig_entries,
            self._compare_orig_by_iid,
            "o",
            sig_map,
        )
        self._compare_fill_tree(
            self.tree_compare_df,
            self._compare_df_entries,
            self._compare_df_by_iid,
            "d",
            sig_map,
            match_signature=self._compare_selected_orig_sig,
        )

    def _compare_start_probe(self, generation: int) -> None:
        entries = list(self._compare_orig_entries) + list(self._compare_df_entries)
        if not entries:
            return
        if not shutil.which("ffprobe"):
            self._log(self.tr("log.compare_probe_no_ffprobe"))
            return

        def work() -> None:
            total = len(entries)
            for i, entry in enumerate(entries, 1):
                if generation != self._compare_probe_generation:
                    return
                ow.enrich_compare_entry_probe(entry)
                if i % 3 == 0 or i == total:
                    cur, tot, gen = i, total, generation
                    self.root.after(0, lambda: self._compare_probe_progress(gen, cur, tot))
            gen = generation
            self.root.after(0, lambda: self._compare_probe_done(gen))

        threading.Thread(target=work, daemon=True).start()

    def _compare_probe_progress(self, generation: int, current: int, total: int) -> None:
        if generation != self._compare_probe_generation:
            return
        self._log(self.tr("log.compare_probe_progress", cur=current, tot=total))

    def _compare_probe_done(self, generation: int) -> None:
        if generation != self._compare_probe_generation:
            return
        self._compare_rebuild_trees()
        self._log(self.tr("log.compare_probe_done"))

    def _compare_scan_lists(self) -> None:
        src_root = Path(self.var_compare_source_dir.get().strip())
        df_root = Path(self.var_compare_deepfake_dir.get().strip())
        if not src_root.is_dir() or not df_root.is_dir():
            messagebox.showerror(self.tr("err.input"), self.tr("err.compare_scan_dirs"))
            return
        self._compare_probe_generation += 1
        generation = self._compare_probe_generation
        rec = self.var_compare_recursive.get()
        self._compare_orig_entries = ow.scan_compare_folder(src_root, rec)
        self._compare_df_entries = ow.scan_compare_folder(df_root, rec)
        self._compare_selected_orig_sig = None
        self._compare_rebuild_trees()
        self._log(
            self.tr(
                "log.compare_scan",
                no=len(self._compare_orig_entries),
                nd=len(self._compare_df_entries),
            )
        )
        self._compare_start_probe(generation)
        self._save()

    def _compare_tree_file_paths(self, tree: ttk.Treeview, by_iid: Dict[str, Path]) -> List[Path]:
        out: List[Path] = []
        for iid in tree.selection():
            if iid.startswith("grp_"):
                continue
            p = by_iid.get(iid)
            if p is not None:
                out.append(p)
        return out

    def _compare_iid_for_path(self, by_iid: Dict[str, Path], path: Path) -> Optional[str]:
        for iid, p in by_iid.items():
            if ow.compare_paths_equal(p, path):
                return iid
        return None

    def _compare_single_selected_path(
        self, tree: ttk.Treeview, by_iid: Dict[str, Path]
    ) -> Optional[Path]:
        paths = self._compare_tree_file_paths(tree, by_iid)
        return paths[0] if len(paths) == 1 else None

    def _compare_apply_tree_selection(self, tree: ttk.Treeview, iid: str) -> bool:
        if not iid or not tree.exists(iid):
            return False
        self._compare_suppress_tree_select = True
        try:
            cur = tree.selection()
            if cur:
                tree.selection_remove(*cur)
            parent = tree.parent(iid)
            while parent:
                tree.item(parent, open=True)
                parent = tree.parent(parent)
            tree.selection_set(iid)
            tree.focus(iid)
            tree.see(iid)
            tree.update_idletasks()
        except tk.TclError:
            return False
        finally:
            self._compare_suppress_tree_select = False
        return True

    def _compare_scroll_df_to_path(self, path: Path, *, ranked_count: int = 1) -> None:
        iid = self._compare_iid_for_path(self._compare_df_by_iid, path)
        if iid is None:
            self._log(self.tr("log.compare_jump_none", name=path.name))
            return
        if self._compare_apply_tree_selection(self.tree_compare_df, iid):
            self.var_deepfake.set(str(path))
            if ranked_count > 1:
                self._log(
                    self.tr(
                        "log.compare_jump_one_more",
                        name=path.name,
                        more=ranked_count - 1,
                    )
                )
        else:
            self._log(self.tr("log.compare_jump_none", name=path.name))

    def _compare_refresh_df_tree(self) -> None:
        if not getattr(self, "tree_compare_df", None):
            return
        sig_map = ow.compare_signature_tag_map(
            self._compare_orig_entries, self._compare_df_entries
        )
        self._compare_apply_signature_tags(self.tree_compare_df, sig_map)
        self._compare_fill_tree(
            self.tree_compare_df,
            self._compare_df_entries,
            self._compare_df_by_iid,
            "d",
            sig_map,
            match_signature=self._compare_selected_orig_sig,
        )

    def _compare_on_orig_select(self, evt: Optional[tk.Event] = None) -> None:
        if self._compare_suppress_tree_select:
            return
        orig_path = self._compare_resolve_orig_path(evt)
        if orig_path is None:
            return
        aid = self._compare_orig_select_after
        if aid:
            try:
                self.root.after_cancel(aid)
            except tk.TclError:
                pass
        captured = orig_path
        self._compare_orig_select_after = self.root.after(
            80, lambda p=captured: self._compare_do_orig_select(p)
        )

    def _compare_do_orig_select(self, orig_path: Path) -> None:
        self._compare_orig_select_after = None
        if self._compare_suppress_tree_select:
            return
        self.var_source.set(str(orig_path))
        entry = self._compare_entry_for_path(orig_path, self._compare_orig_entries)
        if entry is None:
            self._compare_selected_orig_sig = None
            self._compare_refresh_df_tree()
            self._log(self.tr("log.compare_jump_entry", name=orig_path.name))
            return
        self._compare_selected_orig_sig = ow.compare_match_key(entry)
        pattern = self.var_pattern.get().strip() or "YYMMDDHHmmSS"
        ranked = ow.compare_rank_deepfakes_for_original(
            entry, self._compare_df_entries, pattern
        )
        self._compare_resort_df_hint(orig_path)
        self._compare_refresh_df_tree()
        if not entry.probe_ok or entry.duration_sec is None:
            self._log(self.tr("log.compare_jump_no_meta", name=orig_path.name))
            return
        if not ranked:
            key = ow.compare_match_key(entry) or "?"
            probed = sum(1 for e in self._compare_df_entries if e.probe_ok)
            self._log(
                self.tr(
                    "log.compare_jump_none_detail",
                    name=orig_path.name,
                    match_key=key,
                    nd=len(self._compare_df_entries),
                    probed=probed,
                )
            )
            return
        best = ranked[0]
        self._compare_scroll_df_to_path(best.path, ranked_count=len(ranked))

    def _compare_on_df_select(self, _evt: Optional[tk.Event] = None) -> None:
        paths = self._compare_tree_file_paths(self.tree_compare_df, self._compare_df_by_iid)
        if paths:
            self.var_deepfake.set(str(paths[0]))

    def _compare_resort_df_hint(self, orig: Optional[Path]) -> None:
        """Deepfake-Liste: Signatur-Treffer und Muster-Token nach oben (nur Anzeige)."""
        if orig is None or not self._compare_df_entries:
            return
        sort_key = self.var_compare_sort.get().strip() or "date_desc"
        orig_entry = self._compare_entry_for_path(orig, self._compare_orig_entries)
        orig_sig = ow.compare_match_key(orig_entry) if orig_entry is not None else None
        pattern = self.var_pattern.get().strip() or "YYMMDDHHmmSS"
        token = ow.extract_pattern_match(orig.stem, pattern)

        def _partition(
            entries: List[ow.CompareFileEntry], pred: Callable[[ow.CompareFileEntry], bool]
        ) -> List[ow.CompareFileEntry]:
            hits = [e for e in entries if pred(e)]
            rest = [e for e in entries if not pred(e)]
            return ow.sort_compare_entries(hits, sort_key) + ow.sort_compare_entries(rest, sort_key)

        ordered = list(self._compare_df_entries)
        if orig_sig:
            ordered = _partition(ordered, lambda e: ow.compare_match_key(e) == orig_sig)
        if token:
            ordered = _partition(ordered, lambda e: token in e.path.stem)
        self._compare_df_entries = ordered

    def _prepare_compare_patched_ini(self) -> Optional[str]:
        root_dir = app_dir()
        if not ow.compare_script_path().is_file():
            messagebox.showerror(self.tr("err.input"), self.tr("err.compare_missing"))
            return None
        ini_path = root_dir / "settings.ini"
        if not ini_path.is_file():
            messagebox.showerror(self.tr("err.input"), self.tr("err.ini_missing"))
            return None
        export_dir = self.var_compare_export.get().strip()
        try:
            buf = float(self.var_buffer.get().replace(",", "."))
            noise = int(self.var_noise.get())
            pix = int(self.var_pixel.get())
            pix_max = max(0, int((self.var_pixel_max.get().strip() or "0")))
            dto = int(self.var_davinci_timeout.get())
            dv_start_wait = max(
                0,
                min(
                    600,
                    int(float((self.var_davinci_startup_wait.get().strip() or "20").replace(",", "."))),
                ),
            )
        except ValueError:
            messagebox.showerror(self.tr("err.input"), self.tr("err.numbers"))
            return None
        if export_dir:
            Path(export_dir).mkdir(parents=True, exist_ok=True)
        base_ini = ini_path.read_text(encoding="utf-8", errors="replace")
        return ow.apply_compare_overrides(
            base_ini,
            final_export_dir=export_dir,
            language=self.var_ui_lang.get().strip() or "de",
            buffer_seconds=buf,
            pixel_noise=noise,
            changed_pixels=pix,
            changed_pixels_max=pix_max,
            enable_ffmpeg=self.var_ffmpeg.get(),
            ffmpeg_target=self.var_ffmpeg_target.get().strip(),
            enable_davinci=self.var_davinci.get(),
            davinci_timeout=dto,
            export_avoid_overwrite=self.var_export_unique.get(),
            davinci_api_path=self.var_davinci_api.get().strip(),
            davinci_render_preset=self.var_davinci_preset.get().strip(),
            davinci_exe_path=self.var_davinci_exe.get().strip(),
            davinci_startup_wait_seconds=dv_start_wait,
            ffmpeg_encoder=ow.br_codec_to_compare_ffmpeg_encoder(self.var_br_codec.get()),
        )

    def _compare_set_busy_ui(self, busy: bool) -> None:
        self._compare_busy = busy
        state = "disabled" if busy else "normal"
        self.btn_compare.configure(state=state)
        self.btn_compare_batch.configure(state=state)
        self.btn_compare_stop.configure(state="normal" if busy else "disabled")
        if not busy:
            self.btn_compare_retry.configure(state="disabled")

    def _launch_compare_job(
        self,
        src: str,
        df: str,
        patched: str,
        *,
        retry_export_only: bool = False,
    ) -> None:
        def log_line(s: str) -> None:
            self.root.after(0, lambda m=s: self._log(m))

        def reg_proc(p: Optional[Any]) -> None:
            self.root.after(0, lambda pr=p: setattr(self, "_compare_proc", pr))

        def done(rc: int, err: Optional[str]) -> None:
            self.root.after(0, lambda: self._compare_job_done(rc, err))

        ow.run_compare_subprocess(
            src,
            df,
            patched,
            log_line,
            done,
            register_proc=reg_proc,
            retry_export_only=retry_export_only,
        )

    def _compare_job_done(self, rc: int, err: Optional[str]) -> None:
        stopped = self._compare_user_stopped
        if self._compare_batch_mode and not stopped and err is None and rc == ow.COMPARE_EXIT_OK:
            if self._compare_batch_index + 1 < len(self._compare_batch_queue):
                self._compare_batch_index += 1
                src, df = self._compare_batch_queue[self._compare_batch_index]
                self._log(
                    self.tr(
                        "log.compare_batch_job",
                        cur=self._compare_batch_index + 1,
                        tot=len(self._compare_batch_queue),
                        df=Path(df).name,
                    )
                )
                assert self._compare_patched_ini is not None
                self._launch_compare_job(src, df, self._compare_patched_ini)
                return
            self._log(self.tr("log.compare_batch_done"))
            self._compare_batch_mode = False

        if self._compare_batch_mode and not stopped and (err or rc != ow.COMPARE_EXIT_OK):
            self._log(self.tr("log.compare_batch_stopped", rc=rc))
            self._compare_batch_mode = False

        self._compare_proc = None
        self._compare_set_busy_ui(False)
        if stopped:
            self._log(self.tr("log.compare_stopped"))
            self._compare_user_stopped = False
            self._compare_batch_mode = False
        elif err:
            self._log(self.tr("log.compare_err", err=err))
        elif rc == ow.COMPARE_EXIT_PARTIAL_EXPORT:
            self._log(self.tr("log.compare_partial"))
            self.btn_compare_retry.configure(state="normal")
        self._log(self.tr("log.compare_end", rc=rc))
        self._save()

    def _compare_build_job_queue(self) -> tuple[Optional[List[tuple[str, str]]], Optional[str]]:
        """Warteschlange aus Baumauswahl (bevorzugt) oder Pfadfeldern."""
        orig_paths = self._compare_tree_file_paths(
            self.tree_compare_orig, self._compare_orig_by_iid
        )
        df_paths = self._compare_tree_file_paths(self.tree_compare_df, self._compare_df_by_iid)

        src: Optional[str] = None
        if len(orig_paths) > 1:
            return None, "err.compare_pick_orig_tree"
        if len(orig_paths) == 1:
            src = str(orig_paths[0])
        else:
            s = self.var_source.get().strip()
            if s and Path(s).is_file():
                src = s

        dfs: List[str] = []
        if df_paths:
            dfs = [str(p) for p in df_paths]
        else:
            d = self.var_deepfake.get().strip()
            if d and Path(d).is_file():
                dfs = [d]

        if not src:
            return None, "err.pick_orig"
        if not dfs:
            return None, "err.pick_df"
        return [(src, df) for df in dfs], None

    def _start_compare_jobs(
        self,
        queue: List[tuple[str, str]],
        *,
        retry_export_only: bool = False,
        batch: bool = False,
    ) -> None:
        if not queue:
            return
        if self._compare_busy:
            messagebox.showinfo(self.tr("info.note"), self.tr("info.compare_busy"))
            return
        patched = self._prepare_compare_patched_ini()
        if patched is None:
            return
        self._compare_patched_ini = patched
        self._compare_user_stopped = False
        self._compare_batch_mode = batch and len(queue) > 1
        self._compare_batch_queue = list(queue)
        self._compare_batch_index = 0
        self._compare_set_busy_ui(True)
        if self._compare_batch_mode:
            self._log(self.tr("log.compare_batch_start", n=len(queue)))
        elif retry_export_only:
            self._log(self.tr("log.compare_retry_export"))
        else:
            self._log(self.tr("log.compare_start"))
        src, df = queue[0]
        if self._compare_batch_mode:
            self._log(
                self.tr(
                    "log.compare_batch_job",
                    cur=1,
                    tot=len(queue),
                    df=Path(df).name,
                )
            )
        self._launch_compare_job(src, df, patched, retry_export_only=retry_export_only)

    def _run_compare_batch(self) -> None:
        self._run_compare()

    def _run_compare(self, *, retry_export_only: bool = False) -> None:
        if self._compare_busy:
            messagebox.showinfo(self.tr("info.note"), self.tr("info.compare_busy"))
            return
        queue, err_key = self._compare_build_job_queue()
        if err_key or not queue:
            messagebox.showerror(self.tr("err.input"), self.tr(err_key or "err.pick_orig"))
            return
        src, df = queue[0]
        self.var_source.set(src)
        self.var_deepfake.set(df)
        self._start_compare_jobs(
            queue, retry_export_only=retry_export_only, batch=len(queue) > 1
        )

    def _compare_stop(self) -> None:
        if not self._compare_busy:
            return
        self._compare_user_stopped = True
        p = self._compare_proc
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def _retry_compare(self) -> None:
        if self._compare_busy:
            messagebox.showinfo(self.tr("info.note"), self.tr("info.compare_busy"))
            return
        self._run_compare(retry_export_only=True)

    def _bitrate_scan(self) -> None:
        if not shutil.which("ffprobe"):
            messagebox.showerror(self.tr("err.tool"), self.tr("err.ffprobe"))
            return
        rules = self._parse_rules()
        if rules is None:
            return
        folder = Path(self.var_bitrate_in.get().strip())
        if not folder.is_dir():
            messagebox.showerror(self.tr("err.input"), self.tr("err.br_folder"))
            return
        self._log(self.tr("log.br_scan"))
        self.btn_scan.configure(state="disabled")

        def work() -> None:
            def prog(a: int, b: int) -> None:
                self.root.after(0, lambda a=a, b=b: self._log(self.tr("log.scan_line", a=a, b=b)))

            rows = ow.scan_folder_parallel(
                folder,
                self.var_br_recursive.get(),
                rules,
                self.var_br_only_lower.get(),
                progress_cb=prog,
            )
            self.root.after(0, lambda: self._bitrate_scan_done(rows, folder))

        threading.Thread(target=work, daemon=True).start()

    def _bitrate_scan_done(self, rows: List[ow.VideoRow], folder: Path) -> None:
        self.btn_scan.configure(state="normal")
        self._bitrate_rows = rows
        self._bitrate_scan_folder = folder
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            rel = str(row.path.relative_to(folder)) if row.path.is_relative_to(folder) else str(row.path)
            self.tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(
                    rel,
                    f"{row.width}x{row.height}",
                    row.source_kbps if row.source_kbps is not None else "-",
                    row.effective_target_kbps if row.effective_target_kbps is not None else "-",
                    self.tr("br.action.convert")
                    if row.action == "convert"
                    else self.tr("br.action.skip"),
                ),
            )
        n_c = sum(1 for r in rows if r.action == "convert")
        self._log(self.tr("log.scan_done", n=len(rows), c=n_c))

    def _bitrate_rebuild_tree_from_rows(self) -> None:
        folder = self._bitrate_scan_folder or Path(self.var_bitrate_in.get().strip())
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self._bitrate_rows):
            rel = str(row.path.relative_to(folder)) if row.path.is_relative_to(folder) else str(row.path)
            self.tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(
                    rel,
                    f"{row.width}x{row.height}",
                    row.source_kbps if row.source_kbps is not None else "-",
                    row.effective_target_kbps if row.effective_target_kbps is not None else "-",
                    self.tr("br.action.convert")
                    if row.action == "convert"
                    else self.tr("br.action.skip"),
                ),
            )

    def _bitrate_tree_context_menu(self, event: tk.Event) -> None:
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        sel = self.tree.selection()
        if not sel or row_id not in sel:
            self.tree.selection_set(row_id)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=self.tr("flow.ctx_move_to_tagger"), command=self._bitrate_move_selection_to_tagger_in)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _bitrate_move_selection_to_tagger_in(self) -> None:
        tag_in = Path(self.var_tagger_in.get().strip())
        if not tag_in.is_dir():
            messagebox.showerror(self.tr("err.input"), self.tr("err.tagger_in_for_move"))
            return
        br_in = Path(self.var_bitrate_in.get().strip())
        if not self._bitrate_rows:
            return
        sel = self.tree.selection()
        if not sel:
            return
        if tag_in.resolve() == br_in.resolve():
            messagebox.showinfo(self.tr("info.note"), self.tr("info.tagger_same_as_bitrate_in"))
            return
        indices = sorted({int(iid) for iid in sel if str(iid).isdigit()})
        to_move: List[Path] = []
        for i in indices:
            if 0 <= i < len(self._bitrate_rows):
                to_move.append(self._bitrate_rows[i].path)
        if not to_move:
            return
        moved_res: Set[Any] = set()
        for src in to_move:
            if not src.is_file():
                continue
            dst = tag_in / src.name
            if dst.resolve() == src.resolve():
                continue
            if dst.exists():
                dst = ow.make_unique_path(dst)
            try:
                shutil.move(str(src), str(dst))
            except OSError as e:
                messagebox.showerror(self.tr("err.input"), str(e))
                break
            moved_res.add(src.resolve())
            self._log(self.tr("log.br_move_tagger", name=dst.name))
        self._bitrate_rows = [r for r in self._bitrate_rows if r.path.resolve() not in moved_res]
        self._bitrate_rebuild_tree_from_rows()
        self._tagger_refresh_list(log_count=False)

    def _tagger_refresh_list(self, *, log_count: bool = True) -> None:
        if getattr(self, "tree_tagger", None) is None:
            return
        self.tree_tagger.delete(*self.tree_tagger.get_children())
        self._tagger_scan_paths.clear()
        inp = Path(self.var_tagger_in.get().strip())
        if not inp.is_dir():
            return
        files = sorted(p for p in inp.glob("*.mp4") if not ow._is_partial_temp_video(p.name))
        self._tagger_scan_paths.extend(files)
        for i, p in enumerate(files):
            self.tree_tagger.insert("", tk.END, iid=str(i), values=(p.name,))
        if self._tagger_preview is not None:
            self._tagger_preview.load_path(None)
        if log_count and files:
            self._log(self.tr("log.tagger_list", n=len(files)))

    def _on_tagger_tree_select(self, _event: Optional[tk.Event] = None) -> None:
        if self._tagger_preview is None:
            return
        sel = self.tree_tagger.selection()
        if not sel:
            self._tagger_preview.load_path(None)
            return
        indices = sorted({int(iid) for iid in sel if str(iid).isdigit()})
        if not indices:
            self._tagger_preview.load_path(None)
            return
        idx = indices[0]
        if 0 <= idx < len(self._tagger_scan_paths):
            self._tagger_preview.load_path(self._tagger_scan_paths[idx])
        else:
            self._tagger_preview.load_path(None)

    def _tagger_resolved_only_files(self) -> Optional[List[Path]]:
        if getattr(self, "tree_tagger", None) is None:
            return None
        sel = self.tree_tagger.selection()
        if not sel:
            return None
        indices = sorted({int(iid) for iid in sel if str(iid).isdigit()})
        out: List[Path] = []
        for i in indices:
            if 0 <= i < len(self._tagger_scan_paths):
                out.append(self._tagger_scan_paths[i])
        return out

    def _bitrate_stop_click(self) -> None:
        self._bitrate_stop.set()

    def _bitrate_convert(self) -> None:
        if not shutil.which("ffmpeg"):
            messagebox.showerror(self.tr("err.tool"), self.tr("err.ffmpeg"))
            return
        if self._bitrate_thread and self._bitrate_thread.is_alive():
            messagebox.showinfo(self.tr("info.note"), self.tr("info.convert_busy"))
            return
        if not self._bitrate_rows:
            messagebox.showerror(self.tr("err.input"), self.tr("err.br_scan_first"))
            return
        inp = Path(self.var_bitrate_in.get().strip())
        out = Path(self.var_bitrate_out.get().strip())
        if not self.var_bitrate_out.get().strip():
            messagebox.showerror(self.tr("err.input"), self.tr("err.br_out"))
            return
        all_rows = list(self._bitrate_rows)
        sel_iids = self.tree.selection()
        if sel_iids:
            indices: List[int] = []
            for iid in sel_iids:
                try:
                    indices.append(int(str(iid)))
                except (TypeError, ValueError):
                    continue
            indices.sort()
            rows = [all_rows[i] for i in indices if 0 <= i < len(all_rows)]
            if not rows:
                messagebox.showerror(self.tr("err.input"), self.tr("err.br_sel_invalid"))
                return
        else:
            rows = all_rows

        jobs = [r for r in rows if r.action == "convert" and r.effective_target_kbps]
        if not jobs:
            if sel_iids:
                messagebox.showinfo(self.tr("info.note"), self.tr("err.br_sel_no_convert"))
            else:
                messagebox.showinfo(self.tr("info.note"), self.tr("err.br_none_to_convert"))
            return

        out.mkdir(parents=True, exist_ok=True)
        self._bitrate_stop.clear()
        self.btn_conv.configure(state="disabled")
        self.btn_stop_br.configure(state="normal")
        self._log(self.tr("log.br_conv"))
        if sel_iids:
            self._log(self.tr("log.br_conv_sel", n=len(rows)))
        else:
            self._log(self.tr("log.br_conv_all", n=len(all_rows)))

        def prog(cur: int, tot: int) -> None:
            self.root.after(0, lambda c=cur, t=tot: self._log(self.tr("log.br_prog", cur=c, tot=t)))

        def log(s: str) -> None:
            self.root.after(0, lambda m=s: self._log(m))

        def work() -> None:
            try:
                ow.convert_video_rows(
                    rows,
                    inp,
                    out,
                    suffix=self.var_br_suffix.get().strip() or "_bitrate",
                    output_mp4=self.var_br_mp4.get(),
                    codec=self.var_br_codec.get(),
                    audio_mode=self.var_br_audio.get(),
                    stop_event=self._bitrate_stop,
                    log=lambda s: log(s),
                    progress=lambda c, t: prog(c, t),
                    delete_source_after_ok=self.var_br_delete_source.get(),
                    ui_lang=self.var_ui_lang.get().strip() or "de",
                )
            finally:
                self.root.after(0, self._bitrate_convert_done)

        self._bitrate_thread = threading.Thread(target=work, daemon=True)
        self._bitrate_thread.start()

    def _bitrate_convert_done(self) -> None:
        self.btn_conv.configure(state="normal")
        self.btn_stop_br.configure(state="disabled")
        self._log(self.tr("log.br_done"))
        self._tagger_refresh_list(log_count=False)
        self._save()

    def _tagger_filter_settings(self) -> tuple[float, int, int, int]:
        try:
            buf = float(self.var_buffer.get().replace(",", "."))
            noise = int(self.var_noise.get())
            pix = int(self.var_pixel.get())
            pix_max = max(0, int((self.var_pixel_max.get().strip() or "0")))
        except ValueError:
            buf, noise, pix, pix_max = 2.0, 15, 200, 0
        return buf, noise, pix, pix_max

    def _run_tagger(self) -> None:
        inp = Path(self.var_tagger_in.get().strip())
        outp = Path(self.var_tagger_out.get().strip())
        if not inp.is_dir() or not outp.as_posix():
            messagebox.showerror(self.tr("err.input"), self.tr("err.tagger_folders"))
            return
        only = self._tagger_resolved_only_files()
        if only is not None and len(only) == 0:
            messagebox.showerror(self.tr("err.input"), self.tr("err.tagger_sel_invalid"))
            return
        if self._tagger_preview is not None:
            self._tagger_preview.release_file()
        outp.mkdir(parents=True, exist_ok=True)

        def log(s: str) -> None:
            self.root.after(0, lambda m=s: self._log(m))

        lang = (self.var_ui_lang.get().strip() or "de").lower()
        if lang not in ("de", "en"):
            lang = "de"

        buf, noise, pix, pix_max = self._tagger_filter_settings()
        br_suffix = self.var_br_suffix.get().strip() or "_bitrate"

        def work() -> None:
            ok, sk = ow.tagger_process_folder(
                inp,
                outp,
                tag=self.var_tag.get(),
                profile_name=self.var_tag_profile.get().strip() or "Profil",
                keep_suffix_csv=self.var_keep.get(),
                ignore_suffix_csv=self.var_ignore.get(),
                drop_suffix_csv=self.var_drop.get(),
                pattern_text=self.var_pattern.get(),
                log=log,
                only_files=only,
                ui_lang=lang,
                filter_buffer_seconds=buf,
                filter_noise_threshold=noise,
                filter_pixel_threshold=pix,
                filter_pixel_max_threshold=pix_max,
                bitrate_output_suffix=br_suffix,
            )
            self.root.after(0, lambda: self._tagger_done(ok, sk))

        threading.Thread(target=work, daemon=True).start()
        self._log(self.tr("log.tagger_start"))
        if only:
            self._log(self.tr("log.tagger_sel", n=len(only)))

    def _tagger_done(self, ok: int, skipped: int) -> None:
        self._log(self.tr("log.tagger_done", ok=ok, sk=skipped))
        self._tagger_refresh_list(log_count=False)
        self._save()
        if ok > 0:
            self._maybe_auto_tag_distribute()


def _run_compare_cli_child_and_exit() -> None:
    """PyInstaller one-dir: Compare is spawned as ``Oxco.exe --oxco-compare <args>`` (same folder as compare.py)."""
    if len(sys.argv) < 2 or sys.argv[1] != "--oxco-compare":
        return
    import runpy

    root = app_dir()
    try:
        os.chdir(root)
    except OSError:
        pass
    compare_py = root / "compare.py"
    if not compare_py.is_file():
        print(f"compare.py not found: {compare_py}", file=sys.stderr)
        raise SystemExit(1)
    sys.argv = [str(compare_py)] + sys.argv[2:]
    try:
        runpy.run_path(str(compare_py), run_name="__main__")
    except SystemExit as e:
        code = e.code
        if code is None:
            raise SystemExit(0) from e
        if isinstance(code, int):
            raise SystemExit(code) from e
        raise SystemExit(code) from e
    raise SystemExit(0)


def main() -> None:
    root = tk.Tk()
    OxcoApp(root)
    root.mainloop()


if __name__ == "__main__":
    _run_compare_cli_child_and_exit()
    main()
