# Will's Sorter

Keeps the Windows Downloads folder tidy. Uses the PowerShell built into Windows 10/11, so there is nothing to install.

Each run it:

1. **Sorts** loose files into category folders (Documents, Images, Videos, Installers, ...) and cleans up file names. Exact duplicates go to the Recycle Bin.
2. **Zips** compressible files older than 60 days into monthly archives in `<Category>\Zipped\`.
3. **Cleans** installers and abandoned partial downloads older than 90 days (sent to the Recycle Bin).

## Use

Double-click one of:

- `1 - Preview (changes nothing).bat` - list what would happen
- `2 - Run Now.bat` - run once
- `3 - Install Daily Auto-Run.bat` - run every day at noon
- `Uninstall Auto-Run.bat` - stop the daily run

## Settings

Day counts, run time and file-type lists are at the top of `DownloadsOrganizer.ps1`. Re-run the install launcher after changing them. The activity log is at `%LOCALAPPDATA%\DownloadsOrganizer\log.txt`.
