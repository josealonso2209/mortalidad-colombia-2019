@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Instala Python 3.12 desde python.org y vuelve a ejecutar este archivo.
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo No se pudieron instalar las dependencias. Revisa tu conexion.
  pause
  exit /b 1
)
start "Dashboard" http://127.0.0.1:8050
.venv\Scripts\python.exe estadistica.py
pause
