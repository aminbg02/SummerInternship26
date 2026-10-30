@echo off
REM Double-click this to start the whole Orange RAG platform.
REM It just runs start.ps1 (Docker -> databases -> Flask -> Angular), then
REM opens pgAdmin, Qdrant, the API health check and the app in your browser.
REM Pass -NoBrowser through if you'd rather no tabs opened:  run.bat -NoBrowser
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
echo.
echo (This launcher window can be closed. The backend and frontend run in their own windows.)
pause
