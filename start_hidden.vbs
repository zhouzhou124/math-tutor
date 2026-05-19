' Math Tutor - Silent Launcher
' Double-click this file. Zero windows. Browser opens when ready.
' If something goes wrong, double-click run.bat to see error messages.

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Step 1: Kill orphan processes on port 8501 (hidden, wait for completion)
WshShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -ano ^| findstr "":8501.*LISTENING""') do taskkill /F /PID %a >nul 2>&1", 0, True

' Step 2: Start Streamlit with pythonw.exe (no console window, non-blocking)
WshShell.Run "cmd /c cd /d " & Chr(34) & ScriptDir & Chr(34) & " && pythonw -m streamlit run app.py --server.headless true", 0, False

' Step 3: Wait for server to initialize, then open browser silently
WScript.Sleep 6000
WshShell.Run "http://localhost:8501", 1, False
