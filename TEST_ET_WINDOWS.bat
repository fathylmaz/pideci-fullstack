@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Once uygulamayi kurun.
  exit /b 1
)
echo Test gereksinimleri kontrol ediliyor...
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || exit /b 1
".venv\Scripts\python.exe" -m pytest -q || exit /b 1
echo API testleri basarili.
where node >nul 2>&1
if %errorlevel%==0 (
  node --check web\js\site.js || exit /b 1
  node --check web\js\admin.js || exit /b 1
) else (
  echo Node.js yok; JavaScript soz dizimi kontrolu atlandi.
)
