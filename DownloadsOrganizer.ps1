<#
Downloads Organizer for Windows  (works with the PowerShell built into Windows 10/11)

What it does each time it runs:
  1. SORT    - moves loose files in Downloads into category folders
               (Documents, Images, Videos, ...) and tidies up their names.
  2. ZIP     - files that compress well (text, spreadsheets, bitmaps, PSDs, WAVs ...)
               and are older than $ZipAfterDays go into a monthly zip inside
               <Category>\Zipped\.
  3. CLEAN   - installers and abandoned partial downloads older than
               $DeleteAfterDays are sent to the Recycle Bin.

Usage (or just double-click the .bat files):
  DownloadsOrganizer.ps1 -Preview     show what would happen, change nothing
  DownloadsOrganizer.ps1              run once now
  DownloadsOrganizer.ps1 -Install     run automatically every day
  DownloadsOrganizer.ps1 -Uninstall   stop running automatically
#>
[CmdletBinding()]
param(
    [string]$Path,
    [switch]$Preview,
    [switch]$Install,
    [switch]$Uninstall
)

# ============================== SETTINGS ==============================
# After changing anything here, run Install.bat again to update the daily task.

$ZipAfterDays    = 60     # zip compressible files once they are this old
$DeleteAfterDays = 90     # recycle installers / partial downloads once this old
$UseRecycleBin   = $true  # $false = delete permanently instead
$DailyRunTime    = '12:00'  # 24h clock; if the PC is off it runs at next start
$MinAgeMinutes   = 10     # leave very recent files alone (may still be downloading)
$ZipMaxFileMB    = 500    # don't zip single files bigger than this

$Categories = [ordered]@{
    'Documents'     = 'pdf','doc','docx','odt','rtf','txt','md','pages','epub','mobi'
    'Spreadsheets'  = 'xls','xlsx','xlsm','csv','tsv','ods','numbers'
    'Presentations' = 'ppt','pptx','key','odp'
    'Images'        = 'jpg','jpeg','png','gif','webp','heic','bmp','tif','tiff','svg','ico','raw','cr2','nef','dng'
    'Videos'        = 'mp4','mov','mkv','avi','wmv','webm','m4v','flv'
    'Audio'         = 'mp3','wav','flac','m4a','aac','ogg','wma','aiff'
    'Design'        = 'psd','psb','ai','indd','eps','fig','sketch','xd','afdesign','afphoto'
    'Fonts'         = 'ttf','otf','woff','woff2'
    'Code and Data' = 'json','xml','html','htm','css','js','ts','py','ps1','sql','yaml','yml','log','ics','vcf'
    'Archives'      = 'zip','rar','7z','tar','gz','bz2','xz','tgz'
    'Installers'    = 'exe','msi','msix','appx','iso','dmg','pkg','apk'
}
$OtherCategory = 'Other'

# File types worth zipping (already-compressed types like jpg/mp4/docx/pdf gain nothing)
$Compressible = 'doc','rtf','txt','md','xls','csv','tsv','json','xml','html','htm','css','js','ts',
                'py','sql','yaml','yml','log','bmp','tif','tiff','svg','psd','psb','ai','eps',
                'wav','aiff','raw','cr2','nef','dng','ppt','ttf','otf'

# Categories whose old files are considered useless and get removed
$DeleteCategories = @('Installers')

# Unfinished downloads; left alone until old, then removed
$PartialExtensions = 'crdownload','part','partial','download','tmp','opdownload'

# ============================ END SETTINGS ============================

$ErrorActionPreference = 'Stop'
$TaskName   = 'Downloads Organizer'
$OnWindows  = ($PSVersionTable.PSEdition -ne 'Core') -or $IsWindows

if ($env:LOCALAPPDATA) { $AppDir = Join-Path $env:LOCALAPPDATA 'DownloadsOrganizer' }
else                   { $AppDir = $PSScriptRoot }
$LogFile = Join-Path $AppDir 'log.txt'

