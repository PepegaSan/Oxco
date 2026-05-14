# Oxco

Oxco is a small **desktop app** (Windows-friendly) that bundles a few video helpers in one place:

- **Compare** — load two videos, scan frame differences with adjustable sensitivity, and optionally drive exports or edits (see the in-app help for details).
- **Bitrate** — scan folders and transcode videos using simple height-based rules.
- **Preview** — scrub two clips side by side to tune thresholds before a full compare run.
- **Autotagger** — rename and move files using a filename pattern you define.

It is meant for personal workflows (e.g. checking edits, batch housekeeping), not as a forensic guarantee.

## Screenshot

![Oxco main window](UI.png)

Screenshot of the main Oxco window (`UI.png` in the repository root).

## Requirements

- **Windows** is the primary target (other platforms are untested).
- **Python 3.10+** if you run from source.

### FFmpeg / ffprobe (recommended)

For reliable video analysis and optional exports, **ffmpeg** and **ffprobe** must be available:

- **Option A:** Install them and add both to your system **PATH**, or  
- **Option B:** Place `ffmpeg.exe` and `ffprobe.exe` in the **same folder** as `Oxco.exe` (release build) or next to `compare.py` / the project root when running from source.

Without them, some features may fail or fall back to limited behaviour.

### DaVinci Resolve (optional)

DaVinci-related actions only run if you install **DaVinci Resolve Studio**, enable scripting, and fill in the paths in `settings.ini` (see the example file).

## Quick start (source)

1. Clone the repository.
2. Double-click **`install.bat`** (or run `pip install -r requirements.txt` in the project folder).
3. Copy **`settings.example.ini`** to **`settings.ini`** in the same folder (Oxco creates this copy on first launch if it is missing).
4. Run **`python oxco_gui.py`**.

Your window layout and paths are stored in **`oxco_config.json`** in the app folder. The repository ships a **neutral template**; replace values with your own.

## Windows one-folder executable

Use **`build_onedir.bat`**. It installs PyInstaller if needed and writes `dist/Oxco/`.

- **`compare.py`** and **`settings.example.ini`** are placed next to **`Oxco.exe`** automatically by the build script.
- On first launch, Oxco copies `settings.example.ini` → `settings.ini` if it is missing.
- You still need **ffmpeg/ffprobe** on PATH or beside the executable for full support.

### What works in the `.exe`?

It is the **same application** as when you run `python oxco_gui.py`: all tabs (workflow, filters, paths, log), the **Preview** player (OpenCV, Pillow, Tk), bitrate tools, and the autotagger are packaged into the bundle (`Oxco.exe` plus the `_internal` folder).  

**Compare** does not use a separate Python install: Oxco starts a second copy of **`Oxco.exe`** with the hidden flag **`--oxco-compare`**, which runs `compare.py` from the folder next to the executable — so behaviour stays aligned with the source tree.

## License

This project is released under the **MIT License** — see [`LICENSE`](LICENSE).
