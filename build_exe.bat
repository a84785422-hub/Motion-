@echo off
setlocal
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean video_motion_control.spec
echo.
echo Executable genere dans dist\VideoMotionControl\VideoMotionControl.exe
pause
