@echo off
rem Archive the 5-min output JSONs into json_output\archive\<date>, one folder per day (nothing is deleted).
rem Logic is in archive_json.py. optvwap.json and the ASGBOOM state files are kept in place.
cd /d "%~dp0"
tg-flask-venv\Scripts\python archive_json.py
pause
