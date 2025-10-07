#!/bin/bash

echo "--- Activating virtual environment ---"
source .venv/bin/activate

echo "--- Starting VTS Voice Controller ---"
python vts_main.py

echo
echo "--- Program finished. Press any key to exit ---"
read -n 1 -s -r -p ""
