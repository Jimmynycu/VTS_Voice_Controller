@echo off

echo "--- Activating virtual environment ---"
call .\.venv\Scripts\activate.bat

echo "--- Starting VTS Voice Controller ---"
python vts_main.py

echo.
echo "--- Program finished. Press any key to exit ---"
pause
