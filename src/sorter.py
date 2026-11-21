"""Will's Sorter engine: sort, zip and clean a Downloads folder.

Standard library only. The window (app.py) and the daily background run both
call organize(); `python sorter.py --run` is what the daily task executes.

Each pass:
  1. SORT   loose files go into category folders, with tidied names.
  2. ZIP    old files that compress well go into <Category>/Zipped/<month>.zip.
  3. CLEAN  old installers and abandoned partial downloads go to the Recycle Bin.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
import zlib
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

ROOT_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT_DIR / "settings.json"
LOG_PATH = ROOT_DIR / "logs" / "activity.log"
MAX_LOG_BYTES = 1_000_000
TASK_NAME = "Wills Sorter"
WINDOWS = sys.platform == "win32"

DEFAULTS = {
    "folder": "",              # empty = this PC's Downloads folder
    "zip_after_days": 60,
    "delete_after_days": 90,
    "use_recycle_bin": True,
    "daily_time": "12:00",
    "min_age_minutes": 10,     # leave very recent files alone (may still be downloading)
    "zip_max_file_mb": 500,
    "appearance": "light",
}

CATEGORIES = {
    "Documents": "pdf doc docx odt rtf txt md pages epub mobi",
    "Spreadsheets": "xls xlsx xlsm csv tsv ods numbers",
    "Presentations": "ppt pptx key odp",
    "Images": "jpg jpeg png gif webp heic bmp tif tiff svg ico raw cr2 nef dng",
    "Videos": "mp4 mov mkv avi wmv webm m4v flv",
    "Audio": "mp3 wav flac m4a aac ogg wma aiff",
    "Design": "psd psb ai indd eps fig sketch xd afdesign afphoto",
    "Fonts": "ttf otf woff woff2",
    "Code and Data": "json xml html htm css js ts py ps1 sql yaml yml log ics vcf",
    "Archives": "zip rar 7z tar gz bz2 xz tgz",
    "Installers": "exe msi msix appx iso dmg pkg apk",
}
OTHER = "Other"
EXT_TO_CATEGORY = {ext: cat for cat, exts in CATEGORIES.items() for ext in exts.split()}

# Types worth zipping; already-compressed ones (jpg, mp4, docx, pdf) gain nothing.
COMPRESSIBLE = set(
    "doc rtf txt md xls csv tsv json xml html htm css js ts py sql yaml yml log bmp tif tiff "
    "svg psd psb ai eps wav aiff raw cr2 nef dng ppt ttf otf".split())
DELETE_CATEGORIES = ("Installers",)          # old files here are considered useless
NO_ZIP_CATEGORIES = DELETE_CATEGORIES + ("Archives",)
PARTIAL_EXTENSIONS = set("crdownload part partial download tmp opdownload".split())
ZIP_FOLDER = "Zipped"


# ------------------------------- settings -------------------------------

def load_settings():
    settings = dict(DEFAULTS)
    try:
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            for key, default in DEFAULTS.items():
                if key in saved and isinstance(saved[key], type(default)):
                    settings[key] = saved[key]
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps({k: settings[k] for k in DEFAULTS}, indent=2), encoding="utf-8")


def downloads_folder():
    """This PC's real Downloads folder (it can be relocated on Windows)."""
    if WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD),
                            ("d4", ctypes.c_ubyte * 8)]

            # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}
            folder_id = GUID(0x374DE290, 0x123F, 0x4565,
                             (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
            found = ctypes.c_wchar_p()
            get_path = ctypes.windll.shell32.SHGetKnownFolderPath
            get_path.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
                                 ctypes.POINTER(ctypes.c_wchar_p)]
            if get_path(ctypes.byref(folder_id), 0, None, ctypes.byref(found)) == 0 and found.value:
                path = Path(found.value)
                ctypes.windll.ole32.CoTaskMemFree(found)
                if path.is_dir():
                    return path
        except Exception:
            pass
    return Path.home() / "Downloads"


def target_folder(settings):
    return Path(settings["folder"]) if settings.get("folder") else downloads_folder()


# -------------------------------- helpers --------------------------------

def log(message):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > MAX_LOG_BYTES:
            LOG_PATH.unlink()
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}\n")
    except OSError:
        pass


