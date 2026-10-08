@echo off
chcp 65001 >nul
title Instalar Basetoque Studio
echo.
echo  Instalando lo necesario para Basetoque Studio...
echo  (puede pedirte permiso; acepta). Tarda unos minutos.
echo.
where py >nul 2>nul || winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
where ffmpeg >nul 2>nul || winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
echo.
echo  Instalando el asistente de Claude (opcional)...
py -3 -m pip install --upgrade anthropic
echo.
echo  Listo. CIERRA esta ventana y abre "Abrir Basetoque.bat".
echo  (Si dice que falta FFmpeg, reinicia la computadora una vez.)
echo.
pause
