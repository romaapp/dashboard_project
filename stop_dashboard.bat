@echo off
echo Останавливаю дашборд...
powershell.exe -ExecutionPolicy Bypass -File "C:\dashboard_project\stop_dashboard.ps1"
pause