def format_size(count):
    if count >= 1024 ** 3:
        return f"{count / 1024 ** 3:,.1f} GB"
    if count >= 1024 ** 2:
        return f"{count / 1024 ** 2:,.1f} MB"
    return f"{count / 1024:,.0f} KB"


def ext_of(path):
    return path.suffix.lstrip(".").lower()


def category_of(path):
    return EXT_TO_CATEGORY.get(ext_of(path), OTHER)


def clean_name(stem):
    """'Q3_report%20final (1)' -> 'Q3 report final'"""
    name = unquote(stem)
    name = re.sub(r'[\\/:*?"<>|]', "-", name)
    name = re.sub(r"_+", " ", name)
    name = re.sub(r"(?<=\w)\++(?=\w)", " ", name)
    name = re.sub(r"\s*\(\d{1,2}\)\s*$", "", name)                     # browser "(1)" copies
    name = re.sub(r"\s*-\s*Copy(\s*\(\d+\))?\s*$", "", name, flags=re.I)  # Explorer " - Copy"
    name = re.sub(r"\s{2,}", " ", name).strip(" .-")
    return name or stem


def file_time(path):
    """Later of created and last modified, so a file's age is counted from
    when it reached this PC, not from when its author last saved it."""
    info = path.stat()
    created = getattr(info, "st_birthtime", info.st_ctime if WINDOWS else info.st_mtime)
    return max(created, info.st_mtime)


def age_days(path):
    return (time.time() - file_time(path)) / 86400


def unique_path(folder, stem, suffix):
    candidate = folder / (stem + suffix)
    number = 2
    while candidate.exists():
        candidate = folder / f"{stem} ({number}){suffix}"
        number += 1
    return candidate


def _digest(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.digest()


def same_content(a, b):
    return a.stat().st_size == b.stat().st_size and _digest(a) == _digest(b)


def _crc(path):
    value = 0
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            value = zlib.crc32(block, value)
    return value & 0xFFFFFFFF


def _recycle_windows(path):
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _pack_ = 1 if ctypes.sizeof(ctypes.c_void_p) == 4 else 8   # 32-bit Windows packs this struct
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", ctypes.c_void_p),
                    ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort),
                    ("fAnyOperationsAborted", wintypes.BOOL), ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", wintypes.LPCWSTR)]

    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    # The path list must end with two nulls; the zero-filled buffer supplies them.
    source = ctypes.create_unicode_buffer(str(path), len(str(path)) + 2)
    operation = SHFILEOPSTRUCTW(
        None, FO_DELETE, ctypes.addressof(source),
        None, FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI, False, None, None)
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if result != 0 or operation.fAnyOperationsAborted:
        raise OSError(f"Windows could not move it to the Recycle Bin (code {result})")


def remove_file(path, use_recycle_bin=True):
    if use_recycle_bin and WINDOWS:
        _recycle_windows(path)
    else:
        path.unlink()


# --------------------------------- engine ---------------------------------

