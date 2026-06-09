"""
Vorschau-Player (Tkinter + OpenCV + Pillow): Wiedergabe wie Flickercheck,
plus gleiche Pixel-Differenz-Logik wie Compare — zum Einstellen der Schwellen.
"""

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional, Sequence, Set, Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk

import compare as oxco_compare
import oxco_workers as ow


def _to_bgr(frame: Any) -> Optional[np.ndarray]:
    if frame is None:
        return None
    if frame.ndim == 2:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if frame.shape[2] == 1:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return frame


def _match_size(bgr: np.ndarray, wo: int, ho: int) -> np.ndarray:
    hd, wd = bgr.shape[:2]
    if (wd, hd) == (wo, ho):
        return bgr
    return cv2.resize(bgr, (wo, ho), interpolation=cv2.INTER_LINEAR)


def _compare_diff_count(frame_a_bgr: np.ndarray, frame_b_bgr: np.ndarray, noise_thresh: int) -> int:
    """Wie compare.py: Graustufen-Diff, Schwellwert, countNonZero."""
    gray_a = cv2.cvtColor(frame_a_bgr, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(frame_b_bgr, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_a, gray_b)
    _, thresh = cv2.threshold(diff, int(noise_thresh), 255, cv2.THRESH_BINARY)
    return int(cv2.countNonZero(thresh))


def _apply_diff_overlay(
    orig_bgr: np.ndarray, other_bgr: np.ndarray, noise_thresh: int, opacity: float = 0.5
) -> np.ndarray:
    gray_o = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2GRAY)
    gray_d = cv2.cvtColor(other_bgr, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_o, gray_d)
    _, mask = cv2.threshold(diff, int(noise_thresh), 255, cv2.THRESH_BINARY)
    mask_bgr = cv2.merge([mask, np.zeros_like(mask), mask])
    return cv2.addWeighted(orig_bgr, 1.0, mask_bgr, opacity, 0)


