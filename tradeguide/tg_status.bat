@echo off
rem Quick tradeguide status (read-only). Examples:
rem   tg_status.bat               short summary
rem   tg_status.bat --all         summary + OI + sectors + option VWAP
rem   tg_status.bat --oi          OI table only
rem   tg_status.bat --date 2026-10-08 --time 11:30
cd /d "%~dp0"
tg-flask-venv\Scripts\python tg_status.py %*
pause
