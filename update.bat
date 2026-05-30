@echo off
echo ========================================
echo  Actualizando requirements.txt
echo ========================================
call venv\Scripts\activate
pip freeze > requirements.txt
echo.
echo requirements.txt actualizado correctamente
echo.
pause