def organize(folder, settings, preview=False, emit=None, cancelled=None):
    """Run one pass over `folder`.

    Calls emit(kind, name, detail) for every action, where kind is one of
    "sorted", "duplicate", "zipped", "removed", "skipped". Returns the totals.
    With preview=True nothing on disk changes.
    """
    folder = Path(folder)
    stats = {"sorted": 0, "duplicate": 0, "zipped": 0, "zip_saved": 0,
             "removed": 0, "removed_bytes": 0, "skipped": 0}
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")
    prefix = "[preview] " if preview else ""
    stop = cancelled or (lambda: False)

    def report(kind, name, detail):
        if kind in stats:
            stats[kind] += 1
        log(f"{prefix}{kind.upper():<9} {name}  ->  {detail}")
        if emit:
            emit(kind, name, detail)

    log(f"{prefix}=== Organizing {folder} ===")
    recent = time.time() - settings["min_age_minutes"] * 60
    use_bin = settings["use_recycle_bin"]
    bin_word = "Recycle Bin" if use_bin and WINDOWS else "deleted"
    pending = {}   # preview only: files that would have been moved into each category

    def category_files(category):
        directory = folder / category
        found = [p for p in directory.iterdir() if p.is_file()] if directory.is_dir() else []
        return sorted(found + pending.get(category, []), key=lambda p: p.name.lower())

    def visible(path):
        return path.is_file() and not path.name.startswith(".") and path.name.lower() != "desktop.ini"

    # ---- 1. SORT ----
    for path in sorted((p for p in folder.iterdir() if visible(p)), key=lambda p: p.name.lower()):
        if stop():
            break
        try:
            if ext_of(path) in PARTIAL_EXTENSIONS or path.stat().st_mtime > recent:
                continue
            category = category_of(path)
            destination = folder / category
            target = destination / (clean_name(path.stem) + path.suffix)
            if target.exists():
                if same_content(path, target):
                    if not preview:
                        remove_file(path, use_bin)
                    report("duplicate", path.name, f"same as {category}/{target.name} ({bin_word})")
                    continue
                target = unique_path(destination, clean_name(path.stem), path.suffix)
            if preview:
                pending.setdefault(category, []).append(path)
            else:
                destination.mkdir(exist_ok=True)
                shutil.move(str(path), str(target))
            report("sorted", path.name, f"{category}/{target.name}")
        except OSError as error:
            report("skipped", path.name, str(error))

    # ---- 2. ZIP ----
    max_bytes = settings["zip_max_file_mb"] * 1024 * 1024
    for category in list(CATEGORIES) + [OTHER]:
        if stop() or category in NO_ZIP_CATEGORIES:
            continue
        groups = {}
        for path in category_files(category):
            try:
                if (ext_of(path) in COMPRESSIBLE and age_days(path) >= settings["zip_after_days"]
                        and path.stat().st_size <= max_bytes):
                    month = datetime.fromtimestamp(file_time(path)).strftime("%Y-%m")
                    groups.setdefault(month, []).append(path)
            except OSError:
                continue
        for month, paths in sorted(groups.items()):
            zip_path = folder / category / ZIP_FOLDER / f"{category} {month}.zip"
            where = f"{category}/{ZIP_FOLDER}/{zip_path.name}"
            if preview:
                for path in paths:
                    report("zipped", path.name, where)
                continue
            try:
                zip_path.parent.mkdir(parents=True, exist_ok=True)
                before = zip_path.stat().st_size if zip_path.exists() else 0
                added = {}   # entry name -> original path
                with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                    taken = {name.lower() for name in archive.namelist()}
                    for path in paths:
                        entry, number = path.name, 2
                        while entry.lower() in taken:
                            entry = f"{path.stem} ({number}){path.suffix}"
                            number += 1
                        try:
                            archive.write(path, entry)
                            taken.add(entry.lower())
                            added[entry] = path
                        except OSError as error:
                            report("skipped", path.name, f"could not zip: {error}")
                # Remove an original only once its copy in the zip checks out.
                original_bytes = 0
                with zipfile.ZipFile(zip_path) as archive:
                    for entry, path in added.items():
                        info = archive.getinfo(entry)
                        size = path.stat().st_size
                        if info.file_size == size and info.CRC == _crc(path):
                            path.unlink()
                            original_bytes += size
                            report("zipped", path.name, where)
                        else:
                            report("skipped", path.name, "zip check failed, original kept")
                stats["zip_saved"] += original_bytes - (zip_path.stat().st_size - before)
            except (OSError, zipfile.BadZipFile) as error:
                report("skipped", zip_path.name, f"zip problem: {error}")

    # ---- 3. CLEAN ----
    stale = [p for category in DELETE_CATEGORIES for p in category_files(category)]
    stale += [p for p in folder.iterdir() if visible(p) and ext_of(p) in PARTIAL_EXTENSIONS]
    for path in stale:
        if stop():
            break
        try:
            days = age_days(path)
            if days < settings["delete_after_days"]:
                continue
            size = path.stat().st_size
            if not preview:
                remove_file(path, use_bin)
            stats["removed_bytes"] += size
            report("removed", path.name, f"{days:,.0f} days old, {format_size(size)} ({bin_word})")
        except OSError as error:
            report("skipped", path.name, str(error))

    log(prefix + summary(stats, preview))
    return stats


