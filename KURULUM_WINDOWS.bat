@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls
echo ===============================================
echo         PIDECI - ILK KURULUM
echo ===============================================
where py >nul 2>nul
if errorlevel 1 (
 echo Python bulunamadi. Python 3.11 veya yenisini kurun.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 echo [1/3] Sanal ortam kuruluyor...
 py -m venv .venv
 if errorlevel 1 goto :error
)
echo [2/3] Gereksinimler yukleniyor...
REM Avoid blocked SQLAlchemy native extension modules on Windows App Control PCs.
set DISABLE_SQLALCHEMY_CEXT=1
".venv\Scripts\python.exe" -m pip install --no-binary SQLAlchemy -r requirements.txt
if errorlevel 1 goto :error
echo.
echo [3/3] Yonetici hesabi olusturuluyor...
echo Kullanici adi: admin
echo En az 12 karakter uzunlugunda bir sifre secin.
".venv\Scripts\python.exe" -m app.cli create-admin
if errorlevel 1 goto :error
echo.
echo Kurulum tamamlandi. BASLAT_WINDOWS.bat dosyasini calistirin.
pause
exit /b 0
:error
echo.
echo Kurulumda bir sorun olustu. Yukaridaki hatayi kontrol edin.
pause
exit /b 1
