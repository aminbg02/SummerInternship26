@echo off
REM Double-click this to shut down the whole Orange RAG platform.
REM It runs stop.ps1 (backend -> frontend -> database containers). Data is kept.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
echo.
pause
