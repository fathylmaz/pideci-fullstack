@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Once KURULUM_WINDOWS.bat dosyasini calistirin.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" scripts\backup_database.py
pause
