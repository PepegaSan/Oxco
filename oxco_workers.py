"""
Hintergrundlogik für Oxco: Compare (lokal compare.py), Bitrate-Jobs
(angelehnt an Videobitratechanger), Autotagger (angelehnt an Watchdog tagger).
"""

from __future__ import annotations

import configparser
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import oxco_i18n as oi

# Exit codes from compare.py (GUI / automation)
COMPARE_EXIT_OK = 0
COMPARE_EXIT_ERROR = 1
COMPARE_EXIT_PARTIAL_EXPORT = 3


def _oxco_root() -> Path:
    """Application folder: next to the .exe when frozen (PyInstaller), else this package directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


OXCO_ROOT = _oxco_root()


# —— Bitrate (Videobitratechanger — vereinfacht) ——

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".wmv",
    ".webm",
    ".m4v",
    ".ts",
    ".flv",
}


def _is_partial_temp_video(name: str) -> bool:
    """Oxco schreibt FFmpeg-Zwischendateien als *.partial.mp4 — nicht scannen/taggen."""
    return ".partial" in name.lower()


def wait_until_file_stable(
    path: Path,
    *,
    min_stable_seconds: float = 1.25,
    poll_seconds: float = 0.25,
    max_wait_seconds: float = 600.0,
    min_size_bytes: int = 1,
    stop_event: Optional[threading.Event] = None,
) -> bool:
    """
    Wartet, bis Größe und mtime mindestens ``min_stable_seconds`` lang unverändert bleiben.
    So greifen Scan/Konvertierung/Tagger nicht auf noch wachsende Dateien zu (Producer → Consumer).
    """
    deadline = time.monotonic() + max_wait_seconds
    last: Optional[Tuple[int, int]] = None
    stable_since: Optional[float] = None
    while time.monotonic() < deadline:
        if stop_event is not None and stop_event.is_set():
            return False
        try:
            st = path.stat()
        except OSError:
            time.sleep(poll_seconds)
            last = None
            stable_since = None
            continue
        if st.st_size < min_size_bytes:
            time.sleep(poll_seconds)
            last = None
            stable_since = None
            continue
        sig = (st.st_size, int(st.st_mtime_ns))
        now = time.monotonic()
        if sig != last:
            last = sig
            stable_since = now
        elif stable_since is not None and (now - stable_since) >= min_stable_seconds:
            return True
        time.sleep(poll_seconds)
    return False


RULE_ORDER = [2160, 1440, 1080, 720, 480, 360, 0]
BUILTIN_PRESETS: Dict[str, Dict[int, int]] = {
    "Standard": {2160: 12000, 1440: 8000, 1080: 5000, 720: 2800, 480: 1500, 360: 900, 0: 700},
    "Leicht reduziert": {2160: 8000, 1440: 6000, 1080: 4000, 720: 2000, 480: 1000, 360: 800, 0: 700},
    "Reduziert": {2160: 6000, 1440: 4000, 1080: 3000, 720: 1500, 480: 800, 360: 600, 0: 500},
}


def run_ffprobe(path: Path) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_entries",
        "stream=width,height,bit_rate",
        "-select_streams",
        "v:0",
        "-show_entries",
        "format=bit_rate",
        str(path),
    ]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode != 0:
        return None, None, None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None, None, None
    streams = payload.get("streams") or []
    video_stream = streams[0] if streams else None
    if not video_stream:
        return None, None, None
    width = int(video_stream["width"]) if video_stream.get("width") is not None else None
    height = int(video_stream["height"]) if video_stream.get("height") is not None else None
    stream_bitrate_raw = video_stream.get("bit_rate")
    format_bitrate_raw = (payload.get("format") or {}).get("bit_rate")
    bitrate_bps = None
    for raw in (stream_bitrate_raw, format_bitrate_raw):
        if raw is None:
            continue
        try:
            bitrate_bps = int(raw)
            break
        except (TypeError, ValueError):
            continue
    kbps = int(bitrate_bps / 1000) if bitrate_bps and bitrate_bps > 0 else None
    return width, height, kbps


def pick_rule_for_short_side(width: int, height: int, rules: Dict[int, int]) -> int:
    """Wählt die Bitrate-Zeile nach der kürzeren Kantenlänge.

    Hochkant (z. B. 1080×1920) soll dieselbe Stufe wie Quer-1080p nutzen, nicht die Zeile der
    längeren Kante (1920 → fälschlich 1440p/4K).
    """
    short_side = min(int(width), int(height))
    for threshold in sorted(rules.keys(), reverse=True):
        if short_side >= threshold:
            return rules[threshold]
    return rules[min(rules.keys())]


def estimate_sizes(source_size_bytes: int, source_kbps: int, target_kbps: int) -> Tuple[int, int, float]:
    if source_size_bytes <= 0 or source_kbps <= 0 or target_kbps <= 0:
        return source_size_bytes, 0, 0.0
    ratio = min(1.0, target_kbps / source_kbps)
    estimated_output = int(source_size_bytes * ratio)
    saved = max(0, source_size_bytes - estimated_output)
    saved_pct = (saved / source_size_bytes) * 100.0 if source_size_bytes > 0 else 0.0
    return estimated_output, saved, saved_pct


@dataclass
class VideoRow:
    path: Path
    width: int
    height: int
    source_kbps: Optional[int]
    target_rule_kbps: Optional[int]
    effective_target_kbps: Optional[int]
    action: str
    reason: str


def iter_video_files(folder: Path, recursive: bool) -> List[Path]:
    pattern = "**/*" if recursive else "*"
    files: List[Path] = []
    for p in folder.glob(pattern):
        if not p.is_file() or p.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if _is_partial_temp_video(p.name):
            continue
        files.append(p)
    files.sort()
    return files


def analyze_single_file(file_path: Path, rules: Dict[int, int], only_lower: bool) -> VideoRow:
    if not wait_until_file_stable(file_path):
        return VideoRow(
            path=file_path,
            width=0,
            height=0,
            source_kbps=None,
            target_rule_kbps=None,
            effective_target_kbps=None,
            action="skip",
            reason="Datei noch nicht fertig (Timeout)",
        )
    width, height, source_kbps = run_ffprobe(file_path)
    if not width or not height:
        return VideoRow(
            path=file_path,
            width=0,
            height=0,
            source_kbps=None,
            target_rule_kbps=None,
            effective_target_kbps=None,
            action="skip",
            reason="Auflösung nicht lesbar",
        )
    rule = pick_rule_for_short_side(width, height, rules)
    if source_kbps is None:
        return VideoRow(
            path=file_path,
            width=width,
            height=height,
            source_kbps=None,
            target_rule_kbps=rule,
            effective_target_kbps=None,
            action="skip",
            reason="Bitrate unbekannt",
        )
    effective_target = min(source_kbps, rule)
    if only_lower and effective_target >= source_kbps:
        action = "skip"
        reason = "Schon niedrig genug"
    else:
        action = "convert"
        reason = "Reduzieren"
    return VideoRow(
        path=file_path,
        width=width,
        height=height,
        source_kbps=source_kbps,
        target_rule_kbps=rule,
        effective_target_kbps=effective_target,
        action=action,
        reason=reason,
    )


def scan_folder_parallel(
    folder: Path,
    recursive: bool,
    rules: Dict[int, int],
    only_lower: bool,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> List[VideoRow]:
    files = iter_video_files(folder, recursive)
    if not files:
        return []
    rows_map: Dict[Path, VideoRow] = {}
    workers = min(8, max(2, (os.cpu_count() or 4)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(analyze_single_file, fp, rules, only_lower): fp for fp in files
        }
        processed = 0
        total = len(files)
        for future in as_completed(future_map):
            fp = future_map[future]
            try:
                rows_map[fp] = future.result()
            except Exception:
                rows_map[fp] = VideoRow(
                    path=fp,
                    width=0,
                    height=0,
                    source_kbps=None,
                    target_rule_kbps=None,
                    effective_target_kbps=None,
                    action="skip",
                    reason="Scan-Fehler",
                )
            processed += 1
            if progress_cb and (processed % 16 == 0 or processed == total):
                progress_cb(processed, total)
    return [rows_map[p] for p in files]


def build_ffmpeg_cmd(
    src: Path,
    dst: Path,
    target_kbps: int,
    codec: str,
    audio_mode: str,
) -> List[str]:
    codec = (codec or "libx264").strip()
    cmd: List[str] = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(src),
        "-c:v",
        codec,
        "-b:v",
        f"{target_kbps}k",
        "-maxrate",
        f"{target_kbps}k",
        "-bufsize",
        f"{target_kbps * 2}k",
    ]
    if codec in {"h264_nvenc", "hevc_nvenc"}:
        cmd.extend(
            [
                "-rc:v",
                "vbr",
                "-cq:v",
                "23",
                "-preset",
                "p5",
                "-profile:v",
                "high" if codec == "h264_nvenc" else "main",
            ]
        )
    if audio_mode == "aac_128k":
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    else:
        cmd.extend(["-c:a", "copy"])
    if dst.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        cmd.extend(["-movflags", "+faststart"])
    cmd.append(str(dst))
    return cmd


def is_valid_output_video(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    w, h, _ = run_ffprobe(path)
    return bool(w and h)


def _try_delete_bitrate_source(
    src: Path,
    out_file: Path,
    log: Callable[[str], None],
    ui_lang: str,
) -> None:
    """Nach erfolgreicher Konvertierung: Original löschen (nur wenn von Ausgabedatei verschieden)."""
    try:
        src_res = src.resolve()
        out_res = out_file.resolve()
        if src_res == out_res:
            return
        if not src_res.is_file():
            return
        src_res.unlink()
        lang = oi.normalize_lang(ui_lang)
        log(oi.tr(lang, "log.br_src_deleted", name=src.name))
    except OSError as e:
        lang = oi.normalize_lang(ui_lang)
        log(oi.tr(lang, "log.br_src_delete_fail", name=src.name, err=e))


# —— Compare: settings.ini patchen und Subprozess (lokal im Oxco-Ordner) ——


def compare_root() -> Path:
    return OXCO_ROOT


def compare_script_path() -> Path:
    return OXCO_ROOT / "compare.py"


def compare_settings_path() -> Path:
    return OXCO_ROOT / "settings.ini"


def read_settings_ini(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_settings_ini(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def br_codec_to_compare_ffmpeg_encoder(br_codec: str) -> str:
    """Oxco Bitrate-Codec (Filter) → compare.py SETTINGS.ffmpeg_encoder Schlüssel."""
    c = (br_codec or "").strip().lower()
    return {
        "libx264": "cpu",
        "libx265": "cpu_hevc",
        "h264_nvenc": "nvidia_h264",
        "hevc_nvenc": "nvidia_hevc",
    }.get(c, "nvidia_h264")


def apply_compare_overrides(
    ini_text: str,
    *,
    final_export_dir: str,
    language: str,
    buffer_seconds: float,
    pixel_noise: int,
    changed_pixels: int,
    changed_pixels_max: int = 0,
    enable_ffmpeg: bool,
    ffmpeg_target: str,
    enable_davinci: bool,
    davinci_timeout: int,
    export_avoid_overwrite: bool,
    davinci_api_path: str,
    davinci_render_preset: str,
    davinci_exe_path: str = "",
    davinci_startup_wait_seconds: int = 20,
    ffmpeg_encoder: str = "",
) -> str:
    """Nur relevante Schlüssel setzen; EDL-Ausgaben bleiben aus (0)."""
    cfg = configparser.ConfigParser()
    cfg.read_string(ini_text)
    if not cfg.has_section("SETTINGS"):
        cfg.add_section("SETTINGS")
    if not cfg.has_section("PATHS"):
        cfg.add_section("PATHS")
    cfg.set("SETTINGS", "language", language[:2].lower() if language else "de")
    cfg.set("SETTINGS", "buffer_seconds", str(buffer_seconds))
    cfg.set("SETTINGS", "pixel_noise_threshold", str(int(pixel_noise)))
    cfg.set("SETTINGS", "changed_pixels_threshold", str(int(changed_pixels)))
    cfg.set(
        "SETTINGS",
        "changed_pixels_max_threshold",
        str(max(0, int(changed_pixels_max))),
    )
    cfg.set("SETTINGS", "enable_ffmpeg_export", "1" if enable_ffmpeg else "0")
    cfg.set("SETTINGS", "ffmpeg_export_target", ffmpeg_target if ffmpeg_target in ("both", "source", "deepfake") else "both")
    cfg.set("SETTINGS", "enable_davinci_export", "1" if enable_davinci else "0")
    cfg.set("SETTINGS", "davinci_render_timeout_seconds", str(max(0, int(davinci_timeout))))
    cfg.set("SETTINGS", "enable_fullcheck_edl", "0")
    cfg.set("SETTINGS", "enable_autodelete_edl", "0")
    cfg.set("SETTINGS", "export_avoid_overwrite", "1" if export_avoid_overwrite else "0")
    cfg.set("PATHS", "final_export_dir", final_export_dir.strip())
    preset = (davinci_render_preset or "").strip() or "AutoCutPreset"
    cfg.set("SETTINGS", "davinci_render_preset", preset)
    cfg.set("PATHS", "davinci_api_path", (davinci_api_path or "").strip())
    cfg.set("PATHS", "davinci_exe_path", (davinci_exe_path or "").strip())
    cfg.set(
        "SETTINGS",
        "davinci_startup_wait_seconds",
        str(max(0, min(600, int(davinci_startup_wait_seconds)))),
    )
    enc = (ffmpeg_encoder or "").strip().lower()
    if enc:
        cfg.set("SETTINGS", "ffmpeg_encoder", enc)
    buf = io.StringIO()
    cfg.write(buf)
    return buf.getvalue()


def update_compare_ini_language_and_davinci(
    ini_path: Path,
    *,
    language: str,
    davinci_api_path: str,
    davinci_render_preset: str,
    davinci_exe_path: str = "",
    davinci_startup_wait_seconds: int = 20,
) -> bool:
    """Schreibt Sprache, DaVinci-Pfade und Render-Preset dauerhaft in settings.ini (Kommentare gehen verloren)."""
    try:
        cfg = configparser.ConfigParser()
        if ini_path.is_file():
            cfg.read(ini_path, encoding="utf-8")
        if not cfg.has_section("SETTINGS"):
            cfg.add_section("SETTINGS")
        if not cfg.has_section("PATHS"):
            cfg.add_section("PATHS")
        lang = (language or "de").strip().lower()[:2]
        if lang not in ("de", "en"):
            lang = "de"
        cfg.set("SETTINGS", "language", lang)
        preset = (davinci_render_preset or "").strip() or "AutoCutPreset"
        cfg.set("SETTINGS", "davinci_render_preset", preset)
        cfg.set("PATHS", "davinci_api_path", (davinci_api_path or "").strip())
        cfg.set("PATHS", "davinci_exe_path", (davinci_exe_path or "").strip())
        cfg.set(
            "SETTINGS",
            "davinci_startup_wait_seconds",
            str(max(0, min(600, int(davinci_startup_wait_seconds)))),
        )
        buf = io.StringIO()
        cfg.write(buf)
        write_settings_ini(ini_path, buf.getvalue())
        return True
    except OSError:
        return False


def run_compare_subprocess(
    source: str,
    deepfake: str,
    patched_ini_text: str,
    log_line: Callable[[str], None],
    done: Callable[[int, Optional[str]], None],
    register_proc: Optional[Callable[[Optional[subprocess.Popen]], None]] = None,
    retry_export_only: bool = False,
) -> None:
    project = compare_root()
    compare_py = compare_script_path()
    ini_path = compare_settings_path()

    if not compare_py.is_file():
        done(1, f"compare.py fehlt im Oxco-Ordner: {compare_py}")
        return
    if not ini_path.is_file():
        done(1, f"settings.ini fehlt: {ini_path} (Vorlage settings.example.ini nach settings.ini kopieren.)")
        return

    backup = read_settings_ini(ini_path)
    try:
        write_settings_ini(ini_path, patched_ini_text)
    except OSError as e:
        done(1, f"settings.ini konnte nicht geschrieben werden: {e}")
        return

    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--oxco-compare", source, deepfake, "--auto"]
    else:
        cmd = [sys.executable, str(compare_py), source, deepfake, "--auto"]
    if retry_export_only:
        cmd.append("--retry-export-only")
    log_line(f"[Oxco] Arbeitsverzeichnis: {project}")
    log_line(f"[Oxco] Befehl: {' '.join(cmd)}")

    def _thread() -> None:
        rc = 1
        err: Optional[str] = None
        proc: Optional[subprocess.Popen] = None
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(project),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if register_proc:
                register_proc(proc)
            if proc.stdout is not None:
                try:
                    for line in proc.stdout:
                        log_line(line.rstrip("\n"))
                except Exception:
                    pass
            w = proc.wait()
            rc = int(w) if w is not None else 1
        except Exception as e:
            err = str(e)
            rc = 1
        finally:
            if register_proc:
                register_proc(None)
            try:
                write_settings_ini(ini_path, backup)
                log_line("[Oxco] settings.ini wiederhergestellt.")
            except OSError as e:
                log_line(f"[Oxco] WARNUNG: settings.ini nicht wiederhergestellt: {e}")
            done(rc, err)

    threading.Thread(target=_thread, daemon=True).start()


# —— Compare Ordner-Listen (Dual-Tab) ——


@dataclass
class CompareFileEntry:
    path: Path
    rel: str
    size: int
    mtime: float
    duration_sec: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    probe_ok: bool = False


COMPARE_SIGNATURE_PALETTE: Tuple[str, ...] = (
    "#dceefb",
    "#fde2e2",
    "#d9f2d9",
    "#fdecd9",
    "#e8dcf8",
    "#d9f2ec",
    "#fce4f3",
    "#eef6d9",
    "#dce4f8",
    "#f6eed9",
    "#d9eef6",
    "#f0d9f6",
)
COMPARE_TAG_UNKNOWN = "cmp_probe_unknown"
COMPARE_TAG_MATCH = "cmp_match_orig"


def probe_compare_media(path: Path) -> Tuple[Optional[float], Optional[int], Optional[int]]:
    """Laufzeit (s) und Video-Auflösung via ffprobe, oder (None, None, None)."""
    if not shutil.which("ffprobe"):
        return None, None, None
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_entries",
        "format=duration",
        "-show_entries",
        "stream=width,height",
        "-select_streams",
        "v:0",
        str(path),
    ]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode != 0:
        return None, None, None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None, None, None
    duration: Optional[float] = None
    fmt_dur = (payload.get("format") or {}).get("duration")
    if fmt_dur is not None:
        try:
            duration = float(fmt_dur)
        except (TypeError, ValueError):
            duration = None
    streams = payload.get("streams") or []
    video_stream = streams[0] if streams else None
    width: Optional[int] = None
    height: Optional[int] = None
    if video_stream:
        if video_stream.get("width") is not None:
            try:
                width = int(video_stream["width"])
            except (TypeError, ValueError):
                width = None
        if video_stream.get("height") is not None:
            try:
                height = int(video_stream["height"])
            except (TypeError, ValueError):
                height = None
    if duration is None or width is None or height is None:
        return None, None, None
    return duration, width, height


def enrich_compare_entry_probe(entry: CompareFileEntry) -> None:
    duration, width, height = probe_compare_media(entry.path)
    if duration is None or width is None or height is None:
        entry.probe_ok = False
        entry.duration_sec = None
        entry.width = None
        entry.height = None
        return
    entry.duration_sec = duration
    entry.width = width
    entry.height = height
    entry.probe_ok = True


def compare_match_key(entry: CompareFileEntry) -> Optional[str]:
    """Abgleich-Schlüssel wie in der UI (angezeigte Länge + Auflösung)."""
    if not entry.probe_ok or entry.duration_sec is None:
        return None
    dur_label = fmt_compare_duration(entry.duration_sec)
    if entry.width is None or entry.height is None:
        return dur_label
    return f"{dur_label}|{entry.width}x{entry.height}"


def compare_media_signature(entry: CompareFileEntry) -> Optional[str]:
    return compare_match_key(entry)


def compare_signature_tag_map(
    orig: Sequence[CompareFileEntry],
    df: Sequence[CompareFileEntry],
) -> Dict[str, str]:
    """Signatur → Treeview-Tag (gleiche Signatur = gleiche Farbe in beiden Listen)."""
    sigs: set[str] = set()
    for e in orig:
        s = compare_media_signature(e)
        if s:
            sigs.add(s)
    for e in df:
        s = compare_media_signature(e)
        if s:
            sigs.add(s)
    return {sig: f"cmp_sig_{i}" for i, sig in enumerate(sorted(sigs))}


def compare_pick_deepfake_for_original(
    orig: CompareFileEntry,
    df_entries: Sequence[CompareFileEntry],
    pattern_text: str,
) -> Optional[CompareFileEntry]:
    """Erstes passendes Deepfake (Länge/Auflösung); Reihenfolge = ``df_entries``."""
    ranked = compare_rank_deepfakes_for_original(orig, df_entries, pattern_text)
    return ranked[0] if ranked else None


def compare_rank_deepfakes_for_original(
    orig: CompareFileEntry,
    df_entries: Sequence[CompareFileEntry],
    pattern_text: str,
) -> List[CompareFileEntry]:
    """Deepfakes passend zum Original (UI-Länge + Auflösung); Token zuerst."""
    candidates: List[CompareFileEntry] = []
    match_key = compare_match_key(orig)
    if match_key:
        candidates = [e for e in df_entries if compare_match_key(e) == match_key]
    if (
        not candidates
        and orig.probe_ok
        and orig.duration_sec is not None
        and orig.width is not None
        and orig.height is not None
    ):
        candidates = [
            e
            for e in df_entries
            if e.probe_ok
            and e.duration_sec is not None
            and e.width == orig.width
            and e.height == orig.height
            and abs(e.duration_sec - orig.duration_sec) <= 2.0
        ]
    if not candidates:
        return []
    token = extract_pattern_match(orig.path.stem, pattern_text)
    if token:
        token_hits = [e for e in candidates if token in e.path.stem]
        if token_hits:
            token_keys = {compare_path_key(e.path) for e in token_hits}
            rest = [e for e in candidates if compare_path_key(e.path) not in token_keys]
            return token_hits + rest
    return list(candidates)


def compare_paths_equal(a: Path, b: Path) -> bool:
    return compare_path_key(a) == compare_path_key(b)


def compare_path_key(path: Path) -> str:
    try:
        return str(path.resolve()).casefold()
    except OSError:
        return str(path).casefold()


def fmt_compare_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes}:{int(secs):02d}"


def fmt_compare_resolution(width: Optional[int], height: Optional[int]) -> str:
    if width is None or height is None:
        return "—"
    return f"{width}×{height}"


def scan_compare_folder(root: Path, recursive: bool) -> List[CompareFileEntry]:
    """Videos unter ``root`` (optional rekursiv), mit relativem Pfad und Metadaten."""
    if not root.is_dir():
        return []
    root = root.resolve()
    out: List[CompareFileEntry] = []
    for p in iter_video_files(root, recursive):
        try:
            st = p.stat()
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:
                rel = p.name
            out.append(
                CompareFileEntry(path=p, rel=rel, size=int(st.st_size), mtime=float(st.st_mtime))
            )
        except OSError:
            continue
    return out


def _compare_duration_sort_key(entry: CompareFileEntry, *, desc: bool = False) -> Tuple[int, float, str]:
    missing = 1 if entry.duration_sec is None else 0
    dur = entry.duration_sec if entry.duration_sec is not None else 0.0
    name = entry.path.name.casefold()
    if desc:
        return (missing, -dur, name)
    return (missing, dur, name)


def _compare_duration_group_key(entry: CompareFileEntry) -> str:
    if entry.duration_sec is None:
        return "—"
    return fmt_compare_duration(round(entry.duration_sec, 1))


def sort_compare_entries(entries: List[CompareFileEntry], mode: str) -> List[CompareFileEntry]:
    mode = (mode or "date_desc").strip().lower()
    if mode == "date_asc":
        return sorted(entries, key=lambda e: e.mtime)
    if mode == "date_desc":
        return sorted(entries, key=lambda e: e.mtime, reverse=True)
    if mode == "size_asc":
        return sorted(entries, key=lambda e: e.size)
    if mode == "size_desc":
        return sorted(entries, key=lambda e: e.size, reverse=True)
    if mode == "duration_asc":
        return sorted(entries, key=lambda e: _compare_duration_sort_key(e))
    if mode == "duration_desc":
        return sorted(entries, key=lambda e: _compare_duration_sort_key(e, desc=True))
    if mode == "name_desc":
        return sorted(entries, key=lambda e: e.path.name.casefold(), reverse=True)
    return sorted(entries, key=lambda e: e.path.name.casefold())


def _compare_folder_group_key(rel: str) -> str:
    parent = Path(rel.replace("\\", "/")).parent
    s = parent.as_posix()
    return s if s and s != "." else "."


def _compare_date_group_key(mtime: float) -> str:
    import datetime as _dt

    return _dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")


def _compare_letter_group_key(name: str) -> str:
    stem = Path(name).stem
    if not stem:
        return "#"
    c = stem[0].upper()
    return c if c.isalnum() else "#"


def _compare_group_duration_stat(items: Sequence[CompareFileEntry]) -> Tuple[int, float]:
    durs = [e.duration_sec for e in items if e.duration_sec is not None]
    if not durs:
        return (1, 0.0)
    return (0, max(durs))


def group_compare_entries(
    entries: List[CompareFileEntry], group: str, *, sort_mode: str = ""
) -> List[Tuple[str, List[CompareFileEntry]]]:
    group = (group or "none").strip().lower()
    sort_mode = (sort_mode or "").strip().lower()
    if group in ("none", ""):
        return [("", list(entries))]
    buckets: Dict[str, List[CompareFileEntry]] = {}
    for e in entries:
        if group == "folder":
            key = _compare_folder_group_key(e.rel)
        elif group == "date":
            key = _compare_date_group_key(e.mtime)
        elif group == "letter":
            key = _compare_letter_group_key(e.path.name)
        elif group == "duration":
            key = _compare_duration_group_key(e)
        else:
            key = ""
        buckets.setdefault(key, []).append(e)
    items_pairs = list(buckets.items())
    if sort_mode in ("duration_desc", "duration_asc"):
        desc = sort_mode == "duration_desc"

        def _grp_dur_key(item: Tuple[str, List[CompareFileEntry]]) -> Tuple[int, float, str]:
            label, grp_items = item
            missing, dur = _compare_group_duration_stat(grp_items)
            return (missing, -dur if desc else dur, label.casefold())

        items_pairs = sorted(items_pairs, key=_grp_dur_key)
        return [(label, sort_compare_entries(grp_items, sort_mode)) for label, grp_items in items_pairs]
    if group == "duration":

        def _dur_bucket_order(item: Tuple[str, List[CompareFileEntry]]) -> Tuple[int, float, str]:
            label, grp_items = item
            if label == "—":
                return (1, 0.0, label)
            missing, dur = _compare_group_duration_stat(grp_items)
            return (missing, dur, label)

        items_pairs = sorted(items_pairs, key=_dur_bucket_order)
    else:
        items_pairs = sorted(items_pairs, key=lambda kv: kv[0].casefold())
    return items_pairs


# —— Autotagger (Watchdog tagger — Einmal-Lauf, ein Profil) ——


def parse_suffix_list(raw_text: str) -> List[str]:
    values: List[str] = []
    for part in raw_text.split(","):
        value = part.strip()
        if not value:
            continue
        if not value.startswith("_"):
            value = f"_{value}"
        values.append(value.lower())
    return values


# Drop-Suffixe: wie Keep per Komma; zusätzlich ``r:…`` = Regex nur am **Ende** des Namens (Flags re.I).
DropStripEntry = Union[str, re.Pattern]


def parse_drop_suffix_entries(raw_text: str) -> List[DropStripEntry]:
    """Literale wie ``parse_suffix_list`` oder ``r:regex`` (muss das Namensende treffen, ``\\Z`` wird angehängt)."""
    out: List[DropStripEntry] = []
    for part in raw_text.split(","):
        p = part.strip()
        if not p:
            continue
        if len(p) >= 2 and p[:2].lower() == "r:":
            expr = p[2:].lstrip()
            if not expr:
                continue
            try:
                out.append(re.compile(expr + r"\Z", re.IGNORECASE))
            except re.error:
                continue
            continue
        value = p
        if not value.startswith("_"):
            value = f"_{value}"
        out.append(value.lower())
    return out


def compare_export_tag_suffix(
    buffer_seconds: float,
    noise_thresh: int,
    pixel_thresh: int,
    changed_pixels_max: int = 0,
) -> str:
    """Wie ``compare.compare_export_filename_tag`` (Kleinbuchstaben für Suffix-Vergleich)."""
    b = f"{float(buffer_seconds):g}".replace(".", "-")
    s = f"_b{b}_n{int(noise_thresh)}_p{int(pixel_thresh)}"
    mx = int(changed_pixels_max) if changed_pixels_max else 0
    if mx > 0:
        s += f"_m{mx}"
    return s.lower()


def build_automatic_tagger_drop_entries(
    buffer_seconds: float,
    noise_thresh: int,
    pixel_thresh: int,
    changed_pixels_max: int,
    bitrate_output_suffix: str,
) -> List[DropStripEntry]:
    """Compare-/DaVinci-/Bitrate-Endungen — immer beim Taggen entfernen (nicht über Drop-Suffixe)."""
    entries: List[DropStripEntry] = []
    entries.append(
        compare_export_tag_suffix(
            buffer_seconds, noise_thresh, pixel_thresh, changed_pixels_max
        )
    )
    entries.append(re.compile(r"_davinci_export\Z", re.IGNORECASE))
    # Andere Compare-Läufe (andere Schwellen) am Namensende
    entries.append(re.compile(r"_b[\d][\w.-]*_n\d+_p\d+(?:_m\d+)?\Z", re.IGNORECASE))
    sfx = (bitrate_output_suffix or "_bitrate").strip()
    if not sfx.startswith("_"):
        sfx = f"_{sfx}"
    if sfx:
        entries.append(sfx.lower())
    return entries


def extract_pattern_match(original_stem: str, pattern_text: str) -> str:
    pattern_text = (pattern_text or "YYMMDDHHmmSS").strip()
    pattern_text = pattern_text.replace("{", "").replace("}", "")
    token_map = {
        "YYYY": r"(?P<YYYY>\d{4})",
        "YY": r"(?P<YY>\d{2})",
        "MM": r"(?P<MM>\d{2})",
        "DD": r"(?P<DD>\d{2})",
        "HH": r"(?P<HH>\d{2})",
        "mm": r"(?P<mm>\d{2})",
        "SS": r"(?P<SS>\d{2})",
        "DIGITS": r"(?P<DIGITS>\d+)",
        "LETTERS": r"(?P<LETTERS>[A-Za-z]+)",
        "ALNUM": r"(?P<ALNUM>[A-Za-z0-9]+)",
        "ANY": r"(?P<ANY>.+?)",
    }
    token_regex = re.escape(pattern_text)
    for token in ["YYYY", "YY", "MM", "DD", "HH", "mm", "SS", "DIGITS", "LETTERS", "ALNUM", "ANY"]:
        token_regex = token_regex.replace(re.escape(token), token_map[token])
    match = re.search(token_regex, original_stem)
    if not match:
        if pattern_text in original_stem:
            return pattern_text
        return ""
    return match.group(0)


def pick_suffix_to_keep(original_stem: str, keep_csv: str, drop_csv: str) -> str:
    stem_lower = original_stem.lower()
    keep_list = parse_suffix_list(keep_csv)
    drop_entries = parse_drop_suffix_entries(drop_csv)
    drop_literals = [e for e in drop_entries if isinstance(e, str)]
    for suffix in keep_list:
        if stem_lower.endswith(suffix):
            if suffix in drop_literals:
                return ""
            return original_stem[-len(suffix) :]
    for entry in drop_entries:
        if isinstance(entry, str):
            if stem_lower.endswith(entry):
                return ""
        else:
            m = entry.search(original_stem)
            if m and m.end() == len(original_stem):
                return ""
    return ""


def should_ignore_file(original_stem: str, ignore_csv: str) -> bool:
    stem_lower = original_stem.lower()
    for suffix in parse_suffix_list(ignore_csv):
        if stem_lower.endswith(suffix):
            return True
    return False


def remove_date_token(original_stem: str, pattern_text: str) -> str:
    found = extract_pattern_match(original_stem, pattern_text)
    if not found:
        return original_stem.strip("_- ")
    cleaned = original_stem.replace(found, "")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("_- ")


def remove_trailing_suffixes(
    stem: str,
    keep_csv: str,
    drop_csv: str,
    *,
    extra_drop_entries: Optional[Sequence[DropStripEntry]] = None,
) -> str:
    keep_list = parse_suffix_list(keep_csv)
    drop_entries = parse_drop_suffix_entries(drop_csv)
    all_entries: List[DropStripEntry] = list(keep_list) + list(drop_entries)
    if extra_drop_entries:
        all_entries.extend(extra_drop_entries)
    current = stem
    changed = True
    while changed and current:
        changed = False
        lower_current = current.lower()
        for entry in all_entries:
            if isinstance(entry, str):
                if lower_current.endswith(entry):
                    current = current[: -len(entry)].rstrip("_- ")
                    changed = True
                    break
            else:
                m = entry.search(current)
                if m and m.end() == len(current):
                    current = current[: m.start()].rstrip("_- ")
                    changed = True
                    break
    return current


def make_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.stem
    suffix = path.suffix
    folder = path.parent
    counter = 1
    while True:
        candidate = folder / f"{base}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _win_send_path_to_recycle_bin_shell(path: Path) -> bool:
    import ctypes
    from ctypes import wintypes

    p = str(path.resolve())
    if not os.path.isfile(p):
        return False

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 0x0003
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010

    op = SHFILEOPSTRUCTW()
    op.hwnd = 0
    op.wFunc = FO_DELETE
    op.pFrom = p + "\0\0"
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return rc == 0 and not op.fAnyOperationsAborted and not path.is_file()


def _win_send_path_to_recycle_bin_powershell(path: Path) -> bool:
    p = str(path.resolve()).replace("'", "''")
    script = (
        "Add-Type -AssemblyName Microsoft.VisualBasic; "
        f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{p}', "
        "'OnlyErrorDialogs', 'SendToRecycleBin')"
    )
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            creationflags=flags,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and not path.is_file()


def _win_send_path_to_recycle_bin(path: Path) -> bool:
    if _win_send_path_to_recycle_bin_shell(path):
        return True
    return _win_send_path_to_recycle_bin_powershell(path)


def path_looks_file_locked(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with open(path, "r+b"):
            pass
        return False
    except OSError as e:
        if getattr(e, "winerror", None) == 32:
            return True
        return e.errno in (13, 16)


def send_paths_to_recycle_bin(paths: Sequence[Path]) -> Tuple[List[Path], Optional[str]]:
    """Dateien in den Papierkorb (Windows). Gibt gelöschte Pfade zurück."""
    if sys.platform != "win32":
        return [], "unsupported"
    deleted: List[Path] = []
    for raw in paths:
        try:
            p = raw.resolve()
        except OSError:
            continue
        if not p.is_file():
            continue
        if _win_send_path_to_recycle_bin(p):
            deleted.append(p)
    return deleted, None


def build_tagger_target_name(
    stem: str,
    tag: str,
    profile_name: str,
    keep_csv: str,
    drop_csv: str,
    pattern_text: str,
    *,
    auto_drop_entries: Optional[Sequence[DropStripEntry]] = None,
) -> str:
    found = extract_pattern_match(stem, pattern_text)
    if not found:
        raise ValueError("Muster nicht im Dateinamen")
    kept_suffix = pick_suffix_to_keep(stem, keep_csv, drop_csv)
    tag_text = tag.strip()
    # Tag soll das Muster (z. B. YYMMDDHHmmSS) *ersetzen*, nicht ans Ende des restlichen Namens.
    if tag_text:
        base_name = stem.replace(found, tag_text, 1)
    else:
        base_name = remove_date_token(stem, pattern_text)
    base_name = remove_trailing_suffixes(
        base_name, keep_csv, drop_csv, extra_drop_entries=auto_drop_entries
    )
    while "__" in base_name:
        base_name = base_name.replace("__", "_")
    while "--" in base_name:
        base_name = base_name.replace("--", "-")
    base_name = base_name.strip("_- ")
    if tag_text:
        if base_name:
            return f"{base_name}{kept_suffix}.mp4"
        return f"{profile_name}_{tag_text}{kept_suffix}.mp4"
    if base_name:
        return f"{base_name}{kept_suffix}.mp4"
    return f"{profile_name}{kept_suffix}.mp4"


def tagger_process_folder(
    input_dir: Path,
    output_dir: Path,
    *,
    tag: str,
    profile_name: str,
    keep_suffix_csv: str,
    ignore_suffix_csv: str,
    drop_suffix_csv: str,
    pattern_text: str,
    log: Callable[[str], None],
    only_files: Optional[Sequence[Path]] = None,
    ui_lang: str = "de",
    filter_buffer_seconds: float = 2.0,
    filter_noise_threshold: int = 15,
    filter_pixel_threshold: int = 200,
    filter_pixel_max_threshold: int = 0,
    bitrate_output_suffix: str = "_bitrate",
) -> Tuple[int, int]:
    """Process ``.mp4`` in the folder (non-recursive). If ``only_files`` is set, only those paths (must be under input_dir).

    Returns (moved_ok, skipped).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    all_files = sorted(p for p in input_dir.glob("*.mp4") if not _is_partial_temp_video(p.name))
    if only_files:
        want = {p.resolve() for p in only_files}
        files = [p for p in all_files if p.resolve() in want]
        if not files:
            log(oi.tr(ui_lang, "log.tagger_no_sel_match"))
            return 0, 0
    else:
        files = all_files
    auto_drop = build_automatic_tagger_drop_entries(
        filter_buffer_seconds,
        filter_noise_threshold,
        filter_pixel_threshold,
        filter_pixel_max_threshold,
        bitrate_output_suffix,
    )
    ok = 0
    skipped = 0
    for fp in files:
        stem = fp.stem
        if should_ignore_file(stem, ignore_suffix_csv):
            log(f"Übersprungen (Ignore-Suffix): {fp.name}")
            skipped += 1
            continue
        try:
            if not extract_pattern_match(stem, pattern_text):
                log(f"Übersprungen (Muster fehlt): {fp.name}")
                skipped += 1
                continue
            if not wait_until_file_stable(fp):
                log(f"Übersprungen (Datei noch nicht fertig): {fp.name}")
                skipped += 1
                continue
            new_name = build_tagger_target_name(
                stem,
                tag,
                profile_name,
                keep_suffix_csv,
                drop_suffix_csv,
                pattern_text,
                auto_drop_entries=auto_drop,
            )
            target = output_dir / new_name
            target = make_unique_path(target)
            shutil.move(str(fp), str(target))
            log(f"OK: {fp.name} → {target.name}")
            ok += 1
        except Exception as e:
            log(f"Fehler bei {fp.name}: {e}")
            skipped += 1
    return ok, skipped


