# Will's Sorter

Keeps the Windows Downloads folder tidy, with a desktop window in the same style as Partners Toolbox.

Each pass it:

1. **Sorts** loose files into category folders (Documents, Images, Videos, Installers, ...) and cleans up file names. Exact duplicates are removed.
2. **Zips** compressible files older than 60 days into monthly archives in `<Category>\Zipped\`. An original is removed only after its copy in the zip is checked.
3. **Cleans** installers and unfinished downloads older than 90 days (sent to the Recycle Bin).

Subfolders already in Downloads are left alone.

## Run

Needs Python 3.9 or newer from python.org (tick "Add python.exe to PATH"). No other packages.

- `Launch (silent).vbs` - open the window
- `Launch (with console).bat` - open it with a console, to see errors
- `Create Desktop Shortcut.vbs` - run once to put a Will's Sorter icon on the Desktop (run again if you move this folder)

In the window:

- **Organize** - Preview lists what a pass would do without changing anything; Organize now does it.
- **Settings** - day counts, Recycle Bin on/off, and the daily background run (Windows Task Scheduler, no admin rights needed).
- **Activity log** - everything it has done, including daily runs.

Without the window: `python src\sorter.py --preview` or `python src\sorter.py --run`.

## Files

- `src/sorter.py` - all file operations, the daily task, and the command line
- `src/app.py` - the window
- `src/theme.py`, `src/ui_runtime.py` - styles and thread helper shared with Partners Toolbox
- `settings.json`, `logs/` - created on first use, not committed

File-type lists are at the top of `src/sorter.py`.
