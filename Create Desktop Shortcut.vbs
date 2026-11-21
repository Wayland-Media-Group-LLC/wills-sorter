' Double-click this ONCE to put a "Will's Sorter" icon on your Desktop.
' It opens the app with no console window and uses assets\app_icon.ico.
'
' Safe to run again later -- it just overwrites the same shortcut, e.g.
' after moving this folder somewhere else.
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")
desktopDir = WshShell.SpecialFolders("Desktop")

Set link = WshShell.CreateShortcut(desktopDir & "\Will's Sorter.lnk")
link.TargetPath = scriptDir & "\Launch (silent).vbs"
link.IconLocation = scriptDir & "\assets\app_icon.ico"
link.WorkingDirectory = scriptDir
link.Description = "Will's Sorter (Downloads organizer)"
link.Save

MsgBox "Created a 'Will's Sorter' icon on your Desktop." & vbCrLf & vbCrLf & _
    "If you move this folder, run this file again so the icon points at " & _
    "the new place.", vbInformation, "Done"
