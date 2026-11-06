@echo off
cd /d "%~dp0"
echo Iniciando PyImageJ Studio...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocorreu um erro ao iniciar. Verifique se o Python e as dependencias estao instalados.
    echo Tentando instalar dependencias...
    python -m pip install -r requirements.txt
    python main.py
    pause
)