class OxcoVideoPreview(ttk.Frame):
    """Vorschau + Compare-Filter-Hilfe."""

    _SCRUB_DEBOUNCE_MS = 120

    def __init__(self, parent: tk.Misc, host_app: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self._host_app = host_app
        self._cap_a: Any = None
        self._cap_b: Any = None
        self._meta_a: Optional[ow.PreviewVideoMeta] = None
        self._meta_b: Optional[ow.PreviewVideoMeta] = None
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._playing = False
        self._frame_index = 0
        self._total = 0
        self._vw = 1280
        self._vh = 720
        self._last_tick = 0.0
        self._seq_next: Optional[int] = None
        self._updating_scale = False
        self._scrub_after: Optional[str] = None
        self._trace_ids: list[tuple[Any, str, str]] = []
        self._auto_load_after: Optional[str] = None
        self._syncing_paths_from_host = False

        self.var_path_a = tk.StringVar(value="")
        self.var_path_b = tk.StringVar(value="")
        self.var_fps = tk.IntVar(value=24)
        self.var_side = tk.BooleanVar(value=False)
        self.var_link_paths = tk.BooleanVar(value=True)
        self.var_auto_load = tk.BooleanVar(value=True)
        self.var_overlay = tk.BooleanVar(value=True)

        self.var_prev_noise = tk.IntVar(value=15)
        self.var_prev_pixel = tk.IntVar(value=200)
        self._canvas_img_id: Optional[int] = None
        self._init_thresholds_from_host()

        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        top = ttk.LabelFrame(self, text=self._t("preview.files"))
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)

        self.ent_a = ttk.Entry(top, textvariable=self.var_path_a)
        self.ent_b = ttk.Entry(top, textvariable=self.var_path_b)
        la = ttk.Label(top, text=self._t("preview.video_a"))
        la.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.ent_a.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(top, text="…", width=3, command=self._browse_a).grid(row=0, column=2, padx=4)
        lb = ttk.Label(top, text=self._t("preview.video_b"))
        lb.grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.ent_b.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(top, text="…", width=3, command=self._browse_b).grid(row=1, column=2, padx=4)
        self.ent_a.bind("<FocusOut>", lambda _e: self._on_path_focus_out("a"))
        self.ent_b.bind("<FocusOut>", lambda _e: self._on_path_focus_out("b"))

        link_fr = ttk.Frame(top)
        link_fr.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        self.chk_link_paths = ttk.Checkbutton(
            link_fr,
            text=self._t("preview.link_paths"),
            variable=self.var_link_paths,
            command=self._on_toggle_link_paths,
        )
        self.chk_link_paths.pack(side="left", padx=(0, 12))
        self.chk_auto_load = ttk.Checkbutton(
            link_fr, text=self._t("preview.auto_load"), variable=self.var_auto_load
        )
        self.chk_auto_load.pack(side="left")
        lh = ttk.Label(
            top,
            text=self._t("preview.path_hint"),
            wraplength=640,
            foreground="gray",
        )
        lh.grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))

        filt = ttk.LabelFrame(self, text=self._t("preview.try_diff"))
        filt.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        filt.columnconfigure(1, weight=1)
        l_noise = ttk.Label(filt, text=self._t("preview.sens_small"))
        l_noise.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.scale_noise = ttk.Scale(filt, from_=1, to=80, orient="horizontal", command=self._on_noise_slide)
        self.scale_noise.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.lbl_noise_val = ttk.Label(filt, width=4, anchor="e")
        self.lbl_noise_val.grid(row=0, column=2, padx=4)
        l_pix = ttk.Label(filt, text=self._t("preview.diff_threshold"))
        l_pix.grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.scale_pixel = ttk.Scale(filt, from_=1, to=4000, orient="horizontal", command=self._on_pixel_slide)
        self.scale_pixel.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        self.lbl_pixel_val = ttk.Label(filt, width=6, anchor="e")
        self.lbl_pixel_val.grid(row=1, column=2, padx=4)

        rw2 = ttk.Frame(filt)
        rw2.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        self.chk_overlay = ttk.Checkbutton(rw2, text=self._t("preview.overlay"), variable=self.var_overlay)
        self.chk_overlay.pack(side="left", padx=(0, 16))
        self.lbl_diff = ttk.Label(filt, text=self._t("preview.diff.none_b"), font=("Segoe UI", 10, "bold"))
        self.lbl_diff.grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=2)
        self.lbl_swap = ttk.Label(filt, text="—", font=("Segoe UI", 10))
        self.lbl_swap.grid(row=3, column=2, sticky="w", padx=4)

        lf_hint = ttk.Label(
            filt,
            text=self._t("preview.hint_buffer"),
            wraplength=640,
            foreground="gray",
        )
        lf_hint.grid(row=4, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4))

        btn_fr = ttk.Frame(filt)
        btn_fr.grid(row=5, column=0, columnspan=3, sticky="w", padx=6, pady=6)
        self.btn_apply_filter = ttk.Button(btn_fr, text=self._t("preview.apply_filter_tab"), command=self._apply_to_filter_tab)
        self.btn_apply_filter.pack(side="left", padx=(0, 8))
        self.btn_apply_ini = ttk.Button(btn_fr, text=self._t("preview.apply_ini"), command=self._apply_to_settings_ini)
        self.btn_apply_ini.pack(side="left", padx=(0, 8))
        ttk.Button(btn_fr, text="(i)", width=3, command=self._help_filter).pack(side="left", padx=4)

        ctl = ttk.Frame(self)
        ctl.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.btn_load = ttk.Button(ctl, text=self._t("preview.load"), command=self._load)
        self.btn_load.pack(side="left", padx=(0, 8))
        self.btn_play = ttk.Button(ctl, text=self._t("preview.play"), command=self._toggle_play, state="disabled")
        self.btn_play.pack(side="left", padx=(0, 8))
        l_fps = ttk.Label(ctl, text=self._t("preview.max_fps"))
        l_fps.pack(side="left", padx=(8, 4))
        tk.Spinbox(ctl, from_=1, to=60, textvariable=self.var_fps, width=5).pack(side="left", padx=(0, 12))
        self.chk_side = ttk.Checkbutton(
            ctl, text=self._t("preview.side_by_side"), variable=self.var_side, command=self._on_side_toggle
        )
        self.chk_side.pack(side="left", padx=(8, 0))
        ttk.Button(ctl, text="(i)", width=3, command=self._help_player).pack(side="right", padx=4)

        vid_fr = ttk.LabelFrame(self, text=self._t("preview.picture"))
        vid_fr.grid(row=4, column=0, sticky="nsew")
        vid_fr.rowconfigure(0, weight=1)
        vid_fr.columnconfigure(0, weight=1)
        self.vid_canvas = tk.Canvas(vid_fr, bg="#101010", highlightthickness=0, width=640, height=360)
        self.vid_canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        vid_fr.rowconfigure(0, minsize=260)
        self.vid_canvas.bind("<Configure>", lambda _e: self._maybe_redraw())
        self.vid_canvas.bind("<space>", lambda e: self._toggle_play())
        self.vid_canvas.bind("<Left>", lambda e: self._step(-1))
        self.vid_canvas.bind("<Right>", lambda e: self._step(1))

        bot = ttk.Frame(self)
        bot.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        bot.columnconfigure(0, weight=1)
        self.lbl_info = ttk.Label(bot, text="—")
        self.lbl_info.grid(row=0, column=0, sticky="w", padx=4)
        self.scale_pos = ttk.Scale(bot, from_=0, to=1, orient="horizontal", command=self._on_scale, state="disabled")
        self.scale_pos.grid(row=1, column=0, sticky="ew", pady=4)

        self._i18n_frames = (
            (top, "preview.files"),
            (filt, "preview.try_diff"),
            (vid_fr, "preview.picture"),
        )
        self._i18n_labels = (
            (la, "preview.video_a"),
            (lb, "preview.video_b"),
            (l_noise, "preview.sens_small"),
            (l_pix, "preview.diff_threshold"),
            (lh, "preview.path_hint"),
            (lf_hint, "preview.hint_buffer"),
            (l_fps, "preview.max_fps"),
        )
        self._i18n_checks = (
            (self.chk_link_paths, "preview.link_paths"),
            (self.chk_auto_load, "preview.auto_load"),
            (self.chk_overlay, "preview.overlay"),
            (self.chk_side, "preview.side_by_side"),
        )
        self._i18n_buttons = (
            (self.btn_load, "preview.load"),
            (self.btn_apply_filter, "preview.apply_filter_tab"),
            (self.btn_apply_ini, "preview.apply_ini"),
        )

        self.bind("<space>", lambda e: self._toggle_play())
        self.bind("<Left>", lambda e: self._step(-1))
        self.bind("<Right>", lambda e: self._step(1))

        self._refresh_sliders_from_vars()
        self._on_toggle_link_paths()
        oid = self.var_overlay.trace_add("write", lambda *_a: self.after(0, self._maybe_redraw))
        self._trace_ids.append((self.var_overlay, "write", oid))
        self._attach_host_traces()

        self.bind("<Destroy>", self._on_destroy)
        self._show_canvas_empty()

    def _t(self, key: str, **kwargs: Any) -> str:
        if self._host_app is not None and hasattr(self._host_app, "tr"):
            return self._host_app.tr(key, **kwargs)  # type: ignore[no-any-return]
        from oxco_i18n import tr as _tr

        return _tr("de", key, **kwargs)

    def apply_i18n(self) -> None:
        for lf, k in getattr(self, "_i18n_frames", ()):
            lf.configure(text=self._t(k))
        for w, k in getattr(self, "_i18n_labels", ()):
            w.configure(text=self._t(k))
        for w, kt in getattr(self, "_i18n_checks", ()):
            w.configure(text=self._t(kt))
        for b, k in getattr(self, "_i18n_buttons", ()):
            b.configure(text=self._t(k))
        if self._cap_a is None:
            self._show_canvas_empty()
        st = self._t("preview.pause") if self._playing else self._t("preview.play")
        try:
            self.btn_play.configure(text=st)
        except tk.TclError:
            pass
        if self._cap_a is not None:
            self._maybe_redraw()
        else:
            try:
                self.lbl_diff.configure(text=self._t("preview.diff.none_b"))
                self.lbl_swap.configure(text="")
            except tk.TclError:
                pass

    def tr(self, key: str, **kwargs: Any) -> str:
        return self._t(key, **kwargs)

    def _oxco_base_dir(self) -> str:
        return str(Path(__file__).resolve().parent)

    def _init_thresholds_from_host(self) -> None:
        if self._host_app is None:
            return
        try:
            self.var_prev_noise.set(int(float(str(self._host_app.var_noise.get()).replace(",", "."))))
        except (TypeError, ValueError):
            pass
        try:
            self.var_prev_pixel.set(int(self._host_app.var_pixel.get()))
        except (TypeError, ValueError):
            pass

    def _attach_host_traces(self) -> None:
        if self._host_app is None:
            return
        def _trace(*_a: Any) -> None:
            self.after(1, self._on_host_paths_changed)

        for v in (self._host_app.var_source, self._host_app.var_deepfake):
            tid = v.trace_add("write", _trace)
            self._trace_ids.append((v, "write", tid))

    def _maybe_redraw(self) -> None:
        if self._cap_a is not None:
            self._render_frame()
        else:
            self._show_canvas_empty()

    def _show_canvas_empty(self) -> None:
        self.vid_canvas.delete("all")
        self._photo = None
        self.update_idletasks()
        cw = max(120, int(self.vid_canvas.winfo_width()))
        ch = max(80, int(self.vid_canvas.winfo_height()))
        self.vid_canvas.create_text(
            cw // 2,
            ch // 2,
            text=self._t("preview.no_video"),
            fill="#cccccc",
            font=("Segoe UI", 11),
        )

    def _on_destroy(self, _event: tk.Event) -> None:
        for v, mode, tid in self._trace_ids:
            try:
                v.trace_remove(mode, tid)
            except tk.TclError:
                pass
        self._trace_ids.clear()
        self.shutdown()

    def _on_host_paths_changed(self) -> None:
        if self._host_app is not None and getattr(self._host_app, "_file_op_in_progress", False):
            return
        if not self.var_link_paths.get():
            return
        self._sync_paths_from_host()
        if self.var_auto_load.get():
            self._schedule_auto_load()

    def _schedule_auto_load(self) -> None:
        if self._auto_load_after is not None:
            try:
                self.after_cancel(self._auto_load_after)
            except tk.TclError:
                pass
        self._auto_load_after = self.after(400, self._do_auto_load)

    def _do_auto_load(self) -> None:
        self._auto_load_after = None
        pa = self.var_path_a.get().strip()
        if not pa or not Path(pa).is_file():
            return
        if self.var_side.get():
            pb = self.var_path_b.get().strip()
            if not pb or not Path(pb).is_file():
                return
        self._load_internal(silent=True)

    def _sync_paths_from_host(self) -> None:
        if self._host_app is None:
            return
        self._syncing_paths_from_host = True
        try:
            self.var_path_a.set(self._host_app.var_source.get().strip())
            self.var_path_b.set(self._host_app.var_deepfake.get().strip())
            if self.var_path_b.get():
                self.var_side.set(True)
        finally:
            self._syncing_paths_from_host = False

    def _unlink_from_host_if_paths_diverged(self, which: str) -> None:
        if self._host_app is None or not self.var_link_paths.get() or self._syncing_paths_from_host:
            return
        if which == "a":
            if self.var_path_a.get().strip() != self._host_app.var_source.get().strip():
                self.var_link_paths.set(False)
        else:
            if self.var_path_b.get().strip() != self._host_app.var_deepfake.get().strip():
                self.var_link_paths.set(False)

    def _on_path_focus_out(self, which: str) -> None:
        self._unlink_from_host_if_paths_diverged(which)

    def _on_toggle_link_paths(self) -> None:
        if self.var_link_paths.get():
            self._sync_paths_from_host()
            self._schedule_auto_load()

    def _refresh_sliders_from_vars(self) -> None:
        n = int(self.var_prev_noise.get())
        p = int(self.var_prev_pixel.get())
        self._updating_scale = True
        try:
            self.scale_noise.set(n)
            self.scale_pixel.set(p)
        finally:
            self._updating_scale = False
        self.lbl_noise_val.configure(text=str(n))
        self.lbl_pixel_val.configure(text=str(p))

    def _on_noise_slide(self, val: str) -> None:
        if self._updating_scale:
            return
        n = max(1, min(80, int(round(float(val)))))
        self.var_prev_noise.set(n)
        self.lbl_noise_val.configure(text=str(n))
        self._render_frame()

    def _on_pixel_slide(self, val: str) -> None:
        if self._updating_scale:
            return
        p = max(1, min(4000, int(round(float(val)))))
        self.var_prev_pixel.set(p)
        self.lbl_pixel_val.configure(text=str(p))
        self._render_frame()

    def _help_filter(self) -> None:
        messagebox.showinfo(self._t("preview.help_diff.title"), self._t("preview.help_diff.body"))

    def _help_player(self) -> None:
        messagebox.showinfo(self._t("preview.help_player.title"), self._t("preview.help_player.body"))

    def _apply_to_filter_tab(self) -> None:
        if self._host_app is None:
            return
        self._host_app.var_noise.set(str(int(self.var_prev_noise.get())))
        self._host_app.var_pixel.set(str(int(self.var_prev_pixel.get())))
        messagebox.showinfo(self._t("preview.done_filter"), self._t("preview.done_filter_msg"))

    def _apply_to_settings_ini(self) -> None:
        ok = oxco_compare.write_settings_pixel_thresholds(
            self._oxco_base_dir(),
            int(self.var_prev_noise.get()),
            int(self.var_prev_pixel.get()),
        )
        if ok:
            messagebox.showinfo(self._t("preview.done_filter"), self._t("preview.done_ini_msg"))
        else:
            messagebox.showerror(self._t("preview.err_ini_title"), self._t("preview.err_ini_msg"))

    def _browse_a(self) -> None:
        if self.var_link_paths.get():
            self.var_link_paths.set(False)
        p = filedialog.askopenfilename(
            title=self._t("dlg.video_a"), filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm")]
        )
        if p:
            self.var_path_a.set(p)

    def _browse_b(self) -> None:
        if self.var_link_paths.get():
            self.var_link_paths.set(False)
        p = filedialog.askopenfilename(
            title=self._t("dlg.video_b"), filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.webm")]
        )
        if p:
            self.var_path_b.set(p)

    def _release_caps(self) -> None:
        if self._scrub_after is not None:
            try:
                self.after_cancel(self._scrub_after)
            except tk.TclError:
                pass
            self._scrub_after = None
        if self._cap_a is not None:
            self._cap_a.release()
            self._cap_a = None
        if self._cap_b is not None:
            self._cap_b.release()
            self._cap_b = None
        self._meta_a = None
        self._meta_b = None

    def _cancel_scrub_render(self) -> None:
        if self._scrub_after is not None:
            try:
                self.after_cancel(self._scrub_after)
            except tk.TclError:
                pass
            self._scrub_after = None

    def _schedule_scrub_render(self) -> None:
        self._cancel_scrub_render()
        self._scrub_after = self.after(self._SCRUB_DEBOUNCE_MS, self._scrub_render)

    def _scrub_render(self) -> None:
        self._scrub_after = None
        self._render_frame()

    def _preview_ready(self) -> bool:
        return self._meta_a is not None or self._cap_a is not None

    def _on_side_toggle(self) -> None:
        self._seq_next = None
        if self._preview_ready():
            self._render_frame()

    def _load(self) -> None:
        self._load_internal(silent=False)

    def _load_internal(self, silent: bool) -> None:
        self._playing = False
        self.btn_play.configure(text=self._t("preview.play"))
        self._release_caps()
        pa = self.var_path_a.get().strip()
        if not pa:
            if not silent:
                messagebox.showwarning(self._t("preview.warn_no_a_title"), self._t("preview.warn_no_a"))
            return
        if self.var_side.get():
            pb = self.var_path_b.get().strip()
            if not pb:
                if not silent:
                    messagebox.showwarning(self._t("preview.warn_no_a_title"), self._t("preview.warn_no_b"))
                return

        path_a = Path(pa)
        if not path_a.is_file():
            if not silent:
                messagebox.showerror(self._t("preview.warn_no_a_title"), self._t("preview.err_not_found"))
            return

        self._meta_a = ow.probe_preview_media(path_a)
        self._cap_a = cv2.VideoCapture(str(path_a), cv2.CAP_FFMPEG)
        if not self._cap_a.isOpened():
            self._cap_a.release()
            self._cap_a = None
            if self._meta_a is None:
                if not silent:
                    messagebox.showerror(self._t("preview.warn_no_a_title"), self._t("preview.err_open_a"))
                return

        if self._meta_a is not None:
            self._total = self._meta_a.frame_count
            self._vw = self._meta_a.width
            self._vh = self._meta_a.height
        elif self._cap_a is not None:
            self._total = int(self._cap_a.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            self._vw = int(self._cap_a.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
            self._vh = int(self._cap_a.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        else:
            self._total = 0

        self._cap_b = None
        self._meta_b = None
        pb = self.var_path_b.get().strip()
        if pb and Path(pb).is_file():
            path_b = Path(pb)
            self._meta_b = ow.probe_preview_media(path_b)
            self._cap_b = cv2.VideoCapture(str(path_b), cv2.CAP_FFMPEG)
            if not self._cap_b.isOpened():
                self._cap_b.release()
                self._cap_b = None
                if self._meta_b is None and not silent:
                    messagebox.showwarning(self._t("preview.warn_no_a_title"), self._t("preview.warn_b_open"))

        self._frame_index = 0
        self._seq_next = None
        self._updating_scale = True
        last = max(0, self._total - 1)
        try:
            self.scale_pos.configure(to=max(1, last), state="normal")
            self.scale_pos.set(0)
        finally:
            self._updating_scale = False

        self.btn_play.configure(state="normal" if self._cap_a is not None else "disabled")
        self._render_frame()
        self.lbl_info.configure(
            text=self._t("preview.meta", name=path_a.name, frames=self._total, w=self._vw, h=self._vh)
        )

    def _toggle_play(self) -> None:
        if self._cap_a is None:
            return
        self._playing = not self._playing
        self.btn_play.configure(text=self._t("preview.pause") if self._playing else self._t("preview.play"))
        self._last_tick = time.time()
        if self._playing:
            self._seq_next = None
            self._tick()

    def _tick(self) -> None:
        if not self._playing or self._cap_a is None:
            return
        fps = max(1, int(self.var_fps.get() or 24))
        min_interval = 1.0 / fps
        elapsed = time.time() - self._last_tick
        if elapsed < min_interval:
            self.after(max(1, int((min_interval - elapsed) * 1000)), self._tick)
            return
        self._last_tick = time.time()

        if self._total > 0:
            self._frame_index = (self._frame_index + 1) % self._total
        self._seq_next = None

        self._updating_scale = True
        try:
            self.scale_pos.set(self._frame_index)
        finally:
            self._updating_scale = False

        self._render_frame()
        self.after(1, self._tick)

    def _step(self, delta: int) -> None:
        if not self._preview_ready() or self._total <= 0:
            return
        self._seq_next = None
        self._frame_index = max(0, min(self._total - 1, self._frame_index + delta))
        self._updating_scale = True
        try:
            self.scale_pos.set(self._frame_index)
        finally:
            self._updating_scale = False
        if not self._playing:
            self._schedule_scrub_render()

    def _on_scale(self, val: str) -> None:
        if self._updating_scale or not self._preview_ready():
            return
        self._seq_next = None
        self._frame_index = int(float(val))
        if not self._playing:
            self._schedule_scrub_render()

    def _read_frame_pair(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if not self._preview_ready():
            return None, None
        pa = self.var_path_a.get().strip()
        if not pa:
            return None, None
        path_a = Path(pa)
        use_seq = (
            self._playing
            and self._cap_a is not None
            and self._seq_next is not None
            and self._frame_index == self._seq_next
        )
        if use_seq:
            ra, fa = self._cap_a.read()
            fb = None
            if self._cap_b is not None:
                rb, fb = self._cap_b.read()
                if not rb:
                    fb = None
            if not ra:
                return None, None
            return fa, fb

        fa = ow.read_preview_frame_bgr(path_a, self._meta_a, self._frame_index)
        fb = None
        pb = self.var_path_b.get().strip()
        if pb and Path(pb).is_file():
            fb = ow.read_preview_frame_bgr(Path(pb), self._meta_b, self._frame_index)
        return fa, fb

    def _update_diff_labels(self, fa: np.ndarray, fb: Optional[np.ndarray]) -> None:
        noise = int(self.var_prev_noise.get())
        pix_lim = int(self.var_prev_pixel.get())
        if fb is None:
            self.lbl_diff.configure(text=self._t("preview.diff.none_b"))
            self.lbl_swap.configure(text="")
            return
        fb_u = _to_bgr(fb)
        fa_u = _to_bgr(fa)
        if fb_u is None or fa_u is None:
            return
        fb_u = _match_size(fb_u, fa_u.shape[1], fa_u.shape[0])
        cnt = _compare_diff_count(fa_u, fb_u, noise)
        self.lbl_diff.configure(text=self._t("preview.diff.places", n=f"{cnt:,}"))
        # Compare: has_diff = changed_pixels > pixel_thresh
        if cnt > pix_lim:
            self.lbl_swap.configure(
                text=self._t("preview.diff.over"),
                foreground="#1b5e20",
            )
        else:
            self.lbl_swap.configure(
                text=self._t("preview.diff.under"),
                foreground="#b71c1c",
            )

    def _render_frame(self) -> None:
        if not self._preview_ready():
            return
        fa, fb = self._read_frame_pair()
        if fa is None:
            self._playing = False
            self.btn_play.configure(text=self._t("preview.play"))
            return

        fa = _to_bgr(fa)
        if fa is None:
            return
        ho, wo = fa.shape[:2]

        self._update_diff_labels(fa, fb)

        side = self.var_side.get() and fb is not None
        noise = int(self.var_prev_noise.get())

        if side:
            fb_u = _to_bgr(fb)
            if fb_u is not None:
                fb_u = _match_size(fb_u, wo, ho)
                left = fa.copy()
                right = fb_u.copy()
                if self.var_overlay.get():
                    left = _apply_diff_overlay(left, fb_u, noise, 0.5)
                    right = _apply_diff_overlay(fb_u, fa, noise, 0.5)
                cv2.putText(left, "A", (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 0), 2)
                cv2.putText(right, "B", (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (60, 60, 255), 2)
                out = np.hstack([left, right])
            else:
                out = fa
                side = False
        else:
            out = fa.copy()
            if fb is not None and self.var_overlay.get():
                fb_u = _to_bgr(fb)
                if fb_u is not None:
                    fb_u = _match_size(fb_u, wo, ho)
                    out = _apply_diff_overlay(out, fb_u, noise, 0.5)

        rgb = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
        out_h, out_w = out.shape[:2]
        self.update_idletasks()
        tw = max(320, int(self.vid_canvas.winfo_width()) - 4)
        th = max(160, int(self.vid_canvas.winfo_height()) - 4)
        scale = min(tw / out_w, th / out_h, 1.0)
        nw = max(1, int(out_w * scale))
        nh = max(1, int(out_h * scale))
        if nw != out_w or nh != out_h:
            rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)

        cw = max(1, int(self.vid_canvas.winfo_width()))
        ch = max(1, int(self.vid_canvas.winfo_height()))
        ix0 = max(0, (cw - nw) // 2)
        iy0 = max(0, (ch - nh) // 2)

        self.vid_canvas.delete("all")
        self._photo = ImageTk.PhotoImage(image=Image.fromarray(rgb))
        self.vid_canvas.create_image(ix0, iy0, anchor=tk.NW, image=self._photo)

        if self._total > 0 and self._frame_index + 1 < self._total:
            self._seq_next = self._frame_index + 1
        else:
            self._seq_next = None

        self.lbl_info.configure(
            text=self._t(
                "preview.frame_info",
                i=self._frame_index,
                last=max(0, self._total - 1),
            )
        )

    def shutdown(self) -> None:
        self._playing = False
        if self._auto_load_after is not None:
            try:
                self.after_cancel(self._auto_load_after)
            except tk.TclError:
                pass
            self._auto_load_after = None
        self._release_caps()

    def release_caps_for_paths(self, paths: Sequence[Path]) -> None:
        """Video-Handles freigeben, wenn Vorschau A/B betroffene Dateien geöffnet hat."""
        if not paths:
            return
        targets: Set[str] = set()
        for raw in paths:
            try:
                targets.add(str(raw.resolve()).casefold())
            except OSError:
                targets.add(str(raw).casefold())

        def _hit(var: tk.StringVar) -> bool:
            p = var.get().strip()
            if not p:
                return False
            try:
                return str(Path(p).resolve()).casefold() in targets
            except OSError:
                return p.casefold() in targets

        if not (_hit(self.var_path_a) or _hit(self.var_path_b)):
            return
        self._playing = False
        if self._auto_load_after is not None:
            try:
                self.after_cancel(self._auto_load_after)
            except tk.TclError:
                pass
            self._auto_load_after = None
        self._release_caps()


class OxcoTaggerPreview(ttk.Frame):
    """Kleine Einzelvideo-Vorschau im Autotagger — Person im Clip erkennen."""

    CANVAS_W = 320
    CANVAS_H = 180
    _SCRUB_DEBOUNCE_MS = 120
    _SCRUB_MAX_WIDTH = 640

    def __init__(self, parent: tk.Misc, host_app: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self._host = host_app
        self._cap: Any = None
        self._meta: Optional[ow.PreviewVideoMeta] = None
        self._photo: Optional[ImageTk.PhotoImage] = None
        self._path: Optional[Path] = None
        self._frame_index = 0
        self._total = 0
        self._playing = False
        self._updating_scale = False
        self._scrub_after: Optional[str] = None
        self._last_tick = 0.0

        self.columnconfigure(0, weight=1)

        self._lf = ttk.LabelFrame(self, text=self._t("flow.tagger_preview"))
        self._lf.grid(row=0, column=0, sticky="nsew")
        self._lf.columnconfigure(0, weight=1)

        self.lbl_name = ttk.Label(self._lf, text="", wraplength=self.CANVAS_W)
        self.lbl_name.grid(row=0, column=0, sticky="w", padx=4, pady=(4, 2))

        self.canvas = tk.Canvas(
            self._lf, width=self.CANVAS_W, height=self.CANVAS_H, bg="#1a1a1a", highlightthickness=0
        )
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=4, pady=2)

        ctl = ttk.Frame(self._lf)
        ctl.grid(row=2, column=0, sticky="ew", padx=4, pady=2)
        self.btn_play = ttk.Button(
            ctl, text=self._t("preview.play"), command=self._toggle_play, state="disabled", width=8
        )
        self.btn_play.pack(side="left")
        self.lbl_frame = ttk.Label(ctl, text="")
        self.lbl_frame.pack(side="right")

        self.scale = ttk.Scale(self._lf, from_=0, to=1, orient="horizontal", command=self._on_scale)
        self.scale.grid(row=3, column=0, sticky="ew", padx=4, pady=(2, 4))
        self.scale.configure(state="disabled")

        self._hint = ttk.Label(
            self._lf,
            text=self._t("flow.tagger_preview_hint"),
            foreground="gray",
            wraplength=self.CANVAS_W,
        )
        self._hint.grid(row=4, column=0, sticky="w", padx=4, pady=(0, 4))

        self._show_placeholder()

    def _t(self, key: str, **kwargs: Any) -> str:
        if self._host is not None and hasattr(self._host, "tr"):
            return self._host.tr(key, **kwargs)
        return key

    def apply_i18n(self) -> None:
        self._lf.configure(text=self._t("flow.tagger_preview"))
        self._hint.configure(text=self._t("flow.tagger_preview_hint"))
        self.btn_play.configure(text=self._t("preview.pause") if self._playing else self._t("preview.play"))
        if self._path is None:
            self._show_placeholder()

    def load_path(self, path: Optional[Path]) -> None:
        self._stop_playback()
        self._release_cap()
        self._path = None
        if path is None or not path.is_file():
            self._show_placeholder()
            return

        self._path = path
        self.lbl_name.configure(text=path.name)
        self._meta = ow.probe_preview_media(path)
        self._total = self._meta.frame_count if self._meta is not None else self._probe_frame_count(path)
        if self._total <= 0:
            self._path = None
            self._meta = None
            self._show_placeholder(self._t("preview.err_open_a"))
            return

        last = max(0, self._total - 1)
        self._frame_index = min(last, max(0, self._total // 4))
        self._updating_scale = True
        try:
            self.scale.configure(to=max(1, last), state="normal")
            self.scale.set(self._frame_index)
        finally:
            self._updating_scale = False
        self.btn_play.configure(state="normal", text=self._t("preview.play"))
        self._render_frame()

    def release_file(self) -> None:
        """Datei-Handle freigeben (Windows-Sperre), letztes Bild bleibt sichtbar."""
        self._stop_playback()
        self._release_cap()
        self._path = None
        self._meta = None
        self.scale.configure(state="disabled")
        self.btn_play.configure(state="disabled", text=self._t("preview.play"))

    def release_if_paths(self, paths: Sequence[Path]) -> None:
        if self._path is None:
            self._stop_playback()
            self._release_cap()
            return
        targets: Set[str] = set()
        for raw in paths:
            try:
                targets.add(str(raw.resolve()).casefold())
            except OSError:
                targets.add(str(raw).casefold())
        try:
            mine = str(self._path.resolve()).casefold()
        except OSError:
            mine = str(self._path).casefold()
        if mine in targets:
            self.release_file()

    def shutdown(self) -> None:
        self._stop_playback()
        self._cancel_scrub_render()
        self._release_cap()
        self._path = None
        self._meta = None

    def _stop_playback(self) -> None:
        self._playing = False

    def _cancel_scrub_render(self) -> None:
        if self._scrub_after is not None:
            try:
                self.after_cancel(self._scrub_after)
            except tk.TclError:
                pass
            self._scrub_after = None

    def _schedule_scrub_render(self) -> None:
        self._cancel_scrub_render()
        self._scrub_after = self.after(self._SCRUB_DEBOUNCE_MS, self._scrub_render)

    def _scrub_render(self) -> None:
        self._scrub_after = None
        self._render_frame()

    def _release_cap(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _probe_frame_count(self, path: Path) -> int:
        cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
        try:
            if not cap.isOpened():
                return 0
            return int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        finally:
            cap.release()

    def _read_frame_bgr(self, path: Path, frame_index: int) -> Optional[np.ndarray]:
        return ow.read_preview_frame_bgr(
            path,
            self._meta,
            frame_index,
            max_width=self._SCRUB_MAX_WIDTH,
        )

    def _show_placeholder(self, msg: Optional[str] = None) -> None:
        self._release_cap()
        self._path = None
        self.canvas.delete("all")
        self._photo = None
        text = msg or self._t("flow.tagger_preview_no_file")
        self.lbl_name.configure(text="")
        self.lbl_frame.configure(text="")
        self.scale.configure(state="disabled")
        self.btn_play.configure(state="disabled", text=self._t("preview.play"))
        cw, ch = self.CANVAS_W, self.CANVAS_H
        self.canvas.create_text(cw // 2, ch // 2, text=text, fill="#888888", width=cw - 20)

    def _toggle_play(self) -> None:
        if self._path is None:
            return
        self._playing = not self._playing
        self.btn_play.configure(text=self._t("preview.pause") if self._playing else self._t("preview.play"))
        if self._playing:
            self._release_cap()
            self._cap = cv2.VideoCapture(str(self._path), cv2.CAP_FFMPEG)
            if not self._cap.isOpened():
                self._release_cap()
                self._playing = False
                self.btn_play.configure(text=self._t("preview.play"))
                return
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._frame_index)
            self._last_tick = time.time()
            self._tick()
        else:
            self._release_cap()

    def _tick(self) -> None:
        if not self._playing or self._cap is None or self._path is None:
            return
        min_interval = 1.0 / 12.0
        elapsed = time.time() - self._last_tick
        if elapsed < min_interval:
            self.after(max(1, int((min_interval - elapsed) * 1000)), self._tick)
            return
        self._last_tick = time.time()

        ok, frame = self._cap.read()
        if not ok or frame is None:
            self._playing = False
            self._release_cap()
            self.btn_play.configure(text=self._t("preview.play"))
            return

        if self._total > 0:
            self._frame_index = min(self._frame_index + 1, self._total - 1)

        self._updating_scale = True
        try:
            self.scale.set(self._frame_index)
        finally:
            self._updating_scale = False

        bgr = _to_bgr(frame)
        if bgr is not None:
            self._paint_frame(bgr)
        if self._frame_index >= max(0, self._total - 1):
            self._playing = False
            self._release_cap()
            self.btn_play.configure(text=self._t("preview.play"))
            return
        self.after(1, self._tick)

    def _on_scale(self, val: str) -> None:
        if self._updating_scale or self._path is None:
            return
        self._frame_index = int(float(val))
        if self._playing and self._cap is not None:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._frame_index)
            return
        self._schedule_scrub_render()

    def _paint_frame(self, bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        fh, fw = rgb.shape[:2]
        scale = min(self.CANVAS_W / fw, self.CANVAS_H / fh, 1.0)
        nw = max(1, int(fw * scale))
        nh = max(1, int(fh * scale))
        if nw != fw or nh != fh:
            rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)

        ix0 = max(0, (self.CANVAS_W - nw) // 2)
        iy0 = max(0, (self.CANVAS_H - nh) // 2)
        self.canvas.delete("all")
        self._photo = ImageTk.PhotoImage(image=Image.fromarray(rgb))
        self.canvas.create_image(ix0, iy0, anchor=tk.NW, image=self._photo)
        last = max(0, self._total - 1)
        self.lbl_frame.configure(text=self._t("preview.frame_info", i=self._frame_index, last=last))

    def _render_frame(self) -> None:
        if self._path is None:
            return
        if self._playing and self._cap is not None:
            return
        bgr = self._read_frame_bgr(self._path, self._frame_index)
        if bgr is None:
            self._show_placeholder(self._t("preview.err_open_a"))
            return
        self._paint_frame(bgr)
