@echo off
setlocal
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onefile --name MotionControlAI --collect-all mediapipe app/main.py
echo.
echo Executable genere : dist\MotionControlAI.exe
pause
