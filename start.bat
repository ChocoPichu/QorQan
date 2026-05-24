@echo off
echo Starting QorQan Bot System...
start "Dashboard Server" cmd /k python dashboard.py
start "Telegram Bot" cmd /k python main.py
echo Both processes are starting in separate windows.
echo Keep this window open or press any key to close this launcher.
pause