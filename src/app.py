"""Will's Sorter desktop window. Same shell and styles as Partners Toolbox.

The window only presents and starts work; every file operation lives in
sorter.py, which the daily background run uses too.
"""
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT_DIR = Path(__file__).resolve().parent.parent

import sorter  # noqa: E402
import theme  # noqa: E402
from ui_runtime import UiDispatcher  # noqa: E402

APP_TITLE = "Will's Sorter"
ICON_PATH = ROOT_DIR / "assets" / "app_icon.ico"
ACTION_LABELS = {"sorted": "Sorted", "duplicate": "Duplicate", "zipped": "Zipped",
                 "removed": "Removed", "skipped": "Skipped"}
PREVIEW_LABELS = {"sorted": "Will sort", "duplicate": "Duplicate", "zipped": "Will zip",
                  "removed": "Will remove", "skipped": "Skipped"}


class SorterApp:
    WORKSPACES = (
        ("organize", "Organize", "Organize Downloads",
         "Preview what a pass would do, then sort, zip and clean the folder."),
        ("settings", "Settings", "Settings",
         "Choose how old files must be before they are zipped or removed, and when the daily run happens."),
        ("activity", "Activity log", "Activity log",
         "Everything the sorter has done, including daily background runs."),
    )

    def __init__(self, root):
        self.root = root
        self.settings = sorter.load_settings()
        self._busy = False
        self._cancel = threading.Event()
        self._closing = False

        root.title(APP_TITLE)
        width = min(1120, max(940, root.winfo_screenwidth() - 80))
        height = min(760, max(620, root.winfo_screenheight() - 100))
        root.geometry(f"{width}x{height}")
        root.minsize(940, 620)
        theme.apply(root)
        theme.set_icon(root, ICON_PATH)
        self.ui = UiDispatcher(root)

        self._build_shell()
        self._build_organize(self.pages["organize"])
        self._build_settings(self.pages["settings"])
        self._build_activity(self.pages["activity"])
        self.show_workspace("organize")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        theme.bind_quit(root, self._on_close)

    # ------------------------------- shell -------------------------------

    def _build_shell(self):
        body = ttk.Frame(self.root, style="Workspace.TFrame")
        body.pack(fill="both", expand=True)
        sidebar = ttk.Frame(body, style="Sidebar.TFrame", width=204, padding=(12, 20, 12, 16))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(8, 0, 8, 16))
        brand.pack(fill="x")
        ttk.Label(brand, text="WS", style="BrandMark.TLabel").pack(anchor="w", pady=(0, 12))
        ttk.Label(brand, text="Will's", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(brand, text="Sorter", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(brand, text="Downloads organizer", style="SidebarHint.TLabel").pack(anchor="w", pady=(8, 0))

        footer = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(8, 12, 0, 0))
        footer.pack(side="bottom", fill="x")
        ttk.Label(footer, text="KEYBOARD SHORTCUTS", style="SidebarHeading.TLabel").pack(anchor="w")
        ttk.Label(footer, text=f"{theme.SHORTCUT_LABEL} 1 / 2 / 3", style="SidebarHint.TLabel").pack(anchor="w", pady=(6, 0))
        self.mode_button = ttk.Button(sidebar, style="Nav.TButton", command=self._toggle_mode)
        self.mode_button.pack(side="bottom", fill="x", pady=3)
        self._show_mode()

        ttk.Label(sidebar, text="DOWNLOADS", style="SidebarHeading.TLabel").pack(anchor="w", padx=16, pady=(16, 8))
        self.nav_buttons = {}
        for index, (key, label, _title, _subtitle) in enumerate(self.WORKSPACES):
            button = ttk.Button(sidebar, text=label, style="Nav.TButton",
                                command=lambda name=key: self.show_workspace(name))
            button.pack(fill="x", pady=3)
            self.nav_buttons[key] = button
            self.root.bind(f"<{theme.SHORTCUT_KEY}-Key-{index + 1}>",
                           lambda event, name=key: self._navigate_shortcut(name), add="+")

        content = ttk.Frame(body, style="Workspace.TFrame", padding=(20, 16, 20, 16))
        content.pack(side="left", fill="both", expand=True)
        header = ttk.Frame(content, style="Workspace.TFrame")
        header.pack(fill="x", pady=(0, 12))
        self.page_title = tk.StringVar()
        self.page_subtitle = tk.StringVar()
        ttk.Label(header, text="WILL'S SORTER", style="Eyebrow.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(header, textvariable=self.page_title, style="Title.TLabel").pack(anchor="w")
        subtitle = ttk.Label(header, textvariable=self.page_subtitle, style="Subtitle.TLabel", wraplength=760)
        subtitle.pack(fill="x", pady=(4, 0))
        theme.wrap_label(subtitle)

        stack = ttk.Frame(content, style="Panel.TFrame", padding=1)
        stack.pack(fill="both", expand=True)
        stack.rowconfigure(0, weight=1)
        stack.columnconfigure(0, weight=1)
        self.pages = {}
        for key, _label, _title, _subtitle in self.WORKSPACES:
            page = ttk.Frame(stack, padding=(4, 4, 4, 0))
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()
            self.pages[key] = page
        self.active_workspace = None

    def show_workspace(self, key):
        for name, _label, title, subtitle in self.WORKSPACES:
            if name == key:
                self.page_title.set(title)
                self.page_subtitle.set(subtitle)
                for item, page in self.pages.items():
                    if item != key:
                        page.grid_remove()
                self.pages[key].grid()
                for item, button in self.nav_buttons.items():
                    button.configure(style="NavActive.TButton" if item == key else "Nav.TButton")
                self.active_workspace = key
                if key == "activity":
                    self._refresh_log()
                return

    def _navigate_shortcut(self, key):
        self.show_workspace(key)
        self.nav_buttons[key].focus_set()
        return "break"

    def _toggle_mode(self):
        theme.set_mode(self.root, "dark" if theme.MODE == "light" else "light")
        self.settings["appearance"] = theme.MODE
        self._show_mode()

    def _show_mode(self):
        self.mode_button.configure(text="Switch to light mode" if theme.MODE == "dark" else "Switch to dark mode")

    # ------------------------------ organize ------------------------------

    def _build_organize(self, page):
        self.status = tk.StringVar(value="Ready. Preview first to see what would change.")
        theme.status_bar(page, self.status)

        folder = theme.section(page, "Folder")
        row = ttk.Frame(folder)
        row.pack(fill="x")
        self.folder_text = tk.StringVar()
        ttk.Entry(row, textvariable=self.folder_text, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Change...", command=self._choose_folder).pack(side="left", padx=(theme.GAP, 0))
        ttk.Button(row, text="Use Downloads", command=self._reset_folder).pack(side="left", padx=(theme.GAP, 0))
        ttk.Button(row, text="Open", command=self._open_folder).pack(side="left", padx=(theme.GAP, 0))
        self.rules_hint = theme.hint(folder, "", pady=(theme.GAP, 0))
        self._show_folder()

        actions = ttk.Frame(page, padding=(theme.PAD, theme.PAD, theme.PAD, theme.GAP))
        actions.pack(fill="x")
        self.preview_button = ttk.Button(actions, text="Preview", style="Primary.TButton",
                                         command=lambda: self._start(preview=True))
        self.preview_button.pack(side="left")
        self.run_button = ttk.Button(actions, text="Organize now", command=lambda: self._start(preview=False))
        self.run_button.pack(side="left", padx=(theme.GAP, 0))
        self.stop_button = ttk.Button(actions, text="Stop", style="Danger.TButton", state="disabled",
                                      command=self._cancel.set)
        self.stop_button.pack(side="left", padx=(theme.GAP, 0))
        self.result_title = ttk.Label(actions, text="", style="Hint.TLabel")
        self.result_title.pack(side="right")

        table = ttk.Frame(page, padding=(theme.PAD, 0, theme.PAD, theme.PAD))
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("action", "file", "result"), show="headings", height=8)
        for column, title, width, stretch in (("action", "Action", 110, False), ("file", "File", 300, True),
                                              ("result", "Where it goes", 380, True)):
            self.tree.heading(column, text=title, anchor="w")
            self.tree.column(column, width=width, minwidth=90, stretch=stretch, anchor="w")
        theme.tree_tags(self.tree, sorted="text", duplicate="warning", zipped="success",
                        removed="danger", skipped="muted")
        bar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

    def _show_folder(self):
        self.folder_text.set(str(sorter.target_folder(self.settings)))
        s = self.settings
        how = "sent to the Recycle Bin" if s["use_recycle_bin"] else "deleted permanently"
        self.rules_hint.configure(text=(
            f"Loose files are sorted into category folders. Compressible files older than "
            f"{s['zip_after_days']} days are zipped. Installers and unfinished downloads older than "
            f"{s['delete_after_days']} days are {how}. Subfolders are left alone."))

    def _choose_folder(self):
        chosen = filedialog.askdirectory(parent=self.root, title="Folder to organize",
                                         initialdir=str(sorter.target_folder(self.settings)))
        if chosen:
            self.settings["folder"] = str(Path(chosen))
            self._save_settings_quietly()
            self._show_folder()

    def _reset_folder(self):
        self.settings["folder"] = ""
        self._save_settings_quietly()
        self._show_folder()

    def _open_folder(self):
        folder = sorter.target_folder(self.settings)
        try:
            if sys.platform == "win32":
                os.startfile(folder)   # noqa: S606 - opens Explorer on the user's own folder
            else:
                subprocess.Popen(["open" if theme.MAC else "xdg-open", str(folder)])
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not open the folder.\n\n{error}", parent=self.root)

    def _start(self, preview):
        if self._busy:
            return
        folder = sorter.target_folder(self.settings)
        if not folder.is_dir():
            messagebox.showerror(APP_TITLE, f"This folder does not exist:\n\n{folder}", parent=self.root)
            return
        if not preview:
            how = "the Recycle Bin" if self.settings["use_recycle_bin"] else "permanent deletion"
            if not messagebox.askokcancel(
                    APP_TITLE,
                    f"Organize this folder now?\n\n{folder}\n\nFiles will be moved and renamed, old ones zipped, "
                    f"and old installers sent to {how}. Use Preview first if you want to see the list.",
                    parent=self.root):
                return
        self._busy = True
        self._cancel.clear()
        self.tree.delete(*self.tree.get_children())
        self.result_title.configure(text="Preview: nothing is being changed" if preview else "Organizing...")
        self.status.set("Looking through the folder..." if preview else "Organizing...")
        self._set_running(True)
        labels = PREVIEW_LABELS if preview else ACTION_LABELS
        settings = dict(self.settings)

        def emit(kind, name, detail):
            self.ui.submit(lambda: self._add_row(labels.get(kind, kind), kind, name, detail))

        def work():
            try:
                stats = sorter.organize(folder, settings, preview=preview, emit=emit, cancelled=self._cancel.is_set)
                message, failed = sorter.summary(stats, preview), False
            except Exception as error:   # shown to the user; the window stays usable
                sorter.log(f"FAILED    {error}")
                message, failed = f"Stopped: {error}", True
            self.ui.submit(lambda: self._finish(preview, message, failed))

        threading.Thread(target=work, name="sorter-pass", daemon=True).start()

    def _add_row(self, label, kind, name, detail):
        item = self.tree.insert("", "end", values=(label, name, detail), tags=(kind,))
        self.tree.see(item)

    def _finish(self, preview, message, failed):
        self._busy = False
        self._set_running(False)
        stopped = self._cancel.is_set()
        count = len(self.tree.get_children())
        if failed:
            self.result_title.configure(text="Did not finish")
        elif stopped:
            self.result_title.configure(text="Stopped early")
        elif count == 0:
            self.result_title.configure(text="Nothing to do: the folder is already tidy")
        else:
            self.result_title.configure(text=f"Preview: {count} changes, nothing done yet" if preview
                                        else f"Done: {count} changes")
        self.status.set(("Stopped early. " if stopped and not failed else "") + message[:1].upper() + message[1:])

    def _set_running(self, running):
        self.preview_button.configure(state="disabled" if running else "normal")
        self.run_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    # ------------------------------ settings ------------------------------

    def _build_settings(self, page):
        self.settings_status = tk.StringVar(value="")
        theme.status_bar(page, self.settings_status)

        ages = theme.section(page, "File ages")
        self.zip_days = tk.StringVar(value=str(self.settings["zip_after_days"]))
        self.delete_days = tk.StringVar(value=str(self.settings["delete_after_days"]))
        self.use_bin = tk.BooleanVar(value=self.settings["use_recycle_bin"])
        grid = ttk.Frame(ages)
        grid.pack(fill="x")
        for row, (label, variable, note) in enumerate((
                ("Zip files after", self.zip_days, "days. Only types that shrink: text, CSV, old Office files, BMP/TIFF, PSD, WAV."),
                ("Remove after", self.delete_days, "days. Only installers (.exe, .msi, .iso) and unfinished downloads."))):
            ttk.Label(grid, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(grid, textvariable=variable, width=6, justify="right").grid(row=row, column=1, padx=theme.GAP, pady=4)
            ttk.Label(grid, text=note, style="Hint.TLabel").grid(row=row, column=2, sticky="w", pady=4)
        ttk.Checkbutton(ages, text="Send removed files to the Recycle Bin (recommended)",
                        variable=self.use_bin).pack(anchor="w", pady=(theme.GAP, 0))
        ttk.Button(ages, text="Save settings", style="Primary.TButton",
                   command=self._save_settings).pack(anchor="w", pady=(theme.GAP, 0))

        daily = theme.section(page, "Daily run", pady=(theme.PAD, 0))
        row = ttk.Frame(daily)
        row.pack(fill="x")
        ttk.Label(row, text="Run every day at").pack(side="left")
        self.daily_time = tk.StringVar(value=self.settings["daily_time"])
        ttk.Entry(row, textvariable=self.daily_time, width=7, justify="center").pack(side="left", padx=theme.GAP)
        ttk.Label(row, text="24-hour clock. If the PC is off, it runs at the next start.",
                  style="Hint.TLabel").pack(side="left")
        buttons = ttk.Frame(daily)
        buttons.pack(fill="x", pady=(theme.GAP, 0))
        self.daily_on = ttk.Button(buttons, text="Turn on daily run", command=self._daily_on)
        self.daily_on.pack(side="left")
        self.daily_off = ttk.Button(buttons, text="Turn off", command=self._daily_off)
        self.daily_off.pack(side="left", padx=(theme.GAP, 0))
        self.daily_state = ttk.Label(buttons, text="", style="Hint.TLabel")
        self.daily_state.pack(side="left", padx=(theme.PAD, 0))
        if not sorter.WINDOWS:
            theme.hint(daily, "The daily run uses Windows Task Scheduler, so it can only be turned on from a Windows PC.",
                       pady=(theme.GAP, 0))
            self.daily_on.configure(state="disabled")
            self.daily_off.configure(state="disabled")
        self._show_daily_state()

    def _read_settings_form(self):
        """Returns an error message, or None after copying the form into self.settings."""
        values = {}
        for key, variable, label in (("zip_after_days", self.zip_days, "Zip files after"),
                                     ("delete_after_days", self.delete_days, "Remove after")):
            text = variable.get().strip()
            if not text.isdigit() or not 1 <= int(text) <= 3650:
                return f'"{label}" needs a whole number of days between 1 and 3650.'
            values[key] = int(text)
        if not sorter.valid_time(self.daily_time.get().strip()):
            return "Enter the daily time as HH:MM on a 24-hour clock, for example 12:00."
        self.settings.update(values)
        self.settings["use_recycle_bin"] = bool(self.use_bin.get())
        self.settings["daily_time"] = self.daily_time.get().strip()
        return None

    def _save_settings(self):
        error = self._read_settings_form()
        if error:
            self.settings_status.set(error)
            return False
        if not self._save_settings_quietly():
            return False
        self._show_folder()
        self.settings_status.set("Settings saved. The daily run uses them too.")
        return True

    def _save_settings_quietly(self):
        try:
            sorter.save_settings(self.settings)
            return True
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not save settings.\n\n{error}", parent=self.root)
            return False

    def _show_daily_state(self):
        if sorter.WINDOWS:
            self.daily_state.configure(text="Daily run is ON" if sorter.daily_task_installed() else "Daily run is off")

    def _daily_on(self):
        if not self._save_settings():
            return
        _ok, message = sorter.install_daily_task(self.settings["daily_time"])
        self.settings_status.set(message)
        self._show_daily_state()

    def _daily_off(self):
        _ok, message = sorter.remove_daily_task()
        self.settings_status.set(message)
        self._show_daily_state()

    # ------------------------------ activity ------------------------------

    def _build_activity(self, page):
        bar = ttk.Frame(page, padding=(theme.PAD, theme.GAP, theme.PAD, theme.GAP))
        bar.pack(fill="x")
        ttk.Button(bar, text="Refresh", command=self._refresh_log).pack(side="left")
        ttk.Label(bar, text=str(sorter.LOG_PATH), style="Hint.TLabel").pack(side="left", padx=(theme.PAD, 0))
        holder = ttk.Frame(page, padding=(theme.PAD, 0, theme.PAD, theme.PAD))
        holder.pack(fill="both", expand=True)
        self.log_box = theme.log_pane(holder)

    def _refresh_log(self):
        try:
            text = sorter.LOG_PATH.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        lines = text.splitlines()[-theme.MAX_LOG_LINES:]
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("end", "\n".join(lines) + "\n" if lines else "Nothing yet. Runs and previews are recorded here.\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    # -------------------------------- close --------------------------------

    def _on_close(self):
        if self._busy and not messagebox.askokcancel(
                APP_TITLE, "A pass is still running. Stop it and close?", parent=self.root):
            return
        self._closing = True
        self._cancel.set()
        self.ui.close()
        self.root.destroy()


def _show_fatal_error_dialog(exc_type, exc_value, exc_tb):
    """Tk's callback-exception handler, so errors show even under pythonw."""
    try:
        messagebox.showerror(f"{APP_TITLE} - unexpected error",
                             "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    except Exception:
        pass


def _report_startup_crash():
    error_text = traceback.format_exc()
    log_path = ROOT_DIR / "gui_error.log"
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n{error_text}\n")
    except Exception:
        pass
    try:
        messagebox.showerror(f"{APP_TITLE} - failed to start", f"{error_text}\n\nThis was also saved to {log_path}.")
    except Exception:
        pass


def _set_windows_app_user_model_id():
    """Give the taskbar this app's own icon instead of Python's (Windows only)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("WillsSorter.App")
    except Exception:
        pass


def main():
    _set_windows_app_user_model_id()
    root = tk.Tk()
    try:
        SorterApp(root)
    except Exception:
        _report_startup_crash()
        try:
            root.destroy()
        except Exception:
            pass
        return
    root.report_callback_exception = _show_fatal_error_dialog
    root.mainloop()


if __name__ == "__main__":
    main()
