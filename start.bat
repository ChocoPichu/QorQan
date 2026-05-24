@echo off
echo Starting QorQan Bot System...
start "Dashboard Server" cmd /k python -m src.dashboard.app
start "Telegram Bot" cmd /k python -m src.bot.main
echo Both processes are starting in separate windows.
echo Keep this window open or press any key to close this launcher.
pause