def summary(stats, preview=False):
    would = "would be " if preview else ""
    return (f"{stats['sorted']} {would}sorted, {stats['duplicate']} duplicates {would}removed, "
            f"{stats['zipped']} {would}zipped"
            + ("" if preview else f" (saved {format_size(max(0, stats['zip_saved']))})")
            + f", {stats['removed']} old files {would}removed ({format_size(stats['removed_bytes'])}), "
            f"{stats['skipped']} skipped.")


# ------------------------- daily background run -------------------------

_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Sorts, zips and cleans the Downloads folder (Will's Sorter).</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{time}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <Enabled>true</Enabled>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def _schtasks(*args):
    return subprocess.run(["schtasks", *args], capture_output=True, text=True,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def valid_time(text):
    return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", text or ""))


def daily_task_installed():
    return WINDOWS and _schtasks("/Query", "/TN", TASK_NAME).returncode == 0


def install_daily_task(daily_time):
    """Run a pass every day at `daily_time` (HH:MM); a missed run happens at
    the next start. Needs no administrator rights. Returns (ok, message)."""
    if not WINDOWS:
        return False, "The daily run uses Windows Task Scheduler, so it can only be turned on from a Windows PC."
    if not valid_time(daily_time):
        return False, "Enter the time as HH:MM on a 24-hour clock, for example 12:00."
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    command = str(pythonw if pythonw.exists() else sys.executable)
    arguments = f'"{Path(__file__).resolve()}" --run'
    from xml.sax.saxutils import escape
    xml_path = ROOT_DIR / "logs" / "daily_task.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(_TASK_XML.format(time=daily_time, command=escape(command), arguments=escape(arguments)),
                        encoding="utf-16")
    result = _schtasks("/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F")
    if result.returncode != 0:
        # Plain form: same schedule, but a run missed while the PC is off is skipped.
        result = _schtasks("/Create", "/TN", TASK_NAME, "/SC", "DAILY", "/ST", daily_time,
                           "/TR", f'"{command}" {arguments}', "/F")
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "Task Scheduler refused the task.").strip()
    return True, f"Daily run is on, every day at {daily_time}."


def remove_daily_task():
    if not daily_task_installed():
        return True, "Daily run is off."
    result = _schtasks("/Delete", "/TN", TASK_NAME, "/F")
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, "Daily run is off."


# ---------------------------------- CLI ----------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Will's Sorter: organize the Downloads folder.")
    parser.add_argument("--run", action="store_true", help="run one pass now")
    parser.add_argument("--preview", action="store_true", help="list what a pass would do; change nothing")
    parser.add_argument("--path", help="folder to organize (default: the saved folder, else Downloads)")
    args = parser.parse_args(argv)
    if not (args.run or args.preview):
        parser.print_help()
        return 0
    settings = load_settings()
    folder = Path(args.path) if args.path else target_folder(settings)

    def show(kind, name, detail):
        if sys.stdout:   # pythonw has no console
            print(f"{kind:<9} {name}  ->  {detail}")

    try:
        stats = organize(folder, settings, preview=args.preview, emit=show)
    except OSError as error:
        log(f"FAILED    {error}")
        if sys.stdout:
            print(error)
        return 1
    if sys.stdout:
        print(summary(stats, args.preview))
    return 0


if __name__ == "__main__":
    sys.exit(main())
