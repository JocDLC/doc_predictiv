@echo off
rem ============================================================
rem  Documentador Predictivo - Renault GBS Colombia
rem  Doble clic en este archivo para arrancar todo.
rem ============================================================
setlocal
set "BASE=%~dp0"
set "APP=%BASE%app"
set "BOTDIR=%APP%\automation_salesforce"
set "PY_EXE=%BASE%python\python.exe"
set "PY_ARGS="

rem --- 1) Python: portatil del paquete > sistema > instalar ---
rem El paquete incluye Python y Selenium: no requiere instalacion manual.
if exist "%PY_EXE%" goto :python_ready

python --version 2>nul | findstr /b "Python" >nul && (
  set "PY_EXE=python"
  goto :python_ready
)
py -3 --version 2>nul | findstr /b "Python" >nul && (
  set "PY_EXE=py"
  set "PY_ARGS=-3"
  goto :python_ready
)

echo No se encontro Python. Intentando instalar Python 3.12 automaticamente...
winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
py -3 --version 2>nul | findstr /b "Python" >nul && (
  set "PY_EXE=py"
  set "PY_ARGS=-3"
  goto :python_ready
)
echo.
echo ERROR: no hay Python disponible y la instalacion automatica fallo.
echo Extrae nuevamente el ZIP completo o pedile a soporte instalar Python 3.12.
echo.
pause
exit /b 1

:python_ready
if not exist "%BOTDIR%\ui_server.py" (
  echo.
  echo ERROR: falta app\automation_salesforce.
  echo Extrae el ZIP completo antes de ejecutar este archivo.
  echo.
  pause
  exit /b 1
)

rem --- 2) Selenium es indispensable para el bot ---
"%PY_EXE%" %PY_ARGS% -c "import selenium" >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Python encontro una instalacion sin Selenium.
  echo Volve a extraer el ZIP completo y ejecuta INICIAR.bat desde esa carpeta.
  echo No ejecutes 'python ui_server.py' manualmente.
  echo.
  pause
  exit /b 1
)

if not exist "%BOTDIR%\logs" mkdir "%BOTDIR%\logs"
cd /d "%BOTDIR%"

rem --- 3) Servidor local de la app via guardian (minimizado, NO cerrar) ---
rem El guardian reinicia ui_server.py si se cae o deja de responder.
start "Bot Predictivo - Servidor" /min "%PY_EXE%" %PY_ARGS% server_guardian.py > "logs\guardian.log" 2>&1

rem --- 4) Verificar servidor y abrir navegador + app ---
echo Esperando al servidor del bot...
set "OK="
for /l %%i in (1,1,60) do (
  if not defined OK (
    curl -s -o nul http://127.0.0.1:8765/status 2>nul && set "OK=1"
    if not defined OK timeout /t 1 /nobreak >nul
  )
)
if not defined OK (
  echo.
  echo ERROR: el servidor del bot no respondio.
  echo Revisa el detalle en: %BOTDIR%\logs\ui_server.log
  echo.
  pause
  exit /b 1
)

rem Abre en el Edge dedicado del bot: pestaña Salesforce (login/2FA) + la app.
"%PY_EXE%" %PY_ARGS% open_persistent_browser.py > "logs\navegador.log" 2>&1
echo.
echo Listo. En la ventana de Edge: pestaña de Salesforce para iniciar sesion
echo (usuario + 2FA, solo la primera vez) y pestaña con la aplicacion.
echo No cierres las ventanas minimizadas mientras usas la app.
timeout /t 5 >nul
endlocal
