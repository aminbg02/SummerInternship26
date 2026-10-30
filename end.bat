@echo off
REM Double-click to END the platform: Flask backend -> Angular frontend -> containers.
REM
REM YOUR DATA IS KEPT. The containers are stopped, not removed, so companies,
REM users, conversations and knowledge bases all survive — start.bat brings the
REM whole thing back exactly as it was.
REM
REM Docker Desktop itself is left running; quit it from the tray icon if you want
REM its memory back too.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
echo.
pause
