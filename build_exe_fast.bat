@echo off
echo ===================================================
echo   Compilando PyImageJ Studio (Modo Diretorio Rapido)
echo   (Abre em menos de 1 segundo - Sem descompactacao)
echo ===================================================
echo.

cd /d "%~dp0"

echo 1. Verificando dependencias...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao instalar dependencias via pip.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo 2. Executando PyInstaller (--onedir)...
pyinstaller --noconsole --onedir ^
    --icon "icon.ico" ^
    --name "PyImageJ-Studio" ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --add-data "icon.png;." ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "scipy.spatial.distance" ^
    --hidden-import "skimage.filters" ^
    --hidden-import "skimage.measure" ^
    --hidden-import "skimage.segmentation" ^
    --exclude-module "matplotlib" ^
    --exclude-module "tkinter" ^
    --exclude-module "PySide6.QtQml" ^
    --exclude-module "PySide6.QtQuick" ^
    --exclude-module "PySide6.QtWebEngineCore" ^
    --exclude-module "PySide6.Qt3DCore" ^
    --exclude-module "PySide6.QtBluetooth" ^
    --exclude-module "PySide6.QtSensors" ^
    --exclude-module "PySide6.QtMultimedia" ^
    --exclude-module "PySide6.QtPdf" ^
    --exclude-module "PySide6.QtSql" ^
    --clean main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha durante o empacotamento com PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ===================================================
echo   SUCESSO! Pasta com executavel ultra-rapido gerada em:
echo   %~dp0dist\PyImageJ-Studio\PyImageJ-Studio.exe
echo ===================================================
echo.
pause
