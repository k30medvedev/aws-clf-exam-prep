@echo off
echo [1/3] Creating virtual environment...
python -m venv env

echo [2/3] Activating virtual environment...
call env\Scripts\activate

echo [3/3] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo All dependencies installed. You can now start the app using start.bat
pause
