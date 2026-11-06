@echo off
echo ===================================================
echo     Compilando PyImageJ Studio para Executavel (.exe)
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
echo 2. Executando PyInstaller...
pyinstaller --noconsole --onefile ^
    --name "PyImageJ-Studio" ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "scipy.spatial.distance" ^
    --hidden-import "skimage.filters" ^
    --hidden-import "skimage.measure" ^
    --hidden-import "skimage.segmentation" ^
    --clean main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha durante o empacotamento com PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ===================================================
echo   SUCESSO! Executavel gerado na pasta:
echo   %~dp0dist\PyImageJ-Studio.exe
echo ===================================================
echo.
pause