function Write-Log([string]$Message) {
    if ($Preview) { $Message = "[preview] $Message" }
    Write-Host $Message
    try {
        if (-not (Test-Path -LiteralPath $AppDir)) { New-Item -ItemType Directory -Path $AppDir -Force | Out-Null }
        if ((Test-Path -LiteralPath $LogFile) -and ((Get-Item -LiteralPath $LogFile).Length -gt 1MB)) {
            Remove-Item -LiteralPath $LogFile -Force
        }
        Add-Content -LiteralPath $LogFile -Value ("{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message)
    } catch { }
}

function Format-Size([long]$Bytes) {
    if ($Bytes -ge 1GB) { return ('{0:N1} GB' -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ('{0:N1} MB' -f ($Bytes / 1MB)) }
    return ('{0:N0} KB' -f ($Bytes / 1KB))
}

# ---------------------------- install / uninstall ----------------------------

if ($Install) {
    if (-not (Test-Path -LiteralPath $AppDir)) { New-Item -ItemType Directory -Path $AppDir -Force | Out-Null }
    $installed = Join-Path $AppDir 'DownloadsOrganizer.ps1'
    if ($PSCommandPath -ne $installed) { Copy-Item -LiteralPath $PSCommandPath -Destination $installed -Force }

    $arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $installed
    $action    = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
    $trigger   = New-ScheduledTaskTrigger -Daily -At $DailyRunTime
    $settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Description 'Sorts, zips and cleans the Downloads folder.' -Force | Out-Null

    Write-Host "Installed. Downloads will be organized every day at $DailyRunTime."
    Write-Host "Script copied to: $installed"
    Write-Host "Activity log:     $LogFile"
    return
}

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host 'Daily task removed. Your files and folders were not touched.'
    } else {
        Write-Host 'Daily task was not installed.'
    }
    return
}

# --------------------------------- helpers ---------------------------------

function Get-DownloadsPath {
    if ($OnWindows) {
        try {
            $p = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path
            if ($p -and (Test-Path -LiteralPath $p)) { return $p }
        } catch { }
    }
    return (Join-Path $HOME 'Downloads')
}

$ExtToCategory = @{}
foreach ($cat in $Categories.Keys) {
    foreach ($e in $Categories[$cat]) { $ExtToCategory[$e] = $cat }
}

function Get-Ext($File) { return $File.Extension.TrimStart('.').ToLowerInvariant() }

function Get-Category($File) {
    $e = Get-Ext $File
    if ($ExtToCategory.ContainsKey($e)) { return $ExtToCategory[$e] }
    return $OtherCategory
}

# "Q3_report%20final (1)" -> "Q3 report final"
function Get-CleanName([string]$BaseName) {
    $n = $BaseName
    try { $n = [uri]::UnescapeDataString($n) } catch { }
    $n = $n -replace '[\\/:*?"<>|]', '-'
    $n = $n -replace '_+', ' '
    $n = $n -replace '(?<=\w)\++(?=\w)', ' '
    $n = $n -replace '\s*\(\d{1,2}\)\s*$', ''
    $n = $n -replace '\s*-\s*Copy(\s*\(\d+\))?\s*$', ''
    $n = $n -replace '\s{2,}', ' '
    $n = $n.Trim(' ', '.', '-')
    if ([string]::IsNullOrWhiteSpace($n)) { return $BaseName }
    return $n
}

# Age counts from whichever is later: created or last modified.
function Get-FileDate($File) {
    if ($File.CreationTime -gt $File.LastWriteTime) { return $File.CreationTime }
    return $File.LastWriteTime
}
function Get-AgeDays($File) { return ((Get-Date) - (Get-FileDate $File)).TotalDays }

function Get-UniquePath([string]$Dir, [string]$Base, [string]$ExtWithDot) {
    $candidate = Join-Path $Dir ($Base + $ExtWithDot)
    $i = 2
    while (Test-Path -LiteralPath $candidate) {
        $candidate = Join-Path $Dir ("{0} ({1}){2}" -f $Base, $i, $ExtWithDot)
        $i++
    }
    return $candidate
}