def normalize_tag_route_rules(raw: object) -> List[Tuple[str, str]]:
    """``[{"tag": "...", "folder": "..."}, ...]`` → Liste (tag, folder), leere Einträge weg."""
    out: List[Tuple[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        tag = str(item.get("tag", "")).strip()
        folder = str(item.get("folder", "")).strip()
        if tag and folder:
            out.append((tag, folder))
    return out


def _tag_route_bracket_segments(filename: str) -> List[str]:
    """Inhalte in eckigen Klammern, z. B. ``[Julia Berens]`` → ``Julia Berens``."""
    return [m.group(1).strip() for m in re.finditer(r"\[([^\]]+)\]", filename)]


def _tag_route_inner_label(tag: str) -> str:
    t = tag.strip()
    if t.startswith("[") and t.endswith("]") and len(t) >= 2:
        return t[1:-1].strip()
    return t


def _tag_route_match_pattern(tag: str) -> re.Pattern:
    """Tag im Dateinamen, nicht als Teil eines längeren Namens (Julia ≠ Julia Berens)."""
    escaped = re.escape(tag.strip())
    return re.compile(
        rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])(?!\s+[A-Za-z0-9])",
        re.IGNORECASE,
    )


def pick_tag_route_for_filename(filename: str, rules: Sequence[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    """Längster passender Tag zuerst; Klammer-Inhalt exakt (``[Julia]`` ≠ ``[Julia Berens]``)."""
    ordered = sorted(rules, key=lambda r: len(r[0].strip()), reverse=True)
    segments_fold = [s.casefold() for s in _tag_route_bracket_segments(filename)]

    for tag, folder in ordered:
        tag = tag.strip()
        if not tag:
            continue
        label = _tag_route_inner_label(tag)
        label_fold = label.casefold()
        if segments_fold:
            if label_fold in segments_fold:
                return tag, folder
            continue
        if _tag_route_match_pattern(tag).search(filename):
            return tag, folder
    return None


def tagger_distribute_by_rules(
    source_dir: Path,
    rules: Sequence[Tuple[str, str]],
    log: Callable[[str], None],
    ui_lang: str = "de",
) -> Tuple[int, int, int]:
    """Verschiebt ``.mp4`` aus ``source_dir`` nach Zielordnern je Regel (erster Treffer gewinnt).

    Returns (moved, no_match, errors).
    """
    norm: List[Tuple[str, str]] = []
    for item in rules:
        if isinstance(item, dict):
            tag = str(item.get("tag", "")).strip()
            folder = str(item.get("folder", "")).strip()
        else:
            tag = str(item[0]).strip()
            folder = str(item[1]).strip()
        if tag and folder:
            norm.append((tag, folder))
    if not norm:
        log(oi.tr(ui_lang, "log.tag_route_no_rules"))
        return 0, 0, 0
    if not source_dir.is_dir():
        log(oi.tr(ui_lang, "err.tag_route_out_missing"))
        return 0, 0, 0

    files = sorted(p for p in source_dir.glob("*.mp4") if not _is_partial_temp_video(p.name))
    moved = 0
    no_match = 0
    errors = 0
    for fp in files:
        hit = pick_tag_route_for_filename(fp.name, norm)
        if not hit:
            log(oi.tr(ui_lang, "log.tag_route_no_match", name=fp.name))
            no_match += 1
            continue
        _tag, dest_dir_s = hit
        dest_dir = Path(dest_dir_s)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            target = make_unique_path(dest_dir / fp.name)
            if not wait_until_file_stable(fp):
                log(oi.tr(ui_lang, "log.tag_route_unstable", name=fp.name))
                errors += 1
                continue
            shutil.move(str(fp), str(target))
            log(oi.tr(ui_lang, "log.tag_route_moved", name=fp.name, dest=str(target.parent)))
            moved += 1
        except OSError as e:
            log(oi.tr(ui_lang, "log.tag_route_error", name=fp.name, err=e))
            errors += 1
    return moved, no_match, errors


def convert_video_rows(
    rows: List[VideoRow],
    input_root: Path,
    output_root: Path,
    *,
    suffix: str,
    output_mp4: bool,
    codec: str,
    audio_mode: str,
    stop_event: threading.Event,
    log: Callable[[str], None],
    progress: Callable[[int, int], None],
    delete_source_after_ok: bool = False,
    ui_lang: str = "de",
) -> None:
    jobs = [r for r in rows if r.action == "convert" and r.effective_target_kbps]
    total = len(jobs)
    for idx, row in enumerate(jobs, start=1):
        if stop_event.is_set():
            log("Abbruch durch Benutzer.")
            return
        rel = row.path.relative_to(input_root) if row.path.is_relative_to(input_root) else Path(row.path.name)
        out_parent = output_root / rel.parent
        out_parent.mkdir(parents=True, exist_ok=True)
        planned_ext = ".mp4" if output_mp4 else rel.suffix
        out_name = f"{rel.stem}{suffix}{planned_ext}"
        out_file = out_parent / out_name
        work_out = out_file
        if row.path.resolve() == out_file.resolve():
            work_out = out_file.with_name(f"{out_file.stem}.partial{out_file.suffix}")
        kb = row.effective_target_kbps or 1
        if not wait_until_file_stable(row.path, stop_event=stop_event):
            if stop_event.is_set():
                log("Abbruch durch Benutzer.")
                return
            log(f"Überspringe, Quelle noch nicht fertig: {row.path.name}")
            progress(idx, total)
            continue
        cmd = build_ffmpeg_cmd(row.path, work_out, kb, codec, audio_mode)
        log(f"Konvertiere: {row.path.name} → {kb} kbps")
        completed = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if completed.returncode != 0:
            err = (completed.stderr or "").strip().splitlines()
            log(f"FFmpeg-Fehler {row.path.name}: {err[-1] if err else 'unbekannt'}")
            try:
                if work_out.exists() and work_out.resolve() != out_file.resolve():
                    work_out.unlink()
            except OSError:
                pass
        elif not is_valid_output_video(work_out):
            log(f"Ausgabe ungültig: {row.path.name}")
            try:
                if work_out.exists() and work_out.resolve() != out_file.resolve():
                    work_out.unlink()
            except OSError:
                pass
        else:
            try:
                # Wenn FFmpeg direkt nach out_file schreibt (work_out == out_file), darf out_file
                # nicht vor dem Move gelöscht werden — sonst WinError 2 (Datei nicht gefunden).
                if work_out.resolve() != out_file.resolve():
                    if out_file.exists():
                        out_file.unlink()
                    shutil.move(str(work_out), str(out_file))
            except OSError as e:
                log(f"Verschieben fehlgeschlagen: {e}")
            else:
                log(f"Fertig: {out_file.name}")
                if delete_source_after_ok:
                    _try_delete_bitrate_source(row.path, out_file, log, ui_lang)
        progress(idx, total)
