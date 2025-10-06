@echo off
ECHO "--- Activating virtual environment ---"
CALL .\.venv\Scripts\activate.bat

ECHO "--- Starting VTS Voice Controller ---"
python vts_main.py

ECHO "--- Program finished. Press any key to exit ---"
pause