function Test-SameContent([string]$A, [string]$B) {
    if ((Get-Item -LiteralPath $A).Length -ne (Get-Item -LiteralPath $B).Length) { return $false }
    return ((Get-FileHash -LiteralPath $A -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $B -Algorithm SHA256).Hash)
}

function Remove-Safely([string]$FilePath) {
    if ($UseRecycleBin -and $OnWindows) {
        Add-Type -AssemblyName Microsoft.VisualBasic
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($FilePath, 'OnlyErrorDialogs', 'SendToRecycleBin')
    } else {
        Remove-Item -LiteralPath $FilePath -Force
    }
}

# --------------------------------- main ---------------------------------

if ($Path) { $Root = $Path } else { $Root = Get-DownloadsPath }
if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
    Write-Log "Downloads folder not found: $Root"
    exit 1
}
$Root = (Resolve-Path -LiteralPath $Root).Path
Write-Log "=== Organizing $Root ==="

$stats = @{ Moved = 0; Dupes = 0; Zipped = 0; ZipSaved = [long]0; Deleted = 0; DeletedBytes = [long]0; Errors = 0 }
$recentCutoff = (Get-Date).AddMinutes(-$MinAgeMinutes)
$pending = @{}   # preview only: files that would have been moved into each category

function Get-CategoryFiles([string]$Category) {
    $list = @()
    $dir = Join-Path $Root $Category
    if (Test-Path -LiteralPath $dir) { $list += @(Get-ChildItem -LiteralPath $dir -File) }
    if ($pending.ContainsKey($Category)) { $list += $pending[$Category] }
    return $list
}

