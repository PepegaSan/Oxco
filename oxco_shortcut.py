#!/usr/bin/env python3
"""Desktop-Verknuepfung mit Icon + AppUserModelID (Taskleisten-Icon unter Windows)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

OXCO_APP_USER_MODEL_ID = "PepegaSan.Oxco.GUI.1"


def _root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resolve_icon(root: Path) -> Path:
    for candidate in (
        root / "assets" / "oxco_icon.ico",
        root / "dist" / "Oxco" / "assets" / "oxco_icon.ico",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Oxco" / "oxco_icon.ico",
    ):
        if candidate.is_file():
            return candidate.resolve()
    try:
        sys.path.insert(0, str(root))
        from oxco_icon_embed import materialize_icon_ico

        return materialize_icon_ico().resolve()
    except Exception:
        return root / "assets" / "oxco_icon.ico"


def _resolve_target(root: Path) -> tuple[str, str]:
    exe = root / "dist" / "Oxco" / "Oxco.exe"
    if exe.is_file():
        return str(exe.resolve()), ""
    gui = root / "oxco_gui.py"
    from shutil import which

    for launcher in ("pythonw", "python"):
        found = which(launcher)
        if found and gui.is_file():
            return found, f'"{gui.resolve()}"'
    raise FileNotFoundError("Weder dist\\Oxco\\Oxco.exe noch python + oxco_gui.py gefunden.")


def _vbs_quote(value: str) -> str:
    return value.replace('"', '""')


def _create_shortcut(lnk: Path, target: str, args: str, workdir: Path, icon: Path, description: str) -> None:
    body = [
        f'Set sc = CreateObject("WScript.Shell").CreateShortcut("{_vbs_quote(str(lnk))}")',
        f'sc.TargetPath = "{_vbs_quote(target)}"',
        f'sc.WorkingDirectory = "{_vbs_quote(str(workdir))}"',
        f'sc.Description = "{_vbs_quote(description)}"',
        f'sc.IconLocation = "{_vbs_quote(str(icon))},0"',
    ]
    if args:
        body.append(f'sc.Arguments = "{_vbs_quote(args)}"')
    body.append("sc.Save")

    with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="ascii", errors="replace") as tmp:
        tmp.write("\r\n".join(body))
        vbs_path = tmp.name

    try:
        completed = subprocess.run(
            ["cscript", "//nologo", vbs_path],
            capture_output=True,
            text=True,
            encoding="ascii",
            errors="replace",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "shortcut failed").strip())
    finally:
        try:
            os.unlink(vbs_path)
        except OSError:
            pass


def _set_shortcut_app_id(lnk: Path, app_id: str) -> bool:
    """AppUserModelID auf .lnk setzen (optional, braucht pywin32)."""
    try:
        import pythoncom
        import pywintypes
        from win32com.propsys import propsys, pscon
    except ImportError:
        return False

    try:
        gps_readwrite = getattr(propsys, "GPS_READWRITE", 0x2)
        iid_store = getattr(
            propsys,
            "IID_IPropertyStore",
            pywintypes.IID("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}"),
        )
        store = propsys.SHGetPropertyStoreFromParsingName(
            str(lnk.resolve()),
            None,
            gps_readwrite,
            iid_store,
        )
        store.SetValue(pscon.PKEY_AppUserModel_ID, app_id)
        store.Commit()
        return True
    except Exception:
        return False


def main() -> int:
    root = _root_dir()
    desktop = Path(os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"))
    if not desktop.is_dir():
        print("Desktop-Ordner nicht gefunden.")
        return 1

    icon = _resolve_icon(root)
    if not icon.is_file():
        print("oxco_icon.ico nicht gefunden.")
        return 1

    try:
        target, args = _resolve_target(root)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    lnk = desktop / "Oxco.lnk"
    _create_shortcut(
        lnk,
        target,
        args,
        root,
        icon,
        "Oxco - Compare, Bitrate, Autotagger",
    )
    if _set_shortcut_app_id(lnk, OXCO_APP_USER_MODEL_ID):
        print("AppUserModelID gesetzt (Taskleisten-Icon).")
    else:
        print("Hinweis: AppUserModelID nicht gesetzt (Verknuepfung + Icon trotzdem OK).")

    print(f"Verknuepfung erstellt: {lnk}")
    print("Bitte Oxco nur noch ueber diese Verknuepfung starten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
