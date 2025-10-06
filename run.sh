#!/bin/bash
echo "--- Activating virtual environment ---"
source .venv/bin/activate

echo "--- Starting VTS Voice Controller ---"
python vts_main.py

echo "--- Program finished ---"