# ---- 1. SORT ----
foreach ($file in @(Get-ChildItem -LiteralPath $Root -File)) {
    try {
        if ($PartialExtensions -contains (Get-Ext $file)) { continue }
        if ($file.LastWriteTime -gt $recentCutoff)        { continue }

        $category = Get-Category $file
        $destDir  = Join-Path $Root $category
        $clean    = Get-CleanName $file.BaseName
        $target   = Join-Path $destDir ($clean + $file.Extension)

        if (Test-Path -LiteralPath $target) {
            if (Test-SameContent $file.FullName $target) {
                Write-Log "Duplicate removed: $($file.Name)  (same as $category\$($clean + $file.Extension))"
                if (-not $Preview) { Remove-Safely $file.FullName }
                $stats.Dupes++
                continue
            }
            $target = Get-UniquePath $destDir $clean $file.Extension
        }

        Write-Log "Sorted: $($file.Name)  ->  $category\$(Split-Path $target -Leaf)"
        if ($Preview) {
            if (-not $pending.ContainsKey($category)) { $pending[$category] = @() }
            $pending[$category] += $file
        } else {
            if (-not (Test-Path -LiteralPath $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
            Move-Item -LiteralPath $file.FullName -Destination $target
        }
        $stats.Moved++
    } catch {
        $stats.Errors++
        Write-Log "Skipped $($file.Name): $($_.Exception.Message)"
    }
}

# ---- 2. ZIP ----
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$zipCategories = @($Categories.Keys) + $OtherCategory | Where-Object { ($DeleteCategories -notcontains $_) -and ($_ -ne 'Archives') }
foreach ($category in $zipCategories) {
    $catDir = Join-Path $Root $category
    $old = @(Get-CategoryFiles $category | Where-Object {
        ($Compressible -contains (Get-Ext $_)) -and
        ((Get-AgeDays $_) -ge $ZipAfterDays) -and
        ($_.Length -le ($ZipMaxFileMB * 1MB))
    })
    if ($old.Count -eq 0) { continue }

    foreach ($group in ($old | Group-Object { (Get-FileDate $_).ToString('yyyy-MM') })) {
        $zipDir  = Join-Path $catDir 'Zipped'
        $zipPath = Join-Path $zipDir ("{0} {1}.zip" -f $category, $group.Name)

        if ($Preview) {
            foreach ($f in $group.Group) { Write-Log "Would zip: $category\$($f.Name)  ->  $category\Zipped\$(Split-Path $zipPath -Leaf)" }
            $stats.Zipped += $group.Count
            continue
        }

        try {
            if (-not (Test-Path -LiteralPath $zipDir)) { New-Item -ItemType Directory -Path $zipDir -Force | Out-Null }
            $before = 0
            if (Test-Path -LiteralPath $zipPath) { $before = (Get-Item -LiteralPath $zipPath).Length }

            # add files
            $added = @{}   # entry name -> source file
            $zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Update)
            try {
                $names = @{}
                foreach ($entry in $zip.Entries) { $names[$entry.FullName.ToLowerInvariant()] = $true }
                foreach ($f in $group.Group) {
                    $entryName = $f.Name
                    $i = 2
                    while ($names.ContainsKey($entryName.ToLowerInvariant())) {
                        $entryName = "{0} ({1}){2}" -f $f.BaseName, $i, $f.Extension
                        $i++
                    }
                    try {
                        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                            $zip, $f.FullName, $entryName, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
                        $names[$entryName.ToLowerInvariant()] = $true
                        $added[$entryName] = $f
                    } catch {
                        $stats.Errors++
                        Write-Log "Could not zip $($f.Name): $($_.Exception.Message)"
                    }
                }
            } finally { $zip.Dispose() }

            # verify every file really is in the zip before removing the original
            $verified = @{}
            $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
            try {
                foreach ($entry in $zip.Entries) { $verified[$entry.FullName] = $entry.Length }
            } finally { $zip.Dispose() }

            $originalBytes = [long]0
            foreach ($entryName in $added.Keys) {
                $f = $added[$entryName]
                if ($verified.ContainsKey($entryName) -and ($verified[$entryName] -eq $f.Length)) {
                    $originalBytes += $f.Length
                    Remove-Item -LiteralPath $f.FullName -Force
                    Write-Log "Zipped: $category\$($f.Name)  ->  $category\Zipped\$(Split-Path $zipPath -Leaf)"
                    $stats.Zipped++
                } else {
                    $stats.Errors++
                    Write-Log "Zip check failed, kept original: $category\$($f.Name)"
                }
            }
            $growth = (Get-Item -LiteralPath $zipPath).Length - $before
            $stats.ZipSaved += ($originalBytes - $growth)
        } catch {
            $stats.Errors++
            Write-Log "Zip problem in $category ($($group.Name)): $($_.Exception.Message)"
        }
    }
}

# ---- 3. CLEAN ----
$stale = @()
foreach ($category in $DeleteCategories) {
    $stale += @(Get-CategoryFiles $category)
}
$stale += @(Get-ChildItem -LiteralPath $Root -File | Where-Object { $PartialExtensions -contains (Get-Ext $_) })

foreach ($file in $stale) {
    if ((Get-AgeDays $file) -lt $DeleteAfterDays) { continue }
    try {
        $size = $file.Length
        Write-Log ("Removed ({0:N0} days old, {1}): {2}" -f (Get-AgeDays $file), (Format-Size $size), $file.Name)
        if (-not $Preview) { Remove-Safely $file.FullName }
        $stats.Deleted++
        $stats.DeletedBytes += $size
    } catch {
        $stats.Errors++
        Write-Log "Could not remove $($file.Name): $($_.Exception.Message)"
    }
}

Write-Log ("Done: {0} sorted, {1} duplicates removed, {2} zipped (saved {3}), {4} old files removed ({5}), {6} problems." -f `
    $stats.Moved, $stats.Dupes, $stats.Zipped, (Format-Size $stats.ZipSaved), $stats.Deleted, (Format-Size $stats.DeletedBytes), $stats.Errors)
