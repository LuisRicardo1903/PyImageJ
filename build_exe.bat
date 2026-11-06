@echo off
echo ===================================================
echo     Compilando PyImageJ Studio para Executavel (.exe)
echo          (Modo Otimizado - Sem Modulos Pesados)
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
echo 2. Executando PyInstaller com exclusao de modulos desnecessarios...
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
    --exclude-module "matplotlib" ^
    --exclude-module "tkinter" ^
    --exclude-module "PySide6.QtQml" ^
    --exclude-module "PySide6.QtQuick" ^
    --exclude-module "PySide6.QtQuickWidgets" ^
    --exclude-module "PySide6.QtWebEngineCore" ^
    --exclude-module "PySide6.QtWebEngineWidgets" ^
    --exclude-module "PySide6.Qt3DCore" ^
    --exclude-module "PySide6.Qt3DRender" ^
    --exclude-module "PySide6.QtBluetooth" ^
    --exclude-module "PySide6.QtSensors" ^
    --exclude-module "PySide6.QtPositioning" ^
    --exclude-module "PySide6.QtMultimedia" ^
    --exclude-module "PySide6.QtMultimediaWidgets" ^
    --exclude-module "PySide6.QtNfc" ^
    --exclude-module "PySide6.QtPdf" ^
    --exclude-module "PySide6.QtPdfWidgets" ^
    --exclude-module "PySide6.QtSpatialAudio" ^
    --exclude-module "PySide6.QtDesigner" ^
    --exclude-module "PySide6.QtHelp" ^
    --exclude-module "PySide6.QtTest" ^
    --exclude-module "PySide6.QtSql" ^
    --exclude-module "PySide6.QtNetwork" ^
    --clean main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha durante o empacotamento com PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo 3. Copiando executavel para a pasta principal...
copy /y "dist\PyImageJ-Studio.exe" "PyImageJ-Studio.exe"

echo.
echo ===================================================
echo   SUCESSO! Executavel otimizado gerado:
echo   - Na pasta principal: %~dp0PyImageJ-Studio.exe
echo   - E na pasta dist:    %~dp0dist\PyImageJ-Studio.exe
echo ===================================================
echo.
pause
