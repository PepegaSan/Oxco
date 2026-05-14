import cv2
import json
import sys
import os
import shutil
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import configparser
import re
import datetime
import random

TEXTS = {
    'en': {
        'first_run_title': "First Run / Erster Start",
        'first_run_msg': "The file 'settings.ini' was created in the program folder.\n\nPlease open this file, adjust the language (en/de), export settings, and API path if needed, then restart the script.\n\n---\n\nDie Datei 'settings.ini' wurde im Programmordner neu erstellt.\n\nBitte öffne diese Datei, passe bei Bedarf die Sprache (en/de), Exporteinstellungen sowie den Pfad zur API an und starte das Skript danach erneut.",
        'file_dialog_source': "1. Select ORIGINAL Video (Source)",
        'file_dialog_df': "2. Select DEEPFAKE Video",
        'confirm_source_title': "Clarify File Assignment",
        'confirm_source_msg': "Is the following file the ORIGINAL video (Source)?\n\n{name}",
        'abort_double_file_title': "Abort",
        'abort_double_file_msg': "The same file was sent twice. Operation aborted.",
        'cache_step1_title': "Step 1",
        'cache_step1_msg': "File cached for AutoCut:\n{name}\n\nPlease right-click the second file -> Send to -> Deepfake AutoCut.",
        'no_files_sendto': "No files passed via Send To. Starting manual file selection...",
        'abort_not_both': "Abort: Not both videos were selected.",
        'press_enter': "\nPress Enter to exit...",
        'unexpected_error': "\nAn unexpected error occurred: {error}",
        'loading_settings': "Loading settings from settings.ini:",
        'set_buffer': "- Buffer: {val} seconds",
        'set_noise': "- Noise Filter: {val}",
        'set_pixel': "- Pixel Tolerance: {val}",
        'set_pixel_max': "- Pixel ceiling (0=off): {val}",
        'set_davinci': "- DaVinci API Export: {val}",
        'set_davinci_timeout': "- DaVinci render time limit: {val}",
        'davinci_timeout_off': "none (wait until DaVinci finishes)",
        'set_ffmpeg': "- FFmpeg Export: {val}",
        'set_ffmpeg_target': "- FFmpeg renders: {val}",
        'ffmpeg_target_both': "source and deepfake",
        'ffmpeg_target_source': "source only",
        'ffmpeg_target_deepfake': "deepfake only",
        'set_fullcheck': "- FullCheck EDL: {val}",
        'set_export_unique': "- Avoid overwriting video exports (FFmpeg / DaVinci): {val}",
        'on': "On",
        'off': "Off",
        'start_analysis': "\nStarting pixel difference analysis for {frames} frames...",
        'analyzing': "\rAnalyzing: {percent:.1f}% ({current}/{total} frames)",
        'frames_processed': "\n{count} frames processed. Applying filters...",
        'no_diff': "No difference found between the videos.",
        'edl_auto_created': "\nAutoDelete EDL files created:",
        'edl_full_created': "\nFullCheck EDL files created.",
        'all_done': "\nAll operations completed.",
        'compare_exit_partial': (
            "\n[INFO] An enabled export (FFmpeg and/or DaVinci) did not complete successfully. "
            "Exit code 3 — adjust Filters in Oxco and use Retry.\n"
        ),
        'checkpoint_written': "[INFO] Export checkpoint saved (Retry runs export only, no new pixel analysis).\n",
        'checkpoint_write_failed': "[WARN] Could not write export checkpoint: {error}\n",
        'retry_export_start': "[INFO] Retry: export only (EDL / FFmpeg / DaVinci) — same cut as last analysis.\n",
        'retry_export_no_checkpoint': "[ERROR] No export checkpoint. Run a full Compare first (analysis must find differences).\n",
        'retry_export_ck_read_err': "[ERROR] Export checkpoint unreadable: {error}\n",
        'retry_export_path_mismatch': "[ERROR] Checkpoint does not match these two video paths. Run full Compare again.\n",
        'retry_export_missing_file': "[ERROR] Source or deepfake file is missing on disk.\n",
        'retry_export_auto_only': "[ERROR] --retry-export-only is only supported with two paths and --auto (Oxco Retry).\n",
        'manual_res_title': "Manual Resolution Input",
        'manual_res_prompt': "Could not read video resolution.\nPlease enter the resolution manually (e.g., 1920x1080):",
        'manual_res_invalid': "[Info] Invalid input or canceled. Falling back to 1920x1080.",
        'ffmpeg_render': "Rendering {name} via FFmpeg ({codec})...",
        'ffmpeg_progress': "\rProgress: {percent:.1f}% ({frame}/{total} frames)",
        'ffmpeg_error': "\n\n--- FFmpeg Error for {name} ---",
        'ffmpeg_success': "\n-> Successfully created.",
        'davinci_api_missing': "\n[ERROR] DaVinci API (DaVinciResolveScript) not found!",
        'davinci_api_path_searched': "Python explicitly searched in this folder:\n{path}",
        'davinci_api_check_explorer': "Please check in Windows Explorer if this folder and the file 'DaVinciResolveScript.py' actually exist there.",
        'davinci_not_open': "\n[ERROR] DaVinci Resolve Studio must be open before starting this script!",
        'davinci_api_retry': "[INFO] DaVinci scripting API not ready yet; retrying ({n}/{max}, pause {delay}s between checks)...\n",
        'davinci_scriptapp_hint': (
            "[INFO] If this repeats for a long time: use Resolve **Studio** (external scripting is not in the free "
            "version), open a project, and run Resolve + this tool as the same Windows user (not \"Run as admin\" for "
            "only one of them). You can raise SETTINGS → davinci_scriptapp_retry_attempts / "
            "davinci_scriptapp_retry_delay_seconds in settings.ini.\n"
        ),
        'davinci_fallback_skip': "\n[WARN] DaVinci Resolve is not running or the scripting API is unavailable.\nPixel analysis, EDL, and FFmpeg (if enabled) will still run; DaVinci export is skipped.\n",
        'davinci_export_exception': "\n[WARN] DaVinci export failed: {error}\n[INFO] Pixel analysis and any EDL/FFmpeg files written above are still valid.\n",
        'davinci_export_interrupted': "\n[INFO] DaVinci export interrupted or API error while talking to Resolve: {error}\n[INFO] Pixel analysis and any EDL/FFmpeg output above are still valid.\n",
        'davinci_render_no_jobs': "\n[INFO] DaVinci returned no render job info (Resolve may have closed during export).\n",
        'compare_summary_davinci_ok': "[INFO] DaVinci export: completed successfully.\n",
        'compare_summary_davinci_fail': "[INFO] DaVinci export: did not complete (Resolve closed, API error, or timeout). Analysis, EDL, and FFmpeg (if enabled) above are unchanged.\n",
        'davinci_no_project': "\n[ERROR] No open project found in DaVinci Resolve.",
        'davinci_no_project_wait': "[INFO] No open Resolve project yet (typical right after a restart). Retrying ({n}/{max})...\n",
        'davinci_no_project_hint': "[INFO] Tip: Open or create any project in Resolve, then run compare again.\n",
        'davinci_export_start_info': "[INFO] DaVinci export starting (API path: {path})\n",
        'davinci_script_missing': "[WARN] DaVinciResolveScript.py not found:\n{path}\nCheck PATHS → davinci_api_path in settings.ini (Resolve Studio scripting \"Modules\" folder).\n",
        'davinci_sending_data': "\nSending data via API to DaVinci Resolve Studio...",
        'davinci_import_error': "[ERROR] Could not import {path} into Resolve.",
        'davinci_timeline_error': "[ERROR] Could not create a timeline.",
        'davinci_no_valid_scenes': "No valid scenes found to render.",
        'davinci_preset_warning': "\n[WARNING] Could not find render preset '{preset}' in DaVinci!",
        'davinci_preset_fallback': "Rendering will proceed using the last settings used in DaVinci.",
        'davinci_job_created': "Render job for '{name}' created.",
        'davinci_start_render': "Starting hardware rendering in DaVinci Resolve...",
        'davinci_render_running': "-> Rendering in progress! (Progress is now displayed over in the DaVinci Resolve GUI)",
        'davinci_meta_no_resolution': "No resolution in clip metadata.",
        'davinci_meta_parse_error': "[Info] Could not read clip metadata completely: {error}",
        'davinci_render_timeout_exceeded': "DaVinci render exceeded {sec} seconds; export was stopped.",
        'davinci_render_status_failed': "DaVinci render job finished with status: {status}",
        'fps_fallback': "[Info] Could not read a valid FPS from the source video; using 30.",
        'fps_ffprobe': "[INFO] Using stream FPS {fps} from ffprobe for analysis and DaVinci timeline (OpenCV reported {opencv}).\n",
        'fps_ffprobe_only': "[INFO] Using stream FPS {fps} from ffprobe (OpenCV had no valid rate).\n",
        'fps_r_vs_avg': "[INFO] ffprobe r_frame_rate={r:.6g} vs avg_frame_rate={avg:.6g} — using nominal r_frame_rate for timeline (avg is often wrong on NTSC MP4).\n",
        'fps_prefer_opencv': "[INFO] ffprobe avg_frame_rate={avg:.6g} disagrees with OpenCV {ocv:.6g} — using OpenCV (typical when avg is mis-muxed).\n",
        'davinci_timeline_fps': "[INFO] DaVinci timeline frame rate: {rate} (same as compare analysis; Resolve clip metadata was {clip}).\n",
        'davinci_set_failed': "[WARN] DaVinci API refused setting {key}={val!r} on {where} (timeline may keep previous FPS until this succeeds).\n",
        'davinci_fps_verify': "[INFO] DaVinci FPS read-back — Project (Master Settings dropdown): {proj} | Active timeline object: {tl}\n",
        'davinci_ffprobe_wh_warn': "[INFO] ffprobe did not report width/height for the deepfake file. Enter frame size when prompted (or place ffprobe.exe next to the app). Master FPS is applied before import only when resolution is known.\n",
        'davinci_master_preset': "[INFO] Resolve Master after pre-import preset: timelineFrameRate read-back={fps} | {w}x{h}\n",
        'davinci_fps_locked_hint': "[WARN] Master timeline FPS is still {read} (wanted {target}). Resolve often locks FPS once the Media Pool already has clips — use an empty pool, a new project, or a project template that matches the target rate.\n",
        'davinci_temp_project': "[INFO] Using temporary Resolve project '{temp}' for this export (Master FPS can be set with no timelines). Your project '{orig}' will be reopened when finished.\n",
        'davinci_temp_project_failed': "[WARN] Could not create a temporary Resolve project; continuing in the current project — Master FPS may stay locked if timelines or pool clips already exist.\n",
        'davinci_restored_project': "[INFO] Restored Resolve project '{name}'.\n",
        'davinci_restore_failed': "[WARN] Could not switch back to Resolve project '{name}': {error}\n",
        'davinci_render_never_started': "[WARN] DaVinci did not report an active render within {sec}s (script would otherwise exit too early and files can be truncated). Check Deliver page; retry export.\n",
        'davinci_autostart_already': "[INFO] DaVinci Resolve is already running.\n",
        'davinci_autostart_start': "[INFO] DaVinci Resolve is not running. Starting (PATHS → davinci_exe_path)...\n",
        'davinci_autostart_wait': "[INFO] Waiting {sec} seconds for Resolve (SETTINGS → davinci_startup_wait_seconds)...\n",
        'davinci_autostart_err': "[ERROR] Could not start DaVinci Resolve: {e}\n",
        'davinci_autostart_path': "[INFO] Executable path was: {path}\n",
        'davinci_autostart_no_exe': "[WARN] DaVinci export is on, but PATHS → davinci_exe_path is empty or missing — start Resolve Studio manually.\n",
        'davinci_autostart_exe_missing': "[WARN] Resolve.exe not found (check PATHS → davinci_exe_path):\n{path}\n",
        'davinci_autostart_skip_os': "[INFO] Auto-starting Resolve is only implemented on Windows (same as watcher tasklist); start Resolve manually if needed.\n",
        'sync_warn_framecount': (
            "[WARN] OpenCV frame count differs — source: {src}, deepfake: {df}. "
            "Compare always pairs by frame index (0,1,2,…); decoding stops when either file ends. "
            "Different trims, re-encodes, or duplicate frames can look like \"differences\" especially toward the end.\n"
        ),
        'sync_warn_duration': (
            "[WARN] Container duration (ffprobe) differs — source: {src:.3f}s, deepfake: {df:.3f}s (Δ{delta:.3f}s). "
            "If lengths do not match, index pairing is not guaranteed to align with wall-clock time.\n"
        ),
        'sync_warn_fps': (
            "[WARN] OpenCV FPS differs — source: {src:.6g}, deepfake: {df:.6g}. "
            "Analysis FPS is taken from the source file only; the other track may drift perceptually vs. indices.\n"
        ),
        'sync_warn_truncated': (
            "[WARN] Decoding stopped after {got} frame pairs; source container reported {expected}. "
            "Usually the shorter or harder-to-decode file ended first — check that both exports cover the same range.\n"
        ),
        'sync_info_no_ffprobe_duration': "[INFO] ffprobe not found — skipping container duration cross-check (place ffprobe.exe next to the app or on PATH).\n",
    },
    'de': {
        'first_run_title': "Erster Start / First Run",
        'first_run_msg': "Die Datei 'settings.ini' wurde im Programmordner neu erstellt.\n\nBitte öffne diese Datei, passe bei Bedarf die Sprache (en/de), Exporteinstellungen sowie den Pfad zur API an und starte das Skript danach erneut.\n\n---\n\nThe file 'settings.ini' was created in the program folder.\n\nPlease open this file, adjust the language (en/de), export settings, and API path if needed, then restart the script.",
        'file_dialog_source': "1. ORIGINAL-Video auswählen (Source)",
        'file_dialog_df': "2. DEEPFAKE-Video auswählen",
        'confirm_source_title': "Dateizuordnung klären",
        'confirm_source_msg': "Ist folgende Datei das ORIGINAL-Video (Source)?\n\n{name}",
        'abort_double_file_title': "Abbruch",
        'abort_double_file_msg': "Die gleiche Datei wurde zweimal gesendet. Vorgang abgebrochen.",
        'cache_step1_title': "Schritt 1",
        'cache_step1_msg': "Datei für AutoCut gemerkt:\n{name}\n\nBitte klicke nun auf die zweite Datei -> Senden an -> Deepfake AutoCut.",
        'no_files_sendto': "Keine Dateien über Senden an übergeben. Starte manuelle Dateiauswahl...",
        'abort_not_both': "Abbruch: Es wurden nicht beide Videos ausgewählt.",
        'press_enter': "\nDrücke Enter zum Beenden...",
        'unexpected_error': "\nEin unerwarteter Fehler ist aufgetreten: {error}",
        'loading_settings': "Lade Einstellungen aus settings.ini:",
        'set_buffer': "- Puffer: {val} Sekunden",
        'set_noise': "- Rausch-Filter: {val}",
        'set_pixel': "- Pixel-Toleranz: {val}",
        'set_pixel_max': "- Pixel-Obergrenze (0=aus): {val}",
        'set_davinci': "- DaVinci API Export: {val}",
        'set_davinci_timeout': "- DaVinci Render-Zeitlimit: {val}",
        'davinci_timeout_off': "keins (warten bis DaVinci fertig ist)",
        'set_ffmpeg': "- FFmpeg Export: {val}",
        'set_ffmpeg_target': "- FFmpeg rendert: {val}",
        'ffmpeg_target_both': "Original und Deepfake",
        'ffmpeg_target_source': "nur Original",
        'ffmpeg_target_deepfake': "nur Deepfake",
        'set_fullcheck': "- FullCheck EDL: {val}",
        'set_export_unique': "- Video-Exporte nicht überschreiben (FFmpeg / DaVinci): {val}",
        'on': "An",
        'off': "Aus",
        'start_analysis': "\nStarte Pixel-Differenz-Analyse für {frames} Frames...",
        'analyzing': "\rAnalysiere: {percent:.1f}% ({current}/{total} Frames)",
        'frames_processed': "\n{count} Frames verarbeitet. Wende Filter an...",
        'no_diff': "Kein Unterschied zwischen den Videos gefunden.",
        'edl_auto_created': "\nAutoDelete EDL Dateien erstellt:",
        'edl_full_created': "\nFullCheck EDL Dateien erstellt.",
        'all_done': "\nAlle Vorgänge abgeschlossen.",
        'compare_exit_partial': (
            "\n[INFO] Mindestens ein aktivierter Export (FFmpeg und/oder DaVinci) ist fehlgeschlagen. "
            "Exit-Code 3 — im Oxco-Tab „Filter“ anpassen und „Erneut“ nutzen.\n"
        ),
        'checkpoint_written': "[INFO] Export-Checkpoint gespeichert („Erneut“ = nur Export, keine neue Pixelanalyse).\n",
        'checkpoint_write_failed': "[WARN] Checkpoint konnte nicht geschrieben werden: {error}\n",
        'retry_export_start': "[INFO] Erneut: nur Export (EDL / FFmpeg / DaVinci) — gleicher Schnitt wie letzte Analyse.\n",
        'retry_export_no_checkpoint': "[FEHLER] Kein Export-Checkpoint. Zuerst vollständigen Compare starten (Analyse muss Unterschiede finden).\n",
        'retry_export_ck_read_err': "[FEHLER] Export-Checkpoint nicht lesbar: {error}\n",
        'retry_export_path_mismatch': "[FEHLER] Checkpoint passt nicht zu diesen beiden Videopfaden. Compare erneut vollständig ausführen.\n",
        'retry_export_missing_file': "[FEHLER] Original- oder Deepfake-Datei fehlt auf der Platte.\n",
        'retry_export_auto_only': "[FEHLER] --retry-export-only nur mit zwei Pfaden und --auto (Oxco „Erneut“).\n",
        'ffmpeg_render': "Rendere {name} über FFmpeg ({codec})...",
        'ffmpeg_progress': "\rFortschritt: {percent:.1f}% ({frame}/{total} Frames)",
        'ffmpeg_error': "\n\n--- FFmpeg Fehler bei {name} ---",
        'ffmpeg_success': "\n-> Erfolgreich erstellt.",
        'manual_res_title': "Manuelle Auflösungseingabe",
        'manual_res_prompt': "Video-Auflösung konnte nicht ausgelesen werden.\nBitte manuell eingeben (z.B. 1920x1080):",
        'manual_res_invalid': "[Info] Ungültige Eingabe oder abgebrochen. Fallback auf 1920x1080.",
        'davinci_api_missing': "\n[FEHLER] DaVinci API (DaVinciResolveScript) nicht gefunden!",
        'davinci_api_path_searched': "Python hat explizit in diesem Ordner gesucht:\n{path}",
        'davinci_api_check_explorer': "Bitte prüfe im Windows Explorer, ob dieser Ordner und die Datei 'DaVinciResolveScript.py' dort wirklich existieren.",
        'davinci_not_open': "\n[FEHLER] DaVinci Resolve Studio muss geöffnet sein, bevor dieses Skript startet!",
        'davinci_api_retry': "[INFO] DaVinci-Scripting-API noch nicht bereit; erneuter Versuch ({n}/{max}, Pause {delay}s)...\n",
        'davinci_scriptapp_hint': (
            "[INFO] Wenn das lange so bleibt: **Resolve Studio** nutzen (kein externes Scripting in der Gratis-Version), "
            "ein Projekt oeffnen, Resolve und dieses Tool unter dem **gleichen** Windows-Benutzer starten "
            "(nicht nur eines \"als Administrator\"). In settings.ini kannst du "
            "davinci_scriptapp_retry_attempts / davinci_scriptapp_retry_delay_seconds erhoehen.\n"
        ),
        'davinci_fallback_skip': "\n[WARN] DaVinci Resolve laeuft nicht oder die Scripting-API ist nicht verfuegbar.\nPixel-Analyse, EDL und FFmpeg (falls aktiv) laufen trotzdem; DaVinci-Export wird uebersprungen.\n",
        'davinci_export_exception': "\n[WARN] DaVinci-Export fehlgeschlagen: {error}\n[INFO] Pixel-Analyse und bereits geschriebene EDL-/FFmpeg-Dateien bleiben gueltig.\n",
        'davinci_export_interrupted': "\n[INFO] DaVinci-Export unterbrochen oder API-Fehler bei Resolve: {error}\n[INFO] Pixel-Analyse und EDL-/FFmpeg-Ausgabe oben bleiben gueltig.\n",
        'davinci_render_no_jobs': "\n[INFO] DaVinci lieferte keine Render-Job-Infos (Resolve evtl. waehrend des Exports beendet).\n",
        'compare_summary_davinci_ok': "[INFO] DaVinci-Export: erfolgreich abgeschlossen.\n",
        'compare_summary_davinci_fail': "[INFO] DaVinci-Export: nicht abgeschlossen (Resolve geschlossen, API-Fehler oder Timeout). Analyse, EDL und FFmpeg (falls aktiv) oben bleiben unveraendert.\n",
        'davinci_no_project': "\n[FEHLER] Kein offenes Projekt in DaVinci Resolve gefunden.",
        'davinci_no_project_wait': "[INFO] Noch kein offenes Resolve-Projekt (häufig direkt nach Neustart). Wiederhole ({n}/{max})...\n",
        'davinci_no_project_hint': "[INFO] Tipp: In Resolve ein Projekt öffnen oder anlegen, danach Compare erneut starten.\n",
        'davinci_export_start_info': "[INFO] Starte DaVinci-Export (API-Pfad: {path})\n",
        'davinci_script_missing': "[WARN] DaVinciResolveScript.py nicht gefunden:\n{path}\nBitte PATHS → davinci_api_path in settings.ini prüfen (Studio-Ordner \"Modules\").\n",
        'davinci_sending_data': "\nSende Daten über API an DaVinci Resolve Studio...",
        'davinci_import_error': "[FEHLER] Konnte {path} nicht in Resolve importieren.",
        'davinci_timeline_error': "[FEHLER] Konnte keine Timeline erstellen.",
        'davinci_no_valid_scenes': "Keine validen Szenen zum Rendern gefunden.",
        'davinci_preset_warning': "\n[WARNUNG] Konnte Render-Preset '{preset}' in DaVinci nicht finden!",
        'davinci_preset_fallback': "Es wird mit den zuletzt in DaVinci genutzten Einstellungen gerendert.",
        'davinci_job_created': "Render-Job für '{name}' erstellt.",
        'davinci_start_render': "Starte Hardware-Rendering in DaVinci Resolve...",
        'davinci_render_running': "-> Rendering läuft! (Der Fortschritt wird dir jetzt drüben in der DaVinci Resolve GUI angezeigt)",
        'davinci_meta_no_resolution': "Keine Auflösung in den Clip-Metadaten.",
        'davinci_meta_parse_error': "[Info] Clip-Metadaten nicht vollständig lesbar: {error}",
        'davinci_render_timeout_exceeded': "DaVinci-Rendering länger als {sec} Sekunden; Export wurde gestoppt.",
        'davinci_render_status_failed': "DaVinci-Render abgeschlossen mit Status: {status}",
        'fps_fallback': "[Info] Keine gültige FPS aus dem Quellvideo lesbar; verwende 30.",
        'fps_ffprobe': "[INFO] Stream-FPS {fps} von ffprobe fuer Analyse und DaVinci-Timeline (OpenCV meldete {opencv}).\n",
        'fps_ffprobe_only': "[INFO] Stream-FPS {fps} von ffprobe (OpenCV hatte keine gueltige Rate).\n",
        'fps_r_vs_avg': "[INFO] ffprobe r_frame_rate={r:.6g} vs avg_frame_rate={avg:.6g} — nutze nominales r_frame_rate (avg oft falsch bei NTSC-MP4).\n",
        'fps_prefer_opencv': "[INFO] ffprobe avg_frame_rate={avg:.6g} passt nicht zu OpenCV {ocv:.6g} — nutze OpenCV (typisch bei falsch gemuxtem avg).\n",
        'davinci_timeline_fps': "[INFO] DaVinci-Timeline: {rate} (wie Compare-Analyse; Resolve-Clip-Metadaten: {clip}).\n",
        'davinci_set_failed': "[WARN] DaVinci-API lehnt {key}={val!r} auf {where} ab (Timeline behält evtl. alte FPS).\n",
        'davinci_fps_verify': "[INFO] DaVinci FPS zur Kontrolle — Projekt (Master/Dropdown): {proj} | Timeline-Objekt: {tl}\n",
        'davinci_ffprobe_wh_warn': "[INFO] ffprobe liefert keine Breite/Höhe für die Deepfake-Datei. Bitte Auflösung eingeben (oder ffprobe.exe neben die App legen). Master-FPS wird nur vor dem Import gesetzt, wenn die Auflösung bekannt ist.\n",
        'davinci_master_preset': "[INFO] Resolve Master nach Vorab-Preset: timelineFrameRate (read-back)={fps} | {w}x{h}\n",
        'davinci_fps_locked_hint': "[WARN] Master-Timeline-FPS bleibt {read} (Ziel {target}). Resolve sperrt die FPS oft, sobald der Media Pool schon Clips hat — leerer Pool, neues Projekt oder passende Projektvorlage.\n",
        'davinci_temp_project': "[INFO] Temporäres Resolve-Projekt '{temp}' für diesen Export (Master-FPS ohne bestehende Timelines). Danach wird '{orig}' wieder geöffnet.\n",
        'davinci_temp_project_failed': "[WARN] Temporäres Resolve-Projekt nicht erstellbar; es wird das aktuelle Projekt genutzt — Master-FPS kann gesperrt bleiben, wenn schon Timelines/Clips existieren.\n",
        'davinci_restored_project': "[INFO] Resolve-Projekt '{name}' wieder geöffnet.\n",
        'davinci_restore_failed': "[WARN] Zurück zu Resolve-Projekt '{name}' nicht möglich: {error}\n",
        'davinci_render_never_started': "[WARN] Kein laufender Render-Meldung innerhalb {sec}s (sonst bricht das Skript zu früh ab — Datei unvollständig). Deliver prüfen; Export wiederholen.\n",
        'davinci_autostart_already': "[INFO] DaVinci Resolve läuft bereits.\n",
        'davinci_autostart_start': "[INFO] DaVinci Resolve läuft nicht. Starte Programm (PATHS → davinci_exe_path)...\n",
        'davinci_autostart_wait': "[INFO] Warte {sec} Sekunden auf Resolve (SETTINGS → davinci_startup_wait_seconds)...\n",
        'davinci_autostart_err': "[FEHLER] DaVinci Resolve konnte nicht gestartet werden: {e}\n",
        'davinci_autostart_path': "[INFO] Verwendeter Pfad: {path}\n",
        'davinci_autostart_no_exe': "[WARN] DaVinci-Export ist an, aber PATHS → davinci_exe_path fehlt — bitte Resolve Studio manuell starten.\n",
        'davinci_autostart_exe_missing': "[WARN] Resolve.exe nicht gefunden (PATHS → davinci_exe_path prüfen):\n{path}\n",
        'davinci_autostart_skip_os': "[INFO] Auto-Start von Resolve nur unter Windows (wie watcher tasklist); ggf. Resolve manuell starten.\n",
        'sync_warn_framecount': (
            "[WARN] OpenCV-Frameanzahl weicht ab — Original: {src}, Deepfake: {df}. "
            "Compare koppelt immer nach Frame-Index (0,1,2,…); das Dekodieren endet, sobald eine Datei zu Ende ist. "
            "Unterschiedliche Schnitte, Re-Encodes oder doppelte Frames wirken dann oft wie „Unterschiede“, besonders gegen Ende.\n"
        ),
        'sync_warn_duration': (
            "[WARN] Container-Laufzeit (ffprobe) weicht ab — Original: {src:.3f}s, Deepfake: {df:.3f}s (Δ{delta:.3f}s). "
            "Bei unterschiedlicher Länge stimmt die Index-Kopplung nicht zwingend mit der Echtzeit überein.\n"
        ),
        'sync_warn_fps': (
            "[WARN] OpenCV-FPS weicht ab — Original: {src:.6g}, Deepfake: {df:.6g}. "
            "Die Analyse-FPS kommt nur aus dem Original; die andere Spur kann sich zur Index-Zählung anders anfühlen.\n"
        ),
        'sync_warn_truncated': (
            "[WARN] Dekodierung endete nach {got} Frame-Paaren; der Container meldete fürs Original {expected}. "
            "Typisch: kürzeres Deepfake-Export, Lesefehler oder anderer In/Out-Point — prüfen, ob beide Clips dieselbe Spanne haben.\n"
        ),
        'sync_info_no_ffprobe_duration': "[INFO] ffprobe nicht gefunden — Container-Laufzeit wird nicht verglichen (ffprobe.exe neben die App oder im PATH).\n",
    }
}

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _read_ini_file(config, path):
    """Read settings.ini as UTF-8 (matches Control Center). Fallback: default ConfigParser.read."""
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            config.read_file(fh)
    except Exception:
        config.read(path)


