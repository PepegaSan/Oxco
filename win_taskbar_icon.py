"""
win_taskbar_icon.py
===================
Taskleisten- und Fenster-Icon fuer Python/Tkinter unter Windows.

Problem: Bei ``python mein_programm.py`` zeigt Windows oft das Python-Logo,
obwohl ``iconbitmap()`` gesetzt ist. Dieses Modul setzt:
  1. AppUserModelID (vor dem ersten Tk()-Fenster)
  2. Icon auf alle relevanten HWNDs (inkl. Root-Fenster / GetAncestor)

Abhaengigkeiten: nur Python-Standardbibliothek + tkinter.

Schnellstart (Tkinter)
----------------------
::

    import tkinter as tk
    import win_taskbar_icon as wti

    APP_ID = "MeineFirma.MeinTool.1"          # eindeutig pro Programm
    ICON = r"C:\\Pfad\\zu\\app.ico"           # .ico mit 16/32/48 px

    wti.prepare(APP_ID)                       # VOR tk.Tk()
    root = tk.Tk()
    root.title("Mein Tool")
    wti.apply(root, ICON)                     # NACH Aufbau der UI
    root.mainloop()

PyInstaller (.exe)
------------------
Icon in die EXE einbetten (``--icon app.ico``). Dann::

    wti.prepare(APP_ID)
    root = tk.Tk()
    wti.apply(root, ICON, prefer_exe_when_frozen=True)

Verknuepfung (empfohlen fuer Skript-Start)
------------------------------------------
Taskleiste + Icon zuverlaessiger ueber Desktop-.lnk mit gleicher AppUserModelID.
Siehe ``oxco_shortcut.py`` als Vorlage.

.ico erzeugen
-------------
Mit Pillow aus PNG::

    img.save("app.ico", format="ICO", sizes=[(16,16),(32,32),(48,48),(256,256)])
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Set, Union

import tkinter as tk

IconSource = Union[str, Path, os.PathLike[str]]
GA_ROOT = 2


def prepare(app_id: str) -> None:
    """AppUserModelID setzen — immer VOR ``tk.Tk()`` aufrufen."""
    if sys.platform != "win32" or not app_id.strip():
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id.strip())
    except (AttributeError, OSError, ValueError):
        pass


def cache_icon(source: IconSource, app_name: str = "App") -> Optional[Path]:
    """Ico nach ``%LOCALAPPDATA%\\<app_name>\\`` kopieren (stabiler Pfad fuer Tcl/Win32)."""
    src = Path(source)
    if not src.is_file():
        return None
    dest_dir = Path(os.environ.get("LOCALAPPDATA", "")) / app_name
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        data = src.read_bytes()
        if not dest.is_file() or dest.read_bytes() != data:
            dest.write_bytes(data)
        return dest
    except OSError:
        return src


def resolve_icon_path(
    icon: IconSource,
    *,
    app_name: str = "App",
    prefer_exe_when_frozen: bool = False,
    use_cache: bool = True,
) -> Optional[str]:
    """Pfad fuer LoadImageW / iconbitmap aufloesen."""
    if prefer_exe_when_frozen and getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        if exe.is_file():
            return str(exe.resolve())
    path = Path(icon)
    if use_cache:
        cached = cache_icon(path, app_name=app_name)
        if cached is not None and cached.is_file():
            return str(cached.resolve())
    if path.is_file():
        return str(path.resolve())
    if prefer_exe_when_frozen and getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        if exe.is_file():
            return str(exe.resolve())
    return None


def _iter_icon_hwnds(root: tk.Misc) -> Iterable[int]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    pid = os.getpid()
    found: Set[int] = set()

    try:
        root.update_idletasks()
        hwnd = int(root.winfo_id())
    except (tk.TclError, ValueError, TypeError):
        hwnd = 0

    if hwnd:
        found.add(hwnd)
        ancestor = user32.GetAncestor(hwnd, GA_ROOT)
        if ancestor:
            found.add(int(ancestor))
        parent = user32.GetParent(hwnd)
        while parent:
            found.add(int(parent))
            parent = user32.GetParent(parent)

    title = ""
    try:
        title = root.title()
    except tk.TclError:
        title = ""

    if title:
        by_title = user32.FindWindowW(None, title)
        if by_title:
            found.add(int(by_title))
            ancestor = user32.GetAncestor(by_title, GA_ROOT)
            if ancestor:
                found.add(int(ancestor))

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd_l: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd_l):
            return True
        proc = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd_l, ctypes.byref(proc))
        if proc.value == pid:
            found.add(int(hwnd_l))
            ancestor = user32.GetAncestor(hwnd_l, GA_ROOT)
            if ancestor:
                found.add(int(ancestor))
        return True

    try:
        user32.EnumWindows(_enum, 0)
    except (OSError, ValueError):
        pass

    return sorted(found)


def _load_icons(icon_path: str, *, from_frozen_exe: bool) -> tuple[int, int]:
    import ctypes

    user32 = ctypes.windll.user32
    LR_DEFAULTSIZE = 0x0040
    LR_LOADFROMFILE = 0x0010
    IMAGE_ICON = 1

    small = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
    if not big:
        big = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
    if not small and big:
        small = big

    if not from_frozen_exe:
        return int(small or 0), int(big or 0)
    if big and small:
        return int(small), int(big)

    large = ctypes.c_ulong()
    small_h = ctypes.c_ulong()
    count = ctypes.windll.shell32.ExtractIconExW(icon_path, 0, ctypes.byref(large), ctypes.byref(small_h), 1)
    if count > 0:
        return int(small_h.value or 0), int(large.value or 0)
    return int(small or 0), int(big or 0)


def _win32_set_window_icons(hwnd: int, small: int, big: int) -> bool:
    if not hwnd or (not small and not big):
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1
    GWLP_HICON = -14
    GWLP_HICONSM = -34

    if hasattr(user32, "SetWindowLongPtrW"):
        set_long = user32.SetWindowLongPtrW
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE]
        set_long.restype = ctypes.c_void_p
    else:
        set_long = user32.SetWindowLongW
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE]
        set_long.restype = wintypes.LONG

    ok = False
    if small:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
        set_long(hwnd, GWLP_HICONSM, small)
        ok = True
    if big:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
        set_long(hwnd, GWLP_HICON, big)
        ok = True
    return ok


def apply(
    root: tk.Misc,
    icon: IconSource,
    *,
    app_name: str = "App",
    prefer_exe_when_frozen: bool = False,
    use_cache: bool = True,
) -> bool:
    """
    Icon auf Tk-Fenster und Taskleiste anwenden.

    ``root``: Tk/Toplevel nach ``update_idletasks()`` oder am Ende von ``__init__``.
    ``icon``: Pfad zu ``.ico`` (oder ``.exe`` bei PyInstaller + prefer_exe_when_frozen).
    """
    icon_path = resolve_icon_path(
        icon,
        app_name=app_name,
        prefer_exe_when_frozen=prefer_exe_when_frozen,
        use_cache=use_cache,
    )
    if not icon_path:
        return False

    is_exe = icon_path.lower().endswith(".exe")
    if not is_exe:
        tcl_path = icon_path.replace("\\", "/")
        try:
            root.iconbitmap(default=tcl_path)
        except tk.TclError:
            pass
        try:
            root.tk.call("wm", "iconbitmap", root._w, "-bitmap", tcl_path)
        except tk.TclError:
            pass

    if sys.platform != "win32":
        return True

    from_frozen = bool(prefer_exe_when_frozen and getattr(sys, "frozen", False) and is_exe)
    small, big = _load_icons(icon_path, from_frozen_exe=from_frozen)

    def _apply_win32() -> None:
        try:
            for hwnd in _iter_icon_hwnds(root):
                _win32_set_window_icons(hwnd, small, big)
        except (OSError, ValueError, AttributeError, tk.TclError):
            pass

    _apply_win32()
    try:
        root.after_idle(_apply_win32)
        for delay in (50, 250, 1000, 3000):
            root.after(delay, _apply_win32)
        root.bind("<Map>", lambda _e: _apply_win32(), add="+")
        root.bind("<FocusIn>", lambda _e: _apply_win32(), add="+")
        root.bind("<Configure>", lambda _e: _apply_win32(), add="+")
    except tk.TclError:
        pass
    return bool(small or big)


if __name__ == "__main__":
    import tkinter as tk

    DEMO_APP_ID = "Example.DemoApp.1"
    demo_ico = Path(__file__).resolve().parent / "assets" / "oxco_icon.ico"

    prepare(DEMO_APP_ID)
    window = tk.Tk()
    window.title("win_taskbar_icon Demo")
    window.geometry("420x200")
    tk.Label(
        window,
        text="Taskleisten-Icon-Test\nSchliesst sich nach 5 Sekunden.",
        padx=16,
        pady=16,
    ).pack(expand=True)
    window.update_idletasks()
    ok = apply(window, demo_ico, app_name="DemoApp")
    print("Icon angewendet:" if ok else "Icon nicht gefunden:", demo_ico)
    window.after(5000, window.destroy)
    window.mainloop()
