"""Shared desktop styles, adapted from Partners Toolbox so the apps look alike."""
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

PAD = 16
GAP = 8
MAC = sys.platform == "darwin"
LOG_FONT = ("Consolas", 9) if sys.platform == "win32" else ("Menlo", 9) if MAC else ("TkFixedFont", 9)
# Keyboard shortcuts use Command on a Mac and Ctrl elsewhere.
SHORTCUT_KEY = "Command" if MAC else "Control"
SHORTCUT_LABEL = "\u2318" if MAC else "Ctrl +"
PALETTES = {
    "light": {
        "surface": "#edf2f3", "field": "#ffffff", "text": "#182f36",
        "muted": "#526b73", "border": "#d6e2e5", "accent": "#087f83",
        "accent_hover": "#05666a", "selection": "#e1f3f2", "danger": "#b42339",
        "success": "#18734c", "warning": "#94560c", "disabled": "#6c7f85",
        "sidebar": "#142b32", "sidebar_hover": "#203f47", "sidebar_selected": "#27535b",
        "sidebar_text": "#f4fafb", "sidebar_muted": "#b7cdd2", "heading": "#f4f8f9",
        "on_accent": "#ffffff", "danger_border": "#efd5db", "danger_active": "#fff0f2",
    },
    # Every text/background pair the styles use meets WCAG AA (4.5:1) here.
    "dark": {
        "surface": "#0e181b", "field": "#152327", "text": "#e2edef",
        "muted": "#9fb5bb", "border": "#2b4147", "accent": "#3cc2bf",
        "accent_hover": "#62d3d0", "selection": "#1c3a3e", "danger": "#ff8b98",
        "success": "#6ad9a2", "warning": "#f2b866", "disabled": "#73898f",
        "sidebar": "#091114", "sidebar_hover": "#15252a", "sidebar_selected": "#1f3b41",
        "sidebar_text": "#eff7f8", "sidebar_muted": "#98aeb4", "heading": "#1a2b30",
        "on_accent": "#04282a", "danger_border": "#5b2d36", "danger_active": "#3b1e25",
    },
}
MODE = "light"
COLORS = dict(PALETTES[MODE])   # the active palette; set_mode() updates it in place
MAX_LOG_LINES = 5000
# The styles Tk's clam theme (ttk/clamTheme.tcl) gives settings to.
_CLAM_STYLES = (".", "ComboboxPopdownFrame", "Heading", "Sash", "TButton", "TCheckbutton", "TCombobox",
                "TEntry", "TLabelframe", "TMenubutton", "TNotebook.Tab", "TProgressbar", "TRadiobutton",
                "TSpinbox", "Toolbutton", "Treeview")
# Colors of classic Tk widgets that set_mode() moves to the new palette.
_COLOR_OPTIONS = ("background", "foreground", "activebackground", "activeforeground",
                  "highlightbackground", "highlightcolor", "insertbackground", "selectbackground",
                  "selectforeground", "disabledforeground", "troughcolor", "selectcolor")


def _dark_config(c):
    """Colors clam leaves pale or black: bevels, arrows, check marks, cursors."""
    return {
        ".": {"bordercolor": c["border"], "lightcolor": c["field"], "darkcolor": c["field"], "troughcolor": c["heading"]},
        "TEntry": {"insertcolor": c["text"]},
        "TCombobox": {"arrowcolor": c["text"], "insertcolor": c["text"]},
        "TCheckbutton": {"indicatorbackground": c["field"], "indicatorforeground": c["text"]},
        "Vertical.TScrollbar": {"arrowcolor": c["text"]},
        "Horizontal.TScrollbar": {"arrowcolor": c["text"]},
    }


