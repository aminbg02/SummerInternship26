@echo off
REM Double-click to START the platform.
REM
REM Docker engine -> database containers (Postgres, Qdrant, pgAdmin) -> Flask
REM backend -> Angular frontend, then opens each one in the browser as it answers.
REM
REM Safe to run twice: anything already up is left alone. The very first run also
REM creates the Python virtualenv and installs backend + frontend dependencies,
REM which takes a few minutes.
REM
REM   start.bat              start everything, open the browser tabs
REM   start.bat -NoBrowser   start everything, open nothing
REM
REM Shut it all down again with:  end.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
echo.
echo (This window can be closed. The backend and frontend run in their own windows.)
pause
