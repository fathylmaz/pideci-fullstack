@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Once KURULUM_WINDOWS.bat dosyasini calistirin.
 pause
 exit /b 1
)
echo.
echo PIDECI - WEB SUNUCUSU
echo ----------------------------------------------
echo Musteri sitesi:   http://127.0.0.1:8000
echo Yonetim paneli:   http://127.0.0.1:8000/admin
echo Durdurmak icin CTRL + C
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