def _ini_bool(config, section, option, fallback=False):
    """ConfigParser boolean, tolerant of odd editor values."""
    if not config.has_option(section, option):
        return fallback
    try:
        return config.getboolean(section, option)
    except ValueError:
        v = config.get(section, option, fallback="").strip().lower()
        return v in ("1", "yes", "true", "on", "ja")


def _ini_int_clamped(config, section, option, lo, hi, fallback):
    try:
        return max(lo, min(hi, config.getint(section, option, fallback=fallback)))
    except (ValueError, TypeError):
        return fallback


def _ini_float_clamped(config, section, option, lo, hi, fallback):
    try:
        return max(lo, min(hi, config.getfloat(section, option, fallback=fallback)))
    except (ValueError, TypeError):
        return fallback


def _is_resolve_running_win():
    """Windows: same check as Deepfake_smoother_premium watcher.py (tasklist)."""
    if sys.platform != "win32":
        return False
    try:
        kw = {}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Resolve.exe", "/FO", "CSV", "/NH"],
            shell=False,
            **kw,
        ).decode("utf-8", errors="ignore")
        return "Resolve.exe" in output
    except Exception:
        return False


def ensure_resolve_running_for_compare(davinci_exe_path, startup_wait_sec, lang):
    """
    If Resolve is not running, start davinci_exe_path (Windows: os.startfile like watcher.py),
    then sleep startup_wait_sec (SETTINGS.davinci_startup_wait_seconds).
    """
    if sys.platform != "win32":
        print(TEXTS[lang]["davinci_autostart_skip_os"], flush=True)
        return
    if _is_resolve_running_win():
        print(TEXTS[lang]["davinci_autostart_already"], flush=True)
        return
    exe = (davinci_exe_path or "").strip()
    if not exe:
        print(TEXTS[lang]["davinci_autostart_no_exe"], flush=True)
        return
    if not os.path.isfile(exe):
        print(TEXTS[lang]["davinci_autostart_exe_missing"].format(path=exe), flush=True)
        return
    print(TEXTS[lang]["davinci_autostart_start"], flush=True)
    try:
        os.startfile(exe)  # type: ignore[attr-defined]
    except Exception as e:
        print(TEXTS[lang]["davinci_autostart_err"].format(e=e), flush=True)
        print(TEXTS[lang]["davinci_autostart_path"].format(path=exe), flush=True)
        return
    wait_sec = max(0, min(600, int(startup_wait_sec)))
    if wait_sec > 0:
        print(TEXTS[lang]["davinci_autostart_wait"].format(sec=wait_sec), flush=True)
        time.sleep(wait_sec)


