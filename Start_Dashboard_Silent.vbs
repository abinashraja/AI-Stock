Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c cd /d ""d:\Agent"" && streamlit run dashboard.py", 0, False
