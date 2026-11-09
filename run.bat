@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || exit /b 1
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt || exit /b 1
) else (
  call .venv\Scripts\activate.bat
)
python main.py %*