def _eval_fraction_fps(s):
    s = str(s).strip()
    if not s or s == "0/0":
        return None
    if "/" in s:
        parts = s.split("/", 1)
        try:
            num, den = float(parts[0]), float(parts[1])
            if den == 0:
                return None
            return num / den
        except (ValueError, TypeError):
            return None
    try:
        return float(s)
    except ValueError:
        return None


_STANDARD_CFR_ANCHORS = (
    23.976023976023978,
    24.0,
    25.0,
    29.97002997002997,
    30.0,
    48.0,
    50.0,
    59.94005994005994,
    60.0,
)


def _near_standard_cfr(fps, tol=0.06):
    if fps is None or fps <= 0:
        return False
    try:
        f = float(fps)
    except (TypeError, ValueError):
        return False
    for v in _STANDARD_CFR_ANCHORS:
        if abs(f - v) < tol:
            return True
    return False


def probe_video_stream_fps_rates(ffprobe_exe, video_path):
    """
    Returns (r_frame_rate_fps, avg_frame_rate_fps) — each may be None.
    For 29.97 NTSC, r_frame_rate is usually 30000/1001; avg_frame_rate is often mis-reported as ~24.
    """
    if not ffprobe_exe or not video_path or not os.path.isfile(video_path):
        return None, None
    try:
        kw = {}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        completed = subprocess.run(
            [
                ffprobe_exe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=avg_frame_rate,r_frame_rate",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            **kw,
        )
    except (subprocess.SubprocessError, OSError):
        return None, None
    if completed.returncode != 0:
        return None, None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None, None
    streams = payload.get("streams") or []
    if not streams:
        return None, None
    st = streams[0]
    r_fps = _eval_fraction_fps(st.get("r_frame_rate")) if st.get("r_frame_rate") else None
    a_fps = _eval_fraction_fps(st.get("avg_frame_rate")) if st.get("avg_frame_rate") else None
    if r_fps is not None and r_fps <= 0:
        r_fps = None
    if a_fps is not None and a_fps <= 0:
        a_fps = None
    return r_fps, a_fps


def probe_video_wh_ffprobe(ffprobe_exe, video_path):
    """Returns (width, height) for first video stream, or (None, None)."""
    if not ffprobe_exe or not video_path or not os.path.isfile(video_path):
        return None, None
    try:
        kw = {}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        completed = subprocess.run(
            [
                ffprobe_exe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            **kw,
        )
    except (subprocess.SubprocessError, OSError):
        return None, None
    if completed.returncode != 0:
        return None, None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None, None
    streams = payload.get("streams") or []
    if not streams:
        return None, None
    st = streams[0]
    w, h = st.get("width"), st.get("height")
    if w is None or h is None:
        return None, None
    try:
        return int(w), int(h)
    except (TypeError, ValueError):
        return None, None


def probe_format_duration_seconds(ffprobe_exe, video_path):
    """Container duration in seconds from ffprobe (format), or None."""
    if not ffprobe_exe or not video_path or not os.path.isfile(video_path):
        return None
    try:
        kw = {}
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        completed = subprocess.run(
            [
                ffprobe_exe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            **kw,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return None
    fmt = payload.get("format") or {}
    d = fmt.get("duration")
    try:
        v = float(d)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return v


def print_stream_sync_warnings(lang, ffprobe_exe, source_video, deepfake_video, cap_src, cap_df):
    """Cheap sanity checks before index-locked frame comparison (no auto re-sync)."""
    try:
        fc_s = int(cap_src.get(cv2.CAP_PROP_FRAME_COUNT))
    except (TypeError, ValueError):
        fc_s = 0
    try:
        fc_d = int(cap_df.get(cv2.CAP_PROP_FRAME_COUNT))
    except (TypeError, ValueError):
        fc_d = 0
    if fc_s > 0 and fc_d > 0 and fc_s != fc_d:
        print(TEXTS[lang]["sync_warn_framecount"].format(src=fc_s, df=fc_d), flush=True)

    try:
        fps_s = float(cap_src.get(cv2.CAP_PROP_FPS))
    except (TypeError, ValueError):
        fps_s = 0.0
    try:
        fps_d = float(cap_df.get(cv2.CAP_PROP_FPS))
    except (TypeError, ValueError):
        fps_d = 0.0
    if fps_s > 0.01 and fps_d > 0.01 and abs(fps_s - fps_d) >= 0.2:
        print(TEXTS[lang]["sync_warn_fps"].format(src=fps_s, df=fps_d), flush=True)

    if ffprobe_exe:
        ds = probe_format_duration_seconds(ffprobe_exe, source_video)
        dd = probe_format_duration_seconds(ffprobe_exe, deepfake_video)
        if ds is not None and dd is not None:
            delta = abs(ds - dd)
            if delta >= 0.25:
                print(TEXTS[lang]["sync_warn_duration"].format(src=ds, df=dd, delta=delta), flush=True)
    else:
        print(TEXTS[lang]["sync_info_no_ffprobe_duration"], flush=True)


def pick_analysis_fps_from_probes(opencv_fps, r_fps, avg_fps, lang):
    """
    Prefer ffprobe r_frame_rate (nominal CFR). If only avg disagrees with OpenCV on a standard rate, trust OpenCV.
    """
    try:
        of = float(opencv_fps) if opencv_fps and float(opencv_fps) > 0 else None
    except (TypeError, ValueError):
        of = None
    rf = float(r_fps) if r_fps and float(r_fps) > 0 else None
    af = float(avg_fps) if avg_fps and float(avg_fps) > 0 else None

    if rf:
        if af and abs(rf - af) > 0.5:
            print(TEXTS[lang]["fps_r_vs_avg"].format(r=rf, avg=af), flush=True)
        return rf
    if af and of and abs(af - of) >= 0.5 and _near_standard_cfr(of):
        print(TEXTS[lang]["fps_prefer_opencv"].format(avg=af, ocv=of), flush=True)
        return of
    if af:
        return af
    if of:
        return of
    return None


def _davinci_set(project_or_timeline, key, val, where, lang):
    """Log if Resolve rejects a setting (returns False)."""
    try:
        ok = project_or_timeline.SetSetting(key, str(val))
    except Exception as e:
        print(f"[WARN] DaVinci SetSetting({key}) raised: {e}\n", flush=True)
        return False
    if ok is False:
        print(
            TEXTS[lang]["davinci_set_failed"].format(key=key, val=str(val), where=where),
            flush=True,
        )
    return ok is not False


def _timeline_fps_string_candidates(timeline_rate: str, fps_float: float):
    """Resolve is picky: Master dropdown vs timeline may accept '25' vs '25.0'. Try several."""
    try:
        f = float(fps_float)
    except (TypeError, ValueError):
        f = 0.0
    out = []
    seen = set()

    def add(s):
        if s and s not in seen:
            seen.add(s)
            out.append(str(s))

    add(timeline_rate)
    add(format_timeline_framerate_for_resolve(f))
    if f > 0:
        raw = f"{f:.6f}".rstrip("0").rstrip(".")
        add(raw)
        if abs(f - round(f)) < 0.06:
            ri = int(round(f))
            add(str(ri))
            add(f"{ri}.0")
    return out


def _davinci_set_project_master_before_import(project, timeline_rate, analysis_fps, width, height, lang):
    """
    Set Master timeline FPS + resolution on the Project before ImportMedia.
    Resolve often locks Master FPS to the first clip in the pool; doing this first avoids 23.976 lock on 25 fps exports.
    """
    candidates = _timeline_fps_string_candidates(timeline_rate, analysis_fps)
    chosen = None
    for cand in candidates:
        try:
            rp = project.SetSetting("timelineFrameRate", cand)
        except Exception:
            continue
        if rp is False:
            continue
        chosen = cand
        break
    if chosen is None:
        chosen = candidates[0]
        _davinci_set(project, "timelineFrameRate", chosen, "project", lang)
    _davinci_set(project, "timelineResolutionWidth", str(width), "project", lang)
    _davinci_set(project, "timelineResolutionHeight", str(height), "project", lang)
    try:
        gp = project.GetSetting("timelineFrameRate")
        print(
            TEXTS[lang]["davinci_master_preset"].format(fps=gp, w=width, h=height),
            flush=True,
        )
        try:
            gpf = float(str(gp).replace(",", "."))
            want = float(analysis_fps)
            if abs(gpf - want) > 0.5:
                print(
                    TEXTS[lang]["davinci_fps_locked_hint"].format(read=gp, target=timeline_rate),
                    flush=True,
                )
        except (TypeError, ValueError):
            pass
    except Exception:
        pass


def _davinci_sync_active_timeline_fps(project, timeline, timeline_rate, analysis_fps, lang, skip_if_close=False):
    """
    Match the active Timeline object's frame rate to analysis (Timeline:SetSetting).
    Timeline resolution is not set here — Master resolution on Project is enough for new timelines; some Resolve builds reject Timeline width/height via API.
    """
    if skip_if_close:
        try:
            gt = timeline.GetSetting("timelineFrameRate")
            g = float(str(gt).replace(",", "."))
            want = float(analysis_fps)
            if abs(g - want) < 0.06:
                gp = project.GetSetting("timelineFrameRate")
                print(TEXTS[lang]["davinci_fps_verify"].format(proj=gp, tl=gt), flush=True)
                return
        except Exception:
            pass
    candidates = _timeline_fps_string_candidates(timeline_rate, analysis_fps)
    chosen = None
    for cand in candidates:
        try:
            rt = timeline.SetSetting("timelineFrameRate", cand)
        except Exception:
            continue
        if rt is False:
            continue
        chosen = cand
        break
    if chosen is None:
        chosen = candidates[0]
        _davinci_set(timeline, "timelineFrameRate", chosen, "timeline", lang)
    try:
        gp = project.GetSetting("timelineFrameRate")
        gt = timeline.GetSetting("timelineFrameRate")
        print(TEXTS[lang]["davinci_fps_verify"].format(proj=gp, tl=gt), flush=True)
    except Exception:
        pass


def _davinci_delete_all_timelines(project, mediaPool):
    """Resolve makes Project timelineFrameRate read-only while timelines exist; strip defaults on a fresh project."""
    try:
        n = int(project.GetTimelineCount())
    except (TypeError, ValueError, AttributeError, Exception):
        return
    if n <= 0:
        return
    timelines = []
    for idx in range(1, n + 1):
        try:
            tl = project.GetTimelineByIndex(idx)
            if tl:
                timelines.append(tl)
        except Exception:
            continue
    if not timelines:
        return
    try:
        mediaPool.DeleteTimelines(timelines)
    except Exception:
        pass


def _davinci_try_create_export_project(project_manager, lang):
    """Returns (project, name) or (None, None)."""
    for _ in range(12):
        name = (
            f"AutoCut_Export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_"
            f"{random.randint(100000, 999999)}"
        )
        try:
            p = project_manager.CreateProject(name)
        except Exception:
            p = None
        if p:
            return p, name
    print(TEXTS[lang]["davinci_temp_project_failed"], flush=True)
    return None, None


def _davinci_restore_user_project(project_manager, orig_name, did_switch, lang):
    if not did_switch or not orig_name:
        return
    try:
        project_manager.LoadProject(orig_name)
        print(TEXTS[lang]["davinci_restored_project"].format(name=orig_name), flush=True)
    except Exception as e:
        print(
            TEXTS[lang]["davinci_restore_failed"].format(name=orig_name, error=e),
            flush=True,
        )


def _davinci_wait_for_render_idle(project, lang, davinci_render_timeout_seconds, start_time):
    """
    IsRenderingInProgress() is often False for a short time right after StartRendering().
    If we treat that as 'done', the script returns while encoding is still running — output files are truncated.
    Wait until we have either seen active rendering and then idle, or job status is already Complete, or timeout.
    """
    rendering_seen = False
    no_start_deadline = start_time + 120.0
    while True:
        try:
            busy = project.IsRenderingInProgress()
        except Exception as poll_err:
            print(TEXTS[lang]['davinci_export_interrupted'].format(error=poll_err), flush=True)
            return False
        now = time.time()
        if busy:
            rendering_seen = True
        if not busy and rendering_seen:
            time.sleep(2.0)
            try:
                if project.IsRenderingInProgress():
                    continue
            except Exception:
                pass
            return True
        if not busy and not rendering_seen:
            try:
                render_jobs = project.GetRenderJobList()
                if render_jobs:
                    job_id = render_jobs[-1].get("JobId")
                    if job_id:
                        st = project.GetRenderJobStatus(job_id)
                        status = (st or {}).get("JobStatus", "Unknown")
                        if status in ("Complete", "Abgeschlossen"):
                            time.sleep(2.0)
                            return True
                        s = str(status).lower()
                        if "fail" in s or "cancel" in s or "abort" in s:
                            print(
                                TEXTS[lang]['davinci_render_status_failed'].format(
                                    status=status
                                ),
                                flush=True,
                            )
                            return False
            except Exception:
                pass
            if now > no_start_deadline:
                print(
                    TEXTS[lang]['davinci_render_never_started'].format(sec=120),
                    flush=True,
                )
                return False
        if (
            davinci_render_timeout_seconds > 0
            and (now - start_time) > davinci_render_timeout_seconds
        ):
            try:
                project.StopRendering()
            except Exception:
                pass
            time.sleep(2)
            print(
                "\n[INFO] "
                + TEXTS[lang]['davinci_render_timeout_exceeded'].format(
                    sec=davinci_render_timeout_seconds
                )
                + "\n",
                flush=True,
            )
            return False
        time.sleep(0.4 if not rendering_seen else 5.0)


def _davinci_run_export_pipeline(
    project,
    mediaPool,
    deepfake_video,
    all_seqs,
    lang,
    target_dir,
    davinci_render_timeout_seconds,
    analysis_fps,
    timeline_rate,
    width,
    height,
    abs_video_path,
    settings,
):
    """Import, build timeline, render — assumes project/mediaPool are the export target."""
    # Before ImportMedia: avoid Resolve locking Master FPS to the clip's tagged rate (e.g. 23.976 on a 25 fps cut list).
    _davinci_set_project_master_before_import(
        project, timeline_rate, analysis_fps, width, height, lang
    )

    imported_items = mediaPool.ImportMedia([abs_video_path])

    if not imported_items:
        print(TEXTS[lang]['davinci_import_error'].format(path=abs_video_path))
        return False

    df_item = imported_items[0]

    clip_props = df_item.GetClipProperty() or {}
    clip_fps_meta = clip_props.get("FPS")

    # Deepfake export files are often tagged 23.976 while source is 29.97 — override clip interpretation.
    try:
        clip_pv = format_clip_fps_property_for_resolve(analysis_fps)
        for val in (timeline_rate, clip_pv):
            try:
                if df_item.SetClipProperty("FPS", val) is not False:
                    break
            except Exception:
                continue
    except Exception:
        pass

    base_name = os.path.splitext(os.path.basename(deepfake_video))[0]
    custom_render_name = pick_unique_davinci_custom_name(base_name, target_dir, settings)
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    timeline_name = f"AutoCut_{base_name}_{timestamp}"
    timeline = mediaPool.CreateEmptyTimeline(timeline_name)

    if not timeline:
        print(TEXTS[lang]['davinci_timeline_error'])
        return False

    # AppendToTimeline() attaches to the *current* timeline — switch before append.
    project.SetCurrentTimeline(timeline)
    _davinci_sync_active_timeline_fps(project, timeline, timeline_rate, analysis_fps, lang)
    print(
        TEXTS[lang]['davinci_timeline_fps'].format(
            rate=timeline_rate,
            clip=clip_fps_meta if clip_fps_meta is not None else "(none)",
        ),
        flush=True,
    )

    # all_seqs is half-open [start, end) like FFmpeg trim. DaVinci AppendToTimeline uses the same convention:
    # duration = endFrame - startFrame (exclusive end), per Resolve scripting docs / behaviour — do NOT use end-1 here.
    clips_to_append = []
    for start_frame, end_frame, is_good in all_seqs:
        if is_good:
            duration = end_frame - start_frame
            if duration > 0:
                clips_to_append.append({
                    "mediaPoolItem": df_item,
                    "startFrame": int(start_frame),
                    "endFrame": int(end_frame),
                })

    if clips_to_append:
        mediaPool.AppendToTimeline(clips_to_append)
    else:
        print(TEXTS[lang]['davinci_no_valid_scenes'])
        return False

    # Resolve may snap timeline FPS after append — re-sync only if needed (avoids duplicate API warnings).
    project.SetCurrentTimeline(timeline)
    _davinci_sync_active_timeline_fps(
        project, timeline, timeline_rate, analysis_fps, lang, skip_if_close=True
    )

    project.DeleteAllRenderJobs()

    preset_name = str(settings.get("davinci_render_preset", "AutoCutPreset") or "AutoCutPreset").strip()
    if not preset_name:
        preset_name = "AutoCutPreset"
    if not project.LoadRenderPreset(preset_name):
        print(TEXTS[lang]['davinci_preset_warning'].format(preset=preset_name))
        print(TEXTS[lang]['davinci_preset_fallback'])

    try:
        render_fps = float(analysis_fps)
    except (TypeError, ValueError):
        render_fps = 30.0
    project.SetRenderSettings({
        "SelectAllFrames": True,
        "TargetDir": target_dir,
        "CustomName": custom_render_name,
        "ResolutionWidth": width,
        "ResolutionHeight": height,
        "FrameRate": render_fps,
    })

    project.AddRenderJob()
    print(TEXTS[lang]['davinci_job_created'].format(name=custom_render_name))
    print(TEXTS[lang]['davinci_start_render'])
    project.StartRendering()
    print(TEXTS[lang]['davinci_render_running'])

    # Wait until DaVinci finishes; optional time limit (settings.ini davinci_render_timeout_seconds, 0 = no limit).
    # If Resolve is closed mid-render, the API may raise or return empty jobs — treat as soft failure (no process crash).
    start_time = time.time()
    try:
        if not _davinci_wait_for_render_idle(
            project, lang, davinci_render_timeout_seconds, start_time
        ):
            return False

        try:
            render_jobs = project.GetRenderJobList()
        except Exception as e:
            print(TEXTS[lang]['davinci_export_interrupted'].format(error=e))
            return False
        if not render_jobs:
            print(TEXTS[lang]['davinci_render_no_jobs'])
            return False

        job_id = render_jobs[-1].get("JobId")
        if not job_id:
            print(TEXTS[lang]['davinci_render_no_jobs'])
            return False

        try:
            status_dict = project.GetRenderJobStatus(job_id)
        except Exception as e:
            print(TEXTS[lang]['davinci_export_interrupted'].format(error=e))
            return False
        status = status_dict.get("JobStatus", "Unknown") if status_dict else "Unknown"

        if status not in ["Complete", "Abgeschlossen"]:
            print(TEXTS[lang]['davinci_render_status_failed'].format(status=status))
            return False

        return True
    except Exception as e:
        print(TEXTS[lang]['davinci_export_interrupted'].format(error=e))
        return False


def format_clip_fps_property_for_resolve(fps_float):
    """Clip Attributes > Video FPS — scripting examples often use '25.0' style for whole rates."""
    try:
        f = float(fps_float)
    except (TypeError, ValueError):
        return "30.0"
    if f <= 0:
        return "30.0"
    if abs(f - round(f)) < 0.02:
        return f"{float(int(round(f))):.1f}"
    return format_timeline_framerate_for_resolve(f)


def format_timeline_framerate_for_resolve(fps):
    """
    Strings for project.SetSetting('timelineFrameRate', ...).
    Match common Resolve rates so cuts align with AppendToTimeline frame numbers.
    """
    try:
        fps = float(fps)
    except (TypeError, ValueError):
        return "30"
    if fps <= 0:
        return "30"
    common = [
        (23.976023976023978, "23.976"),
        (24.0, "24"),
        (25.0, "25"),
        (29.97002997002997, "29.97"),
        (30.0, "30"),
        (48.0, "48"),
        (50.0, "50"),
        (59.94005994005994, "59.94"),
        (60.0, "60"),
    ]
    for val, label in common:
        if abs(fps - val) < 0.04:
            return label
    if abs(fps - round(fps)) < 0.001:
        return str(int(round(fps)))
    out = f"{fps:.6f}".rstrip("0").rstrip(".")
    return out if out else "30"


def parse_ffmpeg_export_target(raw):
    v = (raw or "both").strip().lower()
    if v in ("both", "source", "deepfake"):
        return v
    return "both"


def load_config():
    base_dir = get_base_dir()
    config_path = os.path.join(base_dir, 'settings.ini')
    config = configparser.ConfigParser()
    
    if not os.path.exists(config_path):
        config['SETTINGS'] = {
            'language': 'en',
            'buffer_seconds': '2.0',
            'pixel_noise_threshold': '15',
            'changed_pixels_threshold': '200',
            'changed_pixels_max_threshold': '0',
            'enable_ffmpeg_export': '0',
            'ffmpeg_export_target': 'both',
            'ffmpeg_encoder': 'nvidia_h264',
            'enable_fullcheck_edl': '0',
            'enable_autodelete_edl': '1',
            'enable_davinci_export': '0',
            'davinci_render_timeout_seconds': '1800',
            'davinci_render_preset': 'AutoCutPreset',
            'davinci_scriptapp_retry_attempts': '60',
            'davinci_scriptapp_retry_delay_seconds': '3',
            'export_avoid_overwrite': '0',
            'davinci_startup_wait_seconds': '20',
        }
        config['PATHS'] = {
            'davinci_api_path': r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules',
            'davinci_exe_path': r'C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe',
            'final_export_dir': ''
        }
        with open(config_path, "w", encoding="utf-8", newline="\n") as configfile:
            config.write(configfile)
            
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo("First Run / Erster Start", TEXTS['en']['first_run_msg'])
        root.destroy()
        sys.exit(0)
            
    _read_ini_file(config, config_path)

    if not config.has_section('SETTINGS'):
        config.add_section('SETTINGS')
    
    if not config.has_section('PATHS'):
        config.add_section('PATHS')

    return {
        'language': config.get('SETTINGS', 'language', fallback='en').lower(),
        'buffer_seconds': config.getfloat('SETTINGS', 'buffer_seconds', fallback=2.0),
        'pixel_noise_threshold': config.getint('SETTINGS', 'pixel_noise_threshold', fallback=15),
        'changed_pixels_threshold': config.getint('SETTINGS', 'changed_pixels_threshold', fallback=200),
        'changed_pixels_max_threshold': max(
            0, config.getint('SETTINGS', 'changed_pixels_max_threshold', fallback=0)
        ),
        'enable_ffmpeg_export': config.getboolean('SETTINGS', 'enable_ffmpeg_export', fallback=False),
        'ffmpeg_export_target': parse_ffmpeg_export_target(
            config.get('SETTINGS', 'ffmpeg_export_target', fallback='both')
        ),
        'ffmpeg_encoder': config.get('SETTINGS', 'ffmpeg_encoder', fallback='nvidia_h264').lower(),
        'enable_fullcheck_edl': _ini_bool(config, 'SETTINGS', 'enable_fullcheck_edl', False),
        'enable_autodelete_edl': _ini_bool(config, 'SETTINGS', 'enable_autodelete_edl', True),
        'enable_davinci_export': _ini_bool(config, 'SETTINGS', 'enable_davinci_export', False),
        'davinci_render_timeout_seconds': max(
            0,
            config.getint('SETTINGS', 'davinci_render_timeout_seconds', fallback=1800)
        ),
        'davinci_render_preset': config.get('SETTINGS', 'davinci_render_preset', fallback='AutoCutPreset').strip() or 'AutoCutPreset',
        'davinci_api_path': config.get('PATHS', 'davinci_api_path', fallback=r'C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules'),
        'final_export_dir': config.get('PATHS', 'final_export_dir', fallback=''),
        'davinci_scriptapp_retry_attempts': _ini_int_clamped(
            config, 'SETTINGS', 'davinci_scriptapp_retry_attempts', 1, 120, 60
        ),
        'davinci_scriptapp_retry_delay_seconds': _ini_float_clamped(
            config, 'SETTINGS', 'davinci_scriptapp_retry_delay_seconds', 1.0, 30.0, 3.0
        ),
        'export_avoid_overwrite': _ini_bool(config, 'SETTINGS', 'export_avoid_overwrite', False),
        'davinci_exe_path': config.get('PATHS', 'davinci_exe_path', fallback='').strip(),
        'davinci_startup_wait_seconds': _ini_int_clamped(
            config, 'SETTINGS', 'davinci_startup_wait_seconds', 0, 600, 20
        ),
    }


def write_settings_pixel_thresholds(base_dir, pixel_noise_threshold=None, changed_pixels_threshold=None):
    """Update only pixel thresholds in settings.ini; other keys unchanged."""
    config_path = os.path.join(base_dir, 'settings.ini')
    if not os.path.exists(config_path):
        return False
    config = configparser.ConfigParser()
    _read_ini_file(config, config_path)
    if not config.has_section('SETTINGS'):
        return False
    if pixel_noise_threshold is not None:
        config.set('SETTINGS', 'pixel_noise_threshold', str(int(pixel_noise_threshold)))
    if changed_pixels_threshold is not None:
        config.set('SETTINGS', 'changed_pixels_threshold', str(int(changed_pixels_threshold)))
    with open(config_path, "w", encoding="utf-8", newline="\n") as f:
        config.write(f)
    return True


def frame_to_tc(frame, fps_int):
    h = int(frame / (fps_int * 3600))
    m = int((frame / (fps_int * 60)) % 60)
    s = int((frame / fps_int) % 60)
    f = int(frame % fps_int)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def compare_export_filename_tag(
    buffer_seconds,
    noise_thresh,
    pixel_thresh,
    changed_pixels_max: int = 0,
):
    """Suffix from Compare filter (buffer / noise / pixel / optional max cap), filename-safe."""
    b = f"{float(buffer_seconds):g}".replace(".", "-")
    s = f"_b{b}_n{int(noise_thresh)}_p{int(pixel_thresh)}"
    mx = int(changed_pixels_max) if changed_pixels_max else 0
    if mx > 0:
        s += f"_m{mx}"
    return s


def allocate_unique_media_output_path(base_without_ext, ext, settings):
    """
    base_without_ext: full path without extension, e.g. C:/work/clip_AutoCut
    ext: includes dot, e.g. .mp4
    If export_avoid_overwrite is false, returns base_without_ext + ext (FFmpeg -y may overwrite).
    """
    if not settings.get("export_avoid_overwrite"):
        return base_without_ext + ext
    tag = compare_export_filename_tag(
        settings["buffer_seconds"],
        settings["pixel_noise_threshold"],
        settings["changed_pixels_threshold"],
        settings.get("changed_pixels_max_threshold", 0) or 0,
    )
    candidates = [f"{base_without_ext}{tag}{ext}"] + [
        f"{base_without_ext}{tag}_{i}{ext}" for i in range(2, 21)
    ]
    for path in candidates:
        if not os.path.exists(path):
            return path
    return f"{base_without_ext}{tag}_{datetime.datetime.now().strftime('%H%M%S')}{ext}"


def pick_unique_davinci_custom_name(base_name, target_dir, settings):
    """Resolve CustomName (no extension). When avoid-overwrite, append filter tag then _2.._20 if needed."""
    stem = f"{base_name}_DaVinci_Export"
    if not settings.get("export_avoid_overwrite"):
        return stem
    tag = compare_export_filename_tag(
        settings["buffer_seconds"],
        settings["pixel_noise_threshold"],
        settings["changed_pixels_threshold"],
        settings.get("changed_pixels_max_threshold", 0) or 0,
    )
    exts = (".mp4", ".mov", ".mxf", ".mkv")

    def stem_taken(cand_stem):
        if not os.path.isdir(target_dir):
            return False
        for e in exts:
            if os.path.isfile(os.path.join(target_dir, cand_stem + e)):
                return True
        return False

    for extra in [""] + [f"_{i}" for i in range(2, 21)]:
        cand = f"{stem}{tag}{extra}"
        if not stem_taken(cand):
            return cand
    return f"{stem}{tag}_{datetime.datetime.now().strftime('%H%M%S')}"


def get_segment_style(is_good):
    if is_good:
        return {
            "clip_name": "SWAP_OK",
            "clip_color": "Green",
            "resolve_color": "ResolveColorGreen",
            "marker_text": "SWAP_OK"
        }
    else:
        return {
            "clip_name": "FLICK_ERROR",
            "clip_color": "Red",
            "resolve_color": "ResolveColorRed",
            "marker_text": "FLICK_ERROR"
        }

def write_edl(output_path, all_seqs, fps_int, video_path, auto_remove):
    clip_name = os.path.basename(video_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("TITLE: GPU Check EDL\n")
        f.write("FCM: NON-DROP FRAME\n\n")

        event_num = 1
        record_time_frames = 0

        for start_frame, end_frame, is_good in all_seqs:
            if auto_remove and not is_good:
                continue

            duration = end_frame - start_frame
            if duration <= 0:
                continue

            src_tc_in = frame_to_tc(start_frame, fps_int)
            src_tc_out = frame_to_tc(end_frame, fps_int)

            if auto_remove:
                rec_tc_in = frame_to_tc(record_time_frames, fps_int)
                record_time_frames += duration
                rec_tc_out = frame_to_tc(record_time_frames, fps_int)
            else:
                rec_tc_in = src_tc_in
                rec_tc_out = src_tc_out

            style = get_segment_style(is_good)

            f.write(f"{event_num:03d} AX AA/V C        {src_tc_in} {src_tc_out} {rec_tc_in} {rec_tc_out}\n")
            f.write(f"* FROM CLIP NAME: {clip_name}\n")
            f.write(f"* CLIP NAME: {style['clip_name']}\n")
            f.write(f"* CLIP COLOR: {style['clip_color']}\n")
            f.write(f"* {style['marker_text']}\n")
            f.write(f" |C:{style['resolve_color']} |M:{style['marker_text']} |D:1\n\n")

            event_num += 1

def export_video_ffmpeg(video_path, output_path, all_seqs, fps_float, total_frames, ffmpeg_exe, lang, encoder_setting):
    """True bei Erfolg oder nichts zu tun; False bei FFmpeg-Fehler."""
    good_seqs = [seq for seq in all_seqs if seq[2]]
    if not good_seqs:
        return True

    filter_path = output_path + "_filter.txt"
    with open(filter_path, 'w', encoding='utf-8') as f:
        concat_inputs = []
        for i, (start, end, _) in enumerate(good_seqs):
            start_sec = start / fps_float
            end_sec = end / fps_float
            
            f.write(f"[0:v]trim=start={start_sec:.5f}:end={end_sec:.5f},setpts=PTS-STARTPTS[v{i}];\n")
            f.write(f"[0:a]atrim=start={start_sec:.5f}:end={end_sec:.5f},asetpts=PTS-STARTPTS[a{i}];\n")
            
            concat_inputs.append(f"[v{i}][a{i}]")

        f.write(f"{''.join(concat_inputs)}concat=n={len(good_seqs)}:v=1:a=1[outv][outa]\n")

    print(TEXTS[lang]['ffmpeg_render'].format(name=os.path.basename(output_path), codec=encoder_setting))
    encoder_params = {
        'cpu': ["-c:v", "libx264", "-preset", "fast", "-crf", "18"],
        'cpu_hevc': ["-c:v", "libx265", "-preset", "fast", "-crf", "22"],
        'nvidia_h264': ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "18"],
        'nvidia_hevc': ["-c:v", "hevc_nvenc", "-preset", "p6", "-cq", "18"],
        'nvidia_av1': ["-c:v", "av1_nvenc", "-preset", "p6", "-cq", "18"],
        'amd_h264': ["-c:v", "h264_amf", "-rc", "cqp", "-qp_p", "18", "-qp_i", "18"],
        'amd_hevc': ["-c:v", "hevc_amf", "-rc", "cqp", "-qp_p", "18", "-qp_i", "18"]
    }
    
    # Fallback auf nvidia_h264, falls eine ungueltige Eingabe gemacht wird
    selected_params = encoder_params.get(encoder_setting, encoder_params['nvidia_h264'])

    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-filter_complex_script", filter_path,
        "-map", "[outv]",
        "-map", "[outa]"
    ] + selected_params + [
        "-c:a", "aac", "-b:a", "256k",
        output_path
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )

        frame_pattern = re.compile(r"frame=\s*(\d+)")
        last_lines = []

        for line in process.stderr:
            last_lines.append(line.strip())
            if len(last_lines) > 15:
                last_lines.pop(0)

            match = frame_pattern.search(line)
            if match and total_frames > 0:
                frame = int(match.group(1))
                percent = (frame / total_frames) * 100
                sys.stdout.write(
                    TEXTS[lang]["ffmpeg_progress"].format(percent=percent, frame=frame, total=total_frames)
                )
                sys.stdout.flush()

        process.wait()

        if process.returncode != 0:
            print(TEXTS[lang]["ffmpeg_error"].format(name=os.path.basename(video_path)))
            for line in last_lines:
                print(line)
            print("---------------------------------\n")
            return False
        print(TEXTS[lang]["ffmpeg_success"])
        return True
    except Exception as ex:
        print(TEXTS[lang]["ffmpeg_error"].format(name=os.path.basename(video_path)))
        print(str(ex))
        print("---------------------------------\n")
        return False
    finally:
        if os.path.exists(filter_path):
            try:
                os.remove(filter_path)
            except Exception:
                pass

def export_via_davinci(
    deepfake_video,
    source_video,
    all_seqs,
    davinci_api_path,
    lang,
    final_export_dir,
    davinci_render_timeout_seconds,
    *,
    analysis_fps,
    scriptapp_retry_attempts=60,
    scriptapp_retry_delay_sec=3.0,
    settings=None,
):
    """Returns True if render completed successfully, False otherwise."""

    if davinci_api_path not in sys.path:
        sys.path.append(davinci_api_path)

    try:
        import DaVinciResolveScript as dvr_script
    except ImportError:
        print(TEXTS[lang]['davinci_api_missing'])
        print(TEXTS[lang]['davinci_api_path_searched'].format(path=davinci_api_path))
        print(TEXTS[lang]['davinci_api_check_explorer'])
        return False

    # scriptapp("Resolve") is often still None until Resolve Studio finishes init (or if not Studio / wrong user).
    max_resolve_wait_attempts = max(1, int(scriptapp_retry_attempts))
    resolve_wait_delay_sec = float(scriptapp_retry_delay_sec)
    resolve = None
    for attempt in range(1, max_resolve_wait_attempts + 1):
        resolve = dvr_script.scriptapp("Resolve")
        if resolve:
            break
        if attempt == 1:
            print(TEXTS[lang]['davinci_scriptapp_hint'], flush=True)
        if attempt < max_resolve_wait_attempts:
            if attempt == 1 or attempt % 10 == 0:
                print(
                    TEXTS[lang]['davinci_api_retry'].format(
                        n=attempt,
                        max=max_resolve_wait_attempts,
                        delay=resolve_wait_delay_sec,
                    ),
                    flush=True,
                )
            time.sleep(resolve_wait_delay_sec)
    if not resolve:
        print(TEXTS[lang]['davinci_not_open'], flush=True)
        return False

    projectManager = resolve.GetProjectManager()
    max_project_wait = 40
    project_wait_delay = 3.0
    project = None
    for attempt in range(1, max_project_wait + 1):
        project = projectManager.GetCurrentProject()
        if project:
            break
        if attempt < max_project_wait:
            if attempt == 1 or attempt % 10 == 0:
                print(
                    TEXTS[lang]['davinci_no_project_wait'].format(
                        n=attempt, max=max_project_wait
                    ),
                    flush=True,
                )
            time.sleep(project_wait_delay)
    if not project:
        print(TEXTS[lang]['davinci_no_project'])
        print(TEXTS[lang]['davinci_no_project_hint'])
        return False

    print(TEXTS[lang]['davinci_sending_data'])

    # Pause so Windows can release file locks from OpenCV before Resolve imports the clip
    time.sleep(2)

    # 2. Pfad für die DaVinci-API erzwingen (Forward-Slashes verhindern Lesefehler)
    abs_video_fs = os.path.abspath(deepfake_video)
    abs_video_path = abs_video_fs.replace("\\", "/")
    if final_export_dir and os.path.exists(final_export_dir):
        target_dir = final_export_dir
    else:
        target_dir = os.path.dirname(abs_video_fs)
    if settings is None:
        settings = {"export_avoid_overwrite": False}

    try:
        analysis_fps = float(analysis_fps)
    except (TypeError, ValueError):
        analysis_fps = 30.0
    if analysis_fps <= 0:
        analysis_fps = 30.0

    # Timeline FPS must match compare.py frame indices (OpenCV + ffprobe), not only Resolve metadata.
    timeline_rate = format_timeline_framerate_for_resolve(analysis_fps)

    base_dir = get_base_dir()
    ffprobe_local = os.path.join(base_dir, "ffprobe.exe")
    ffprobe_exe = ffprobe_local if os.path.isfile(ffprobe_local) else shutil.which("ffprobe")

    width = height = None
    if ffprobe_exe:
        width, height = probe_video_wh_ffprobe(ffprobe_exe, abs_video_fs)

    if not width or not height:
        print(TEXTS[lang]["davinci_ffprobe_wh_warn"], flush=True)
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            user_res = simpledialog.askstring(
                TEXTS[lang]["manual_res_title"],
                TEXTS[lang]["manual_res_prompt"],
                initialvalue="1920x1080",
            )
        finally:
            root.destroy()

        if user_res:
            try:
                width, height = [int(x) for x in user_res.lower().replace(" ", "").split("x", 1)]
            except Exception:
                print(TEXTS[lang]["manual_res_invalid"])
                width, height = 1920, 1080
        else:
            print(TEXTS[lang]["manual_res_invalid"])
            width, height = 1920, 1080

    try:
        orig_resolve_project_name = project.GetName()
    except Exception:
        orig_resolve_project_name = None

    export_proj, export_proj_name = _davinci_try_create_export_project(projectManager, lang)
    switched_to_temp_export_project = False
    if export_proj is not None:
        project = export_proj
        switched_to_temp_export_project = True
        mediaPool = project.GetMediaPool()
        _davinci_delete_all_timelines(project, mediaPool)
        if orig_resolve_project_name:
            print(
                TEXTS[lang]["davinci_temp_project"].format(
                    temp=export_proj_name,
                    orig=orig_resolve_project_name,
                ),
                flush=True,
            )
    else:
        mediaPool = project.GetMediaPool()

    try:
        return _davinci_run_export_pipeline(
            project,
            mediaPool,
            deepfake_video,
            all_seqs,
            lang,
            target_dir,
            davinci_render_timeout_seconds,
            analysis_fps,
            timeline_rate,
            width,
            height,
            abs_video_path,
            settings,
        )
    finally:
        _davinci_restore_user_project(
            projectManager,
            orig_resolve_project_name,
            switched_to_temp_export_project,
            lang,
        )


def _ensure_stdio_utf8() -> None:
    """Windows-Konsole nutzt oft cp1252; unsere Meldungen enthalten z. B. „→“ (U+2192)."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


EXPORT_CHECKPOINT_FILENAME = "oxco_compare_export_checkpoint.json"


def export_checkpoint_path() -> str:
    return os.path.join(get_base_dir(), EXPORT_CHECKPOINT_FILENAME)


def _remove_export_checkpoint_silent() -> None:
    try:
        p = export_checkpoint_path()
        if os.path.isfile(p):
            os.remove(p)
    except OSError:
        pass


def _write_export_checkpoint(
    source_video: str,
    deepfake_video: str,
    lang: str,
    all_seqs: list,
    fps_float: float,
    fps_int: int,
    total_frames: int,
) -> None:
    data = {
        "version": 1,
        "source_video": os.path.normcase(os.path.abspath(source_video)),
        "deepfake_video": os.path.normcase(os.path.abspath(deepfake_video)),
        "lang": lang,
        "all_seqs": [[int(a), int(b), bool(c)] for (a, b, c) in all_seqs],
        "fps_float": float(fps_float),
        "fps_int": int(fps_int),
        "total_frames": int(total_frames),
    }
    try:
        with open(export_checkpoint_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(TEXTS[lang]["checkpoint_written"], flush=True)
    except OSError as e:
        print(TEXTS[lang]["checkpoint_write_failed"].format(error=e), flush=True)


def run_compare_export_pipeline(
    source_video: str,
    deepfake_video: str,
    settings: dict,
    lang: str,
    all_seqs: list,
    fps_float: float,
    fps_int: int,
    total_frames: int,
) -> int:
    """EDL + FFmpeg + DaVinci gemäß settings; Rückgabe 0 oder 3."""
    base_dir = get_base_dir()
    local_ffmpeg = os.path.join(base_dir, "ffmpeg.exe")
    ffmpeg_exe = local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg"

    enable_ffmpeg = settings["enable_ffmpeg_export"]
    ffmpeg_export_target = settings["ffmpeg_export_target"]
    ffmpeg_encoder = settings["ffmpeg_encoder"]
    enable_fullcheck = settings["enable_fullcheck_edl"]
    enable_autodelete_edl = settings["enable_autodelete_edl"]
    enable_davinci = settings["enable_davinci_export"]
    davinci_api_path = settings["davinci_api_path"]
    final_export_dir = settings.get("final_export_dir", "") or ""
    davinci_render_timeout_seconds = settings.get("davinci_render_timeout_seconds", 1800)
    scriptapp_retries = settings.get("davinci_scriptapp_retry_attempts", 60)
    scriptapp_delay = settings.get("davinci_scriptapp_retry_delay_seconds", 3.0)
    davinci_exe_path = settings.get("davinci_exe_path", "") or ""
    try:
        _dsw = settings.get("davinci_startup_wait_seconds", 20)
        davinci_startup_wait_seconds = max(0, min(600, int(_dsw)))
    except (TypeError, ValueError):
        davinci_startup_wait_seconds = 20

    if enable_davinci:
        ensure_resolve_running_for_compare(davinci_exe_path, davinci_startup_wait_seconds, lang)

    base_src_full = os.path.splitext(source_video)[0]
    base_df_full = os.path.splitext(deepfake_video)[0]

    if final_export_dir and os.path.exists(final_export_dir):
        path_src_base = os.path.join(final_export_dir, os.path.basename(base_src_full))
        path_df_base = os.path.join(final_export_dir, os.path.basename(base_df_full))
    else:
        path_src_base = base_src_full
        path_df_base = base_df_full

    if enable_autodelete_edl:
        edl_src_auto = f"{path_src_base}_SOURCE_AutoDelete.edl"
        edl_df_auto = f"{path_df_base}_DEEPFAKE_AutoDelete.edl"
        write_edl(edl_src_auto, all_seqs, fps_int, source_video, auto_remove=True)
        write_edl(edl_df_auto, all_seqs, fps_int, deepfake_video, auto_remove=True)
        print(TEXTS[lang]["edl_auto_created"])
        print(f"- {os.path.basename(edl_src_auto)}")
        print(f"- {os.path.basename(edl_df_auto)}")

    if enable_fullcheck:
        edl_src_full = f"{path_src_base}_SOURCE_FullCheck.edl"
        edl_df_full = f"{path_df_base}_DEEPFAKE_FullCheck.edl"
        write_edl(edl_src_full, all_seqs, fps_int, source_video, auto_remove=False)
        write_edl(edl_df_full, all_seqs, fps_int, deepfake_video, auto_remove=False)
        print(TEXTS[lang]["edl_full_created"])

    if enable_ffmpeg:
        vid_src_auto = allocate_unique_media_output_path(f"{path_src_base}_AutoCut", ".mp4", settings)
        vid_df_auto = allocate_unique_media_output_path(f"{path_df_base}_AutoCut", ".mp4", settings)
        ffmpeg_ok_all = True
        if ffmpeg_export_target in ("both", "source"):
            if not export_video_ffmpeg(
                source_video, vid_src_auto, all_seqs, fps_float, total_frames, ffmpeg_exe, lang, ffmpeg_encoder
            ):
                ffmpeg_ok_all = False
        if ffmpeg_export_target in ("both", "deepfake"):
            if not export_video_ffmpeg(
                deepfake_video, vid_df_auto, all_seqs, fps_float, total_frames, ffmpeg_exe, lang, ffmpeg_encoder
            ):
                ffmpeg_ok_all = False
    else:
        ffmpeg_ok_all = True

    davinci_ok = True
    if enable_davinci:
        api_abs = os.path.abspath(davinci_api_path)
        dvm = os.path.join(api_abs, "DaVinciResolveScript.py")
        print(TEXTS[lang]["davinci_export_start_info"].format(path=api_abs), flush=True)
        if not os.path.isfile(dvm):
            print(TEXTS[lang]["davinci_script_missing"].format(path=dvm), flush=True)
            davinci_ok = False
        else:
            print(
                f"[INFO] DaVinci scriptapp connect: up to {int(scriptapp_retries)} tries, "
                f"{float(scriptapp_delay)}s apart (settings.ini: davinci_scriptapp_retry_*).\n",
                flush=True,
            )
            try:
                davinci_ok = export_via_davinci(
                    deepfake_video,
                    source_video,
                    all_seqs,
                    davinci_api_path,
                    lang,
                    final_export_dir,
                    davinci_render_timeout_seconds,
                    analysis_fps=fps_float,
                    scriptapp_retry_attempts=scriptapp_retries,
                    scriptapp_retry_delay_sec=scriptapp_delay,
                    settings=settings,
                )
            except Exception as ex:
                print(TEXTS[lang]["davinci_export_exception"].format(error=ex))
                davinci_ok = False
        if davinci_ok:
            print(TEXTS[lang]["compare_summary_davinci_ok"])
        else:
            print(TEXTS[lang]["compare_summary_davinci_fail"])

    export_failed = False
    if enable_ffmpeg and not ffmpeg_ok_all:
        export_failed = True
    if enable_davinci and not davinci_ok:
        export_failed = True

    print(TEXTS[lang]["all_done"])
    if export_failed:
        print(TEXTS[lang]["compare_exit_partial"], flush=True)
        return 3
    _remove_export_checkpoint_silent()
    return 0


def run_retry_export_from_checkpoint(source_video: str, deepfake_video: str, settings: dict) -> int:
    """Nur Export erneut (keine Pixelanalyse). Rückgabe 0/3/1."""
    lang = settings.get("language", "en") or "en"
    if isinstance(lang, str):
        lang = lang.lower()
    if lang not in TEXTS:
        lang = "en"

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

    ck_path = export_checkpoint_path()
    if not os.path.isfile(ck_path):
        print(TEXTS[lang]["retry_export_no_checkpoint"], flush=True)
        return 1
    try:
        with open(ck_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(TEXTS[lang]["retry_export_ck_read_err"].format(error=e), flush=True)
        return 1

    if data.get("version") != 1:
        print(TEXTS[lang]["retry_export_no_checkpoint"], flush=True)
        return 1

    sa = os.path.normcase(os.path.abspath(source_video))
    sb = os.path.normcase(os.path.abspath(deepfake_video))
    if data.get("source_video") != sa or data.get("deepfake_video") != sb:
        print(TEXTS[lang]["retry_export_path_mismatch"], flush=True)
        return 1
    if not os.path.isfile(source_video) or not os.path.isfile(deepfake_video):
        print(TEXTS[lang]["retry_export_missing_file"], flush=True)
        return 1

    all_seqs = []
    for item in data.get("all_seqs") or []:
        if len(item) >= 3:
            all_seqs.append((int(item[0]), int(item[1]), bool(item[2])))
    if not all_seqs:
        print(TEXTS[lang]["retry_export_no_checkpoint"], flush=True)
        return 1

    print(TEXTS[lang]["retry_export_start"], flush=True)
    fps_float = float(data["fps_float"])
    fps_int = int(data["fps_int"])
    total_frames = int(data["total_frames"])
    return run_compare_export_pipeline(
        source_video, deepfake_video, settings, lang, all_seqs, fps_float, fps_int, total_frames
    )


def main(source_video, deepfake_video, settings):
    lang = (settings.get('language', 'en') or 'en')
    if isinstance(lang, str):
        lang = lang.lower()
    if lang not in TEXTS:
        lang = 'en'

    _remove_export_checkpoint_silent()

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
        
    base_dir = get_base_dir()
    local_ffmpeg = os.path.join(base_dir, "ffmpeg.exe")
    ffmpeg_exe = local_ffmpeg if os.path.exists(local_ffmpeg) else "ffmpeg"
    
    buffer_seconds = settings['buffer_seconds']
    noise_thresh = settings['pixel_noise_threshold']
    pixel_thresh = settings['changed_pixels_threshold']
    pixel_max = int(settings.get("changed_pixels_max_threshold", 0) or 0)
    enable_ffmpeg = settings['enable_ffmpeg_export']
    ffmpeg_export_target = settings['ffmpeg_export_target']
    ffmpeg_encoder = settings['ffmpeg_encoder']
    enable_fullcheck = settings['enable_fullcheck_edl']
    enable_autodelete_edl = settings['enable_autodelete_edl']
    enable_davinci = settings['enable_davinci_export']
    davinci_api_path = settings['davinci_api_path']
    final_export_dir = settings.get('final_export_dir', '')
    davinci_render_timeout_seconds = settings.get('davinci_render_timeout_seconds', 1800)
    scriptapp_retries = settings.get("davinci_scriptapp_retry_attempts", 60)
    scriptapp_delay = settings.get("davinci_scriptapp_retry_delay_seconds", 3.0)
    davinci_exe_path = settings.get("davinci_exe_path", "") or ""
    try:
        _dsw = settings.get("davinci_startup_wait_seconds", 20)
        davinci_startup_wait_seconds = max(0, min(600, int(_dsw)))
    except (TypeError, ValueError):
        davinci_startup_wait_seconds = 20

    if enable_davinci:
        ensure_resolve_running_for_compare(davinci_exe_path, davinci_startup_wait_seconds, lang)

    cap_src = cv2.VideoCapture(source_video)
    cap_df = cv2.VideoCapture(deepfake_video)

    try:
        opencv_fps_raw = float(cap_src.get(cv2.CAP_PROP_FPS))
    except (TypeError, ValueError):
        opencv_fps_raw = 0.0
    ffprobe_local = os.path.join(base_dir, "ffprobe.exe")
    ffprobe_exe = ffprobe_local if os.path.isfile(ffprobe_local) else shutil.which("ffprobe")
    r_fps, avg_fps = (None, None)
    if ffprobe_exe:
        r_fps, avg_fps = probe_video_stream_fps_rates(ffprobe_exe, source_video)
    picked = pick_analysis_fps_from_probes(opencv_fps_raw, r_fps, avg_fps, lang)
    if picked is not None:
        fps_float = float(picked)
        if (not opencv_fps_raw or opencv_fps_raw <= 0) and fps_float > 0:
            print(TEXTS[lang]['fps_ffprobe_only'].format(fps=f"{fps_float:.6g}"), flush=True)
    else:
        fps_float = opencv_fps_raw
    if not fps_float or fps_float <= 0:
        print(TEXTS[lang]['fps_fallback'])
        fps_float = 30.0
    fps_int = max(1, int(round(fps_float)))
    buffer_frames = int(fps_float * buffer_seconds)
    total_frames = int(cap_src.get(cv2.CAP_PROP_FRAME_COUNT))

    print_stream_sync_warnings(lang, ffprobe_exe, source_video, deepfake_video, cap_src, cap_df)

    print(TEXTS[lang]['loading_settings'])
    print(TEXTS[lang]['set_buffer'].format(val=buffer_seconds))
    print(TEXTS[lang]['set_noise'].format(val=noise_thresh))
    print(TEXTS[lang]['set_pixel'].format(val=pixel_thresh))
    print(TEXTS[lang]['set_pixel_max'].format(val=pixel_max))
    print(TEXTS[lang]['set_davinci'].format(val=TEXTS[lang]['on'] if enable_davinci else TEXTS[lang]['off']))
    if enable_davinci:
        _dto = davinci_render_timeout_seconds
        _tout = TEXTS[lang]['davinci_timeout_off'] if _dto == 0 else f"{_dto}s"
        print(TEXTS[lang]['set_davinci_timeout'].format(val=_tout))
    print(TEXTS[lang]['set_ffmpeg'].format(val=TEXTS[lang]['on'] if enable_ffmpeg else TEXTS[lang]['off']))
    if enable_ffmpeg:
        print(TEXTS[lang]['set_ffmpeg_target'].format(
            val=TEXTS[lang][f'ffmpeg_target_{ffmpeg_export_target}']
        ))
    print(TEXTS[lang]['set_fullcheck'].format(val=TEXTS[lang]['on'] if enable_fullcheck else TEXTS[lang]['off']))
    print(
        TEXTS[lang]['set_export_unique'].format(
            val=TEXTS[lang]['on'] if settings.get('export_avoid_overwrite') else TEXTS[lang]['off']
        )
    )

    print(TEXTS[lang]['start_analysis'].format(frames=total_frames))
    
    raw_diff = []
    actual_frame_count = 0
    
    for _ in range(total_frames):
        ret_s, frame_s = cap_src.read()
        ret_d, frame_d = cap_df.read()
        
        if not ret_s or not ret_d:
            break
            
        gray_s = cv2.cvtColor(frame_s, cv2.COLOR_BGR2GRAY)
        gray_d = cv2.cvtColor(frame_d, cv2.COLOR_BGR2GRAY)
        if gray_d.shape != gray_s.shape:
            gray_d = cv2.resize(gray_d, (gray_s.shape[1], gray_s.shape[0]), interpolation=cv2.INTER_LINEAR)
        
        diff = cv2.absdiff(gray_s, gray_d)
        _, thresh = cv2.threshold(diff, noise_thresh, 255, cv2.THRESH_BINARY)
        changed_pixels = cv2.countNonZero(thresh)

        has_diff = changed_pixels > pixel_thresh
        if has_diff and pixel_max > 0 and changed_pixels > pixel_max:
            has_diff = False
        raw_diff.append(has_diff)
        actual_frame_count += 1

        if total_frames > 0 and (actual_frame_count % 30 == 0 or actual_frame_count == total_frames):
            percent = (actual_frame_count / total_frames) * 100
            sys.stdout.write(TEXTS[lang]['analyzing'].format(percent=percent, current=actual_frame_count, total=total_frames))
            sys.stdout.flush()

    cap_src.release()
    cap_df.release()

    if total_frames > 0 and actual_frame_count < total_frames:
        print(
            TEXTS[lang]["sync_warn_truncated"].format(got=actual_frame_count, expected=total_frames),
            flush=True,
        )

    print(TEXTS[lang]['frames_processed'].format(count=actual_frame_count))
    
    keep_frames = []
    false_streak = 0
    
    for i in range(len(raw_diff)):
        if raw_diff[i]:
            keep_frames.append(i)
            false_streak = 0
        else:
            false_streak += 1
            if false_streak >= buffer_frames:
                keep_frames.append(i)
                if false_streak == buffer_frames:
                    for j in range(1, buffer_frames):
                        keep_frames.append(i - j)

    keep_frames_set = set(keep_frames)
    
    if not keep_frames_set:
        print(TEXTS[lang]['no_diff'])
        return 0

    all_seqs = []
    if actual_frame_count > 0:
        current_state = 0 in keep_frames_set
        start_frame = 0
        for i in range(1, actual_frame_count):
            state = i in keep_frames_set
            if state != current_state:
                all_seqs.append((start_frame, i, current_state))
                start_frame = i
                current_state = state
        all_seqs.append((start_frame, actual_frame_count, current_state))

    _write_export_checkpoint(source_video, deepfake_video, lang, all_seqs, fps_float, fps_int, total_frames)
    return run_compare_export_pipeline(
        source_video, deepfake_video, settings, lang, all_seqs, fps_float, fps_int, total_frames
    )

def get_files_via_gui(lang):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    source = filedialog.askopenfilename(title=TEXTS[lang]['file_dialog_source'], filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")])
    if not source:
        root.destroy()
        return None, None
        
    deepfake = filedialog.askopenfilename(title=TEXTS[lang]['file_dialog_df'], filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")])
    root.destroy()
    if not deepfake:
        return None, None
        
    return source, deepfake

def confirm_source(file1, file2, lang):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    name1 = os.path.basename(file1)
    answer = messagebox.askyesno(TEXTS[lang]['confirm_source_title'], TEXTS[lang]['confirm_source_msg'].format(name=name1))
    root.destroy()
    if answer:
        return file1, file2
    else:
        return file2, file1


def _strip_compare_script_from_argv(parts):
    """When launched as ``python compare.py A B``, argv[1] is this script — drop it."""
    if not parts:
        return parts
    if getattr(sys, "frozen", False):
        return parts
    try:
        here = os.path.abspath(__file__)
        p0 = os.path.abspath(parts[0])
        if os.path.isfile(parts[0]) and os.path.normcase(p0) == os.path.normcase(here):
            return parts[1:]
    except (OSError, ValueError, TypeError):
        pass
    return parts


def parse_compare_cli_args():
    """
    Normalize argv for compare.exe, ``python compare.py``, and ``python compare.py --`` from GUI.

    Returns (mode, a, b, retry_export_only) where mode is:
      'two_auto' | 'two_confirm' | 'one_file' | 'none'
    """
    parts = list(sys.argv[1:])
    retry_export_only = "--retry-export-only" in parts
    parts = [p for p in parts if p != "--retry-export-only"]
    if parts and parts[-1] == "--auto":
        parts = parts[:-1]
        auto = True
    else:
        auto = False
    parts = _strip_compare_script_from_argv(parts)

    if len(parts) == 2:
        return (("two_auto", parts[0], parts[1]) if auto else ("two_confirm", parts[0], parts[1])) + (
            retry_export_only,
        )
    if len(parts) == 1:
        return ("one_file", parts[0], None, retry_export_only)
    return ("none", None, None, retry_export_only)


if __name__ == "__main__":
    _ensure_stdio_utf8()
    settings = load_config()
    lang = settings.get('language', 'en').lower()
    if lang not in TEXTS:
        lang = 'en'
        
    source_video = None
    deepfake_video = None

    mode, path_a, path_b, retry_export_only = parse_compare_cli_args()

    if mode == "two_auto":
        source_video, deepfake_video = path_a, path_b
    elif mode == "two_confirm":
        source_video, deepfake_video = confirm_source(path_a, path_b, lang)
    elif mode == "one_file":
        cache_file = os.path.join(get_base_dir(), "autocut_cache.txt")
        current_file = path_a

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_file = f.read().strip()
            
            os.remove(cache_file)

            if cached_file == current_file:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                messagebox.showinfo(TEXTS[lang]['abort_double_file_title'], TEXTS[lang]['abort_double_file_msg'])
                root.destroy()
                sys.exit(0)

            source_video, deepfake_video = confirm_source(cached_file, current_file, lang)
        else:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(current_file)
            
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo(TEXTS[lang]['cache_step1_title'], TEXTS[lang]['cache_step1_msg'].format(name=os.path.basename(current_file)))
            root.destroy()
            sys.exit(0)
    else:
        print(TEXTS[lang]['no_files_sendto'])
        source_video, deepfake_video = get_files_via_gui(lang)

    if not source_video or not deepfake_video:
        print(TEXTS[lang]['abort_not_both'])
        input(TEXTS[lang]['press_enter'])
        sys.exit(1)
        
    is_auto_mode = mode == "two_auto"

    status = 0
    try:
        if retry_export_only:
            if mode != "two_auto":
                print(TEXTS[lang]["retry_export_auto_only"], flush=True)
                status = 1
            else:
                status = run_retry_export_from_checkpoint(source_video, deepfake_video, settings)
        else:
            status = main(source_video, deepfake_video, settings)
        if status is None:
            status = 0
    except Exception as e:
        try:
            print(TEXTS[lang]['unexpected_error'].format(error=e))
        except UnicodeEncodeError:
            print(
                TEXTS[lang]['unexpected_error']
                .format(error=e)
                .encode("ascii", errors="replace")
                .decode("ascii")
            )
        # Im Fehlerfall auch bei Auto-Mode kurz warten, damit man die Fehlermeldung lesen kann
        if is_auto_mode:
            time.sleep(10)
        sys.exit(1)

    if not is_auto_mode:
        input(TEXTS[lang]['press_enter'])
    sys.exit(int(status))