' Starts Will's Sorter with no console window.
' If nothing appears, run "Launch (with console).bat" once to see the error.
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir
WshShell.Run "pythonw.exe " & Chr(34) & scriptDir & "\src\app.py" & Chr(34), 0, False
