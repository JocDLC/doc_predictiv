@echo off
rem ============================================================
rem  Documentador Predictivo - Recolector de diagnostico
rem  Doble clic: genera diagnostico_bot.zip junto a este archivo
rem  con lo que soporte necesita para revisar el bot.
rem ============================================================
setlocal
set "BASE=%~dp0app\automation_salesforce"
set "WORK=%TEMP%\diag_bot"
set "OUT=%~dp0diagnostico_bot.zip"

if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"

copy /y "%BASE%\ui_output\monitor_state.json" "%WORK%\" >nul 2>&1
copy /y "%BASE%\logs\ui_server.log" "%WORK%\" >nul 2>&1
copy /y "%BASE%\config.json" "%WORK%\" >nul 2>&1
copy /y "%BASE%\logs\navegador.log" "%WORK%\" >nul 2>&1
copy /y "%BASE%\logs\guardian.log" "%WORK%\" >nul 2>&1
copy /y "%USERPROFILE%\Desktop\reporte_verificacion_pc.txt" "%WORK%\" >nul 2>&1
copy /y "%~dp0reporte_verificacion_pc.txt" "%WORK%\" >nul 2>&1

powershell -NoProfile -Command "Compress-Archive -Path '%WORK%\*' -DestinationPath '%OUT%' -Force"

if exist "%OUT%" (
  echo.
  echo Listo: se creo  diagnostico_bot.zip
  echo Enviale ese archivo a soporte.
) else (
  echo.
  echo ERROR: no se pudo crear el diagnostico. Avisa a soporte.
)
echo.
pause
endlocal
