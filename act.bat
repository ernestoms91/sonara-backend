@echo off
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo Entorno virtual activado: venv
) else (
    if exist "env\Scripts\activate.bat" (
        call env\Scripts\activate.bat
        echo Entorno virtual activado: env
    ) else (
        echo No se encontro el entorno virtual (venv o env)
    )
)