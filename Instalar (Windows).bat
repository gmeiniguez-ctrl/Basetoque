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
echo  Creando el acceso directo en el Escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Basetoque Studio.lnk')); $s.TargetPath='%~dp0Abrir Basetoque.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%SystemRoot%\System32\shell32.dll,115'; $s.Save()"
echo.
echo  ===========================================================
echo   LISTO. Reinicia la computadora una vez y despues abre
echo   "Basetoque Studio" desde tu Escritorio.
echo   (No borres ni muevas esta carpeta: el acceso directo la usa.)
echo  ===========================================================
echo.
pause
