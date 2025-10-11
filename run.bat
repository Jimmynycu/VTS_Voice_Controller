@echo off

echo "--- Activating virtual environment and launching application in new window... ---"

:: Use start to open a new command prompt window.
:: The /k flag keeps the new window open after the script finishes.
start "VTS Voice Controller Log" cmd /k "call .\.venv\Scripts\activate.bat && python vts_main.py"