def _dark_maps(c):
    """State colors (disabled, pressed, focus...) that clam fixes to light grays."""
    return {
        ".": {"background": [("disabled", c["surface"]), ("active", c["selection"])],
              "foreground": [("disabled", c["disabled"])],
              "selectbackground": [("!focus", c["border"])], "selectforeground": [("!focus", c["text"])]},
        "TButton": {"lightcolor": [("pressed", c["border"])], "darkcolor": [("pressed", c["border"])]},
        "TCheckbutton": {"indicatorbackground": [("pressed", c["selection"]), ("!disabled", "alternate", c["accent"]),
                                                 ("disabled", "alternate", c["disabled"]), ("disabled", c["surface"])]},
        "TEntry": {"lightcolor": [("focus", c["accent"])], "darkcolor": [("focus", c["accent"])],
                   "background": [("readonly", c["surface"])]},
        "TCombobox": {"background": [("active", c["selection"]), ("pressed", c["selection"])],
                      "arrowcolor": [("disabled", c["disabled"])]},
        "TNotebook.Tab": {"lightcolor": [("selected", c["selection"]), ("!selected", c["field"])]},
        # A scrollbar with nothing to scroll is drawn "disabled".
        "Vertical.TScrollbar": {"background": [("disabled", c["border"])], "arrowcolor": [("disabled", c["disabled"])]},
        "Horizontal.TScrollbar": {"background": [("disabled", c["border"])], "arrowcolor": [("disabled", c["disabled"])]},
    }


def saved_mode():
    """The light/dark choice saved by the sidebar switch ("light" if none)."""
    try:
        import sorter
        mode = sorter.load_settings().get("appearance")
    except Exception:
        return "light"
    return mode if mode in PALETTES else "light"


