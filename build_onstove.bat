@echo off
echo Building Onstove Open Script
call venv\Scripts\activate.bat
pip install playwright pyinstaller
playwright install chromium
pyinstaller -y --onefile --name "Onstove_Open" onstove_open.py
echo Build complete!
