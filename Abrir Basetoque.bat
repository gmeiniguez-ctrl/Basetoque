@echo off
chcp 65001 >nul
title Basetoque Studio
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 app\server.py
  goto fin
)
where python >nul 2>nul
if %errorlevel%==0 (
  python app\server.py
  goto fin
)
echo.
echo  No encontre Python en esta computadora.
echo  Haz doble clic en "Instalar (Windows).bat" primero.
echo.
:fin
pause
