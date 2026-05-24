@echo off
echo Starting QorQan Bot System...

if exist ".venv\Scripts\python.exe" (
    start "Dashboard Server" cmd /k ".venv\Scripts\python.exe -m src.dashboard.app"
    start "Telegram Bot" cmd /k ".venv\Scripts\python.exe -m src.bot.main"
) else (
    start "Dashboard Server" cmd /k python -m src.dashboard.app
    start "Telegram Bot" cmd /k python -m src.bot.main
)

echo Both processes are starting in separate windows.
pause