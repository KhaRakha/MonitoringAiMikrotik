' ==============================================================================
' MikroTik AI Agent Automation - Silent Background Launcher
' Runs the bot completely in the background without any visible command prompt
' ==============================================================================
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
ProjectDir = FSO.GetParentFolderName(ScriptDir)
WshShell.CurrentDirectory = ProjectDir

PythonExe = "C:\Users\LENOVO\AppData\Local\Programs\Python\Python314\python.exe"
If Not FSO.FileExists(PythonExe) Then
    PythonExe = WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
End If
If Not FSO.FileExists(PythonExe) Then
    PythonExe = "python.exe"
End If

Cmd = """" & PythonExe & """ """ & ScriptDir & "\watchdog.py"""

' 0 = Hide window completely, False = Do not wait for return
WshShell.Run Cmd, 0, False
Set WshShell = Nothing
Set FSO = Nothing
