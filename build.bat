@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ==============================================
echo   Ecoa - compilacao (PyInstaller)
echo   Uso: build.bat          (um unico .exe)
echo        build.bat onedir   (pasta com .exe, abre mais rapido)
echo ==============================================

where py >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado. Instale o Python 3.10+ em python.org e marque "Add python.exe to PATH".
  exit /b 1
)

if not exist .venv (
  echo Criando ambiente virtual...
  py -3 -m venv .venv || goto :err
)
call .venv\Scripts\activate.bat || goto :err

echo Instalando dependencias...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt -r requirements-build.txt || goto :err

if not exist assets\icon.ico (
  echo Gerando icone...
  python tools\make_icon.py || goto :err
)

set MODE=--onefile
if /I "%~1"=="onedir" set MODE=--onedir

echo Compilando...
pyinstaller --noconfirm --clean --windowed %MODE% --name Ecoa --icon assets\icon.ico ^
  --collect-all customtkinter --hidden-import pystray._win32 main.py || goto :err

echo.
echo Pronto! Resultado em: dist\
if /I "%~1"=="onedir" (echo Execute: dist\Ecoa\Ecoa.exe) else (echo Execute: dist\Ecoa.exe)
exit /b 0

:err
echo.
echo [ERRO] A compilacao falhou. Veja as mensagens acima.
exit /b 1
