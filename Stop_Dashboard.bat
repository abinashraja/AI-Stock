@echo off
title Stop Dashboard
echo Stopping the AI Stock Dashboard...
taskkill /F /IM python.exe /T
echo Dashboard successfully stopped.
pause
