@echo off
rem ============================================================
rem  Documentador Predictivo - Verificacion de PC
rem  Doble clic: revisa Edge, politicas, Selenium y conexion,
rem  y deja reporte_verificacion_pc.txt en el Escritorio.
rem ============================================================
cd /d "%~dp0"
setlocal
set "PY_EXE=python"
if exist "%~dp0python\python.exe" set "PY_EXE=%~dp0python\python.exe"
"%PY_EXE%" app\automation_salesforce\verificar_pc.py
echo.
echo El reporte quedo guardado como reporte_verificacion_pc.txt en el Escritorio.
echo.
pause
endlocal