def apply(root):
    """Apply once per Tk root, including when a new window replaces an old one."""
    root = root.winfo_toplevel()
    if getattr(root, "_partners_theme_applied", False):
        return
    global MODE
    MODE = saved_mode()
    COLORS.update(PALETTES[MODE])
    if MAC:
        # Tk on a Mac sizes fonts at 72 dpi, so the point sizes below (chosen
        # on Windows at 96 dpi) would come out a quarter smaller.
        root.tk.call("tk", "scaling", 96 / 72)
    style = ttk.Style(root)
    base = tkfont.nametofont("TkDefaultFont", root=root)
    base.configure(size=10)
    if sys.platform == "win32":
        base.configure(family="Segoe UI")
    family, size = base.cget("family"), base.cget("size")
    for name in ("TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name, root=root).configure(family=family, size=size)
        except tk.TclError:
            pass
    if "clam" in style.theme_names():
        # One ttk theme per mode: switching selects the other theme, so light
        # mode is never left with a dark setting. A new theme takes only clam's
        # elements and layouts, so copy clam's own style settings in first.
        style.theme_use("clam")
        clam = {name: (style.configure(name) or {}, style.map(name)) for name in _CLAM_STYLES}
        for mode, palette in PALETTES.items():
            name = f"sorter-{mode}"
            if name not in style.theme_names():
                style.theme_create(name, parent="clam")
            style.theme_use(name)
            for styled, (options, maps) in clam.items():
                if options:
                    style.configure(styled, **options)
                if maps:
                    style.map(styled, **maps)
            _configure_theme(style, palette, mode == "dark", family, size)
        style.theme_use(f"sorter-{MODE}")
    else:
        _configure_theme(style, COLORS, MODE == "dark", family, size)
    _configure_root(root)
    root._partners_theme_applied = True


def _configure_root(root):
    c = COLORS
    root.configure(background=c["surface"])
    # Defaults for classic Tk widgets created later without their own colors
    # (dialogs, plain Text boxes, combobox drop-down lists).
    for pattern, value in (("*Toplevel.background", c["surface"]), ("*Text.background", c["field"]),
                           ("*Text.foreground", c["text"]), ("*Text.insertBackground", c["text"]),
                           ("*Listbox.background", c["field"]), ("*Listbox.foreground", c["text"]),
                           ("*Listbox.selectBackground", c["selection"]),
                           ("*Listbox.selectForeground", c["text"])):
        root.option_add(pattern, value)


def _configure_theme(style, c, dark, family, size):
    style.configure(".", background=c["field"], foreground=c["text"], font=(family, size))
    if dark:
        # Clam's own bevels, arrows and state colors are light grays and black.
        for name, options in _dark_config(c).items():
            style.configure(name, **options)
        for name, options in _dark_maps(c).items():
            style.map(name, **options)
    style.configure("TFrame", background=c["field"])
    style.configure("TLabel", background=c["field"], foreground=c["text"])
    style.configure("Workspace.TFrame", background=c["surface"])
    style.configure("Panel.TFrame", background=c["field"], bordercolor=c["border"], relief="solid", borderwidth=1)
    style.configure("TButton", padding=(12, 7), background=c["field"], bordercolor=c["border"],
                    foreground=c["text"], relief="flat", focusthickness=2, focuscolor=c["accent"])
    style.map("TButton", background=[("disabled", c["surface"]), ("pressed", c["border"]), ("active", c["selection"])],
              foreground=[("disabled", c["disabled"])])
    style.configure("Primary.TButton", background=c["accent"], foreground=c["on_accent"],
                    font=(family, size, "bold"), bordercolor=c["accent"])
    style.map("Primary.TButton", background=[("disabled", c["border"]), ("pressed", c["accent_hover"]),
                                              ("active", c["accent_hover"])],
              foreground=[("disabled", c["muted"]), ("!disabled", c["on_accent"])])
    style.configure("Danger.TButton", foreground=c["danger"], bordercolor=c["danger_border"])
    style.map("Danger.TButton", foreground=[("disabled", c["disabled"]), ("!disabled", c["danger"])],
              background=[("disabled", c["surface"]), ("active", c["danger_active"])])
    style.configure("TEntry", padding=7, fieldbackground=c["field"], bordercolor=c["border"], relief="flat")
    style.map("TEntry", bordercolor=[("focus", c["accent"])])
    style.configure("TCombobox", padding=6, fieldbackground=c["field"], bordercolor=c["border"], arrowsize=14)
    style.map("TCombobox", fieldbackground=[("readonly", c["field"]), ("disabled", c["surface"])],
              foreground=[("disabled", c["disabled"])])
    style.configure("TCheckbutton", padding=(0, 4), background=c["field"])
    style.map("TCheckbutton", background=[("active", c["field"])], foreground=[("disabled", c["disabled"])])
    style.configure("TNotebook", borderwidth=0, background=c["field"], tabmargins=(0, 0, 0, 6))
    style.configure("TNotebook.Tab", padding=(16, 9), background=c["field"], foreground=c["muted"],
                    font=(family, size, "bold"), borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", c["selection"]), ("active", c["heading"])],
              foreground=[("selected", c["accent"])])
    style.configure("TLabelframe", padding=(PAD, GAP, PAD, PAD), background=c["field"],
                    bordercolor=c["border"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", font=(family, size, "bold"), foreground=c["text"])
    style.configure("Treeview", rowheight=30, background=c["field"], fieldbackground=c["field"],
                    foreground=c["text"], bordercolor=c["border"], borderwidth=0, relief="flat")
    style.map("Treeview", background=[("selected", c["selection"])], foreground=[("selected", c["text"])])
    style.configure("Treeview.Heading", padding=(12, 9), background=c["heading"],
                    foreground=c["muted"], font=(family, size, "bold"), relief="flat")
    style.configure("Vertical.TScrollbar", background=c["border"], troughcolor=c["heading"],
                    borderwidth=0, arrowsize=12, gripcount=0)
    style.configure("Horizontal.TScrollbar", background=c["border"], troughcolor=c["heading"],
                    borderwidth=0, arrowsize=12, gripcount=0)
    style.configure("Hint.TLabel", foreground=c["muted"])
    style.configure("Warning.TLabel", foreground=c["danger"])
    style.configure("Target.TLabel", foreground=c["muted"])
    style.configure("Title.TLabel", font=(family, 21, "bold"), background=c["surface"])
    style.configure("Subtitle.TLabel", foreground=c["muted"], background=c["surface"])
    style.configure("Eyebrow.TLabel", font=(family, 8, "bold"), foreground=c["muted"], background=c["surface"])
    style.configure("Section.TLabel", font=(family, 11, "bold"), foreground=c["text"])
    style.configure("Compact.TButton", padding=(9, 4), foreground=c["muted"])
    style.configure("Status.TLabel", anchor="w", padding=(PAD, 9), background=c["heading"], foreground=c["muted"])
    style.configure("Sidebar.TFrame", background=c["sidebar"])
    style.configure("Brand.TLabel", background=c["sidebar"], foreground=c["sidebar_text"], font=(family, 15, "bold"))
    style.configure("SidebarHint.TLabel", background=c["sidebar"], foreground=c["sidebar_muted"], font=(family, 9))
    style.configure("SidebarHeading.TLabel", background=c["sidebar"], foreground=c["sidebar_muted"], font=(family, 8, "bold"))
    style.configure("BrandMark.TLabel", background=c["accent"], foreground=c["on_accent"], font=(family, 12, "bold"),
                    padding=(10, 8), anchor="center")
    for name, selected in (("Nav.TButton", False), ("NavActive.TButton", True)):
        style.configure(name, background=c["sidebar_selected"] if selected else c["sidebar"],
                        foreground=c["sidebar_text"] if selected else c["sidebar_muted"],
                        bordercolor=c["sidebar_selected"] if selected else c["sidebar"],
                        padding=(16, 12), anchor="w", relief="flat", font=(family, 10, "bold"),
                        focusthickness=2, focuscolor=c["accent"])
        style.map(name, background=[("active", c["sidebar_hover"]), ("pressed", c["sidebar_selected"])],
                  foreground=[("active", c["sidebar_text"])])


def set_mode(root, mode):
    """Switch every open window between "light" and "dark" right away, and
    remember the choice for the next start."""
    global MODE
    if mode not in PALETTES or mode == MODE:
        return
    root = root.winfo_toplevel()
    old = dict(COLORS)
    MODE = mode
    COLORS.update(PALETTES[mode])
    style = ttk.Style(root)
    if f"sorter-{mode}" in style.theme_names():
        style.theme_use(f"sorter-{mode}")
    else:
        base = tkfont.nametofont("TkDefaultFont", root=root)
        _configure_theme(style, COLORS, mode == "dark", base.cget("family"), base.cget("size"))
    _configure_root(root)
    # Classic Tk widgets hold their colors themselves: move each palette color
    # to its counterpart (first key wins where two keys share a color).
    counterpart = {}
    for key, value in old.items():
        counterpart.setdefault(value.lower(), COLORS[key])
    _recolor(root, counterpart)
    try:
        import sorter
        settings = sorter.load_settings()
        settings["appearance"] = mode
        sorter.save_settings(settings)
    except Exception:
        pass   # a preference that can't be saved never blocks the switch


def _recolor(widget, counterpart):
    if isinstance(widget, ttk.Treeview):
        tree_tags(widget, **getattr(widget, "_partners_tags", {}))
    elif not isinstance(widget, ttk.Widget):
        for option in _COLOR_OPTIONS:
            try:
                value = str(widget.cget(option)).lower()
            except (tk.TclError, ValueError):
                continue
            if value in counterpart:
                widget.configure(**{option: counterpart[value]})
        if widget.winfo_class() == "Listbox":   # combobox drop-downs keep Tk's own colors
            widget.configure(background=COLORS["field"], foreground=COLORS["text"],
                             selectbackground=COLORS["selection"], selectforeground=COLORS["text"])
    for child in widget.winfo_children():
        _recolor(child, counterpart)


def set_icon(root, ico_path):
    """Use `ico_path` as the window icon: the .ico on Windows, else the PNG
    beside it (on a Mac this is also the Dock icon). Cosmetic, never raises."""
    try:
        if sys.platform == "win32":
            if ico_path.exists():
                root.iconbitmap(default=str(ico_path))
            return
        png = ico_path.with_suffix(".png")
        if png.exists():
            image = tk.PhotoImage(master=root, file=str(png))
            root.iconphoto(True, image)
            root._partners_icon = image   # Tk drops an image nothing references
    except Exception:
        pass


def bind_quit(root, on_quit):
    """Route the Mac's Command-Q / Quit menu item through the window's own
    close handler, so jobs and browsers shut down as they do on Windows."""
    if MAC:
        try:
            root.createcommand("tk::mac::Quit", on_quit)
        except tk.TclError:
            pass


def section(parent, title, **pack_kwargs):
    frame = ttk.LabelFrame(parent, text=title)
    kwargs = {"fill": "x", "padx": PAD, "pady": (GAP, 0)}
    kwargs.update(pack_kwargs)
    frame.pack(**kwargs)
    return frame


def status_bar(parent, textvariable):
    bar = ttk.Label(parent, textvariable=textvariable, style="Status.TLabel")
    bar.pack(side="bottom", fill="x")
    return bar


def wrap_label(label):
    """Follow the allocated width, so long help and account text cannot widen panes."""
    last = [None]

    def _rewrap(event):
        # Re-applying an unchanged wraplength makes Tk on a Mac re-lay-out the
        # label and send another <Configure>, which loops forever and freezes
        # the window before it is drawn. Only act when the width really changed.
        wrap = max(1, event.width - 4)
        if wrap != last[0]:
            last[0] = wrap
            label.configure(wraplength=wrap)

    label.bind("<Configure>", _rewrap, add="+")
    return label


def hint(parent, text, **pack_kwargs):
    label = ttk.Label(parent, text=text, style="Hint.TLabel", wraplength=420, justify="left")
    label.pack(**({"anchor": "w", "fill": "x"} | pack_kwargs))
    return wrap_label(label)


def warning(parent, text, **pack_kwargs):
    label = ttk.Label(parent, text=text, style="Warning.TLabel", wraplength=420, justify="left")
    label.pack(**({"anchor": "w", "fill": "x", "pady": (2, 2)} | pack_kwargs))
    return wrap_label(label)


def log_pane(parent):
    # A themed scrollbar: Tk's classic one is the system's native control on
    # Windows and Mac and can't follow dark mode.
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    box = tk.Text(frame, state="disabled", wrap="word", font=LOG_FONT,
                  relief="flat", borderwidth=0, padx=12, pady=10,
                  background=COLORS["field"], foreground=COLORS["text"],
                  highlightthickness=1, highlightbackground=COLORS["border"],
                  insertbackground=COLORS["text"])
    bar = ttk.Scrollbar(frame, orient="vertical", command=box.yview)
    box.configure(yscrollcommand=bar.set)
    bar.pack(side="right", fill="y")
    box.pack(side="left", fill="both", expand=True)
    return box


def text_input(parent, **kwargs):
    """A normal Tk text editor, styled consistently with entries."""
    options = dict(wrap="word", undo=True, font=("Segoe UI", 10) if sys.platform == "win32" else "TkDefaultFont",
                   relief="flat", borderwidth=0, padx=12, pady=10, highlightthickness=1,
                   background=COLORS["field"], foreground=COLORS["text"],
                   highlightbackground=COLORS["border"], highlightcolor=COLORS["accent"],
                   selectbackground=COLORS["selection"], selectforeground=COLORS["text"],
                   insertbackground=COLORS["text"])
    options.update(kwargs)
    return tk.Text(parent, **options)


def append_log(box, text):
    """Bound the on-screen history; callers retain their existing full disk logs."""
    at_bottom = box.yview()[1] >= 0.99
    box.configure(state="normal")
    try:
        box.insert("end", text)
        # Tk's final empty line is not part of the displayed history.
        lines = int(box.index("end-1c").split(".")[0])
        if lines > MAX_LOG_LINES:
            box.delete("1.0", f"{lines - MAX_LOG_LINES + 1}.0")
        if at_bottom:
            box.see("end")
    finally:
        box.configure(state="disabled")


def tree_tags(tree, **tags):
    tree._partners_tags = tags   # re-applied by set_mode()
    for tag, color in tags.items():
        tree.tag_configure(tag, foreground=COLORS[color])
