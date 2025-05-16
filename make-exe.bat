@echo off
pyinstaller --noconsole --icon=icons\app.ico --onefile panel.py 
pause

move /y dist\panel.exe .\panel.exe
pause