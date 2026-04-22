@echo off
REM Windows 本機打包腳本
REM 使用前請先建立虛擬環境：python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --onedir --windowed --name "xFRAME808" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build failed. Make sure you have activated the virtual environment and installed dependencies.
    exit /b %ERRORLEVEL%
)

echo.
echo Build complete. Output: dist\xFRAME808\xFRAME808.exe
echo.
echo To share, zip the entire dist\xFRAME808\ folder:
echo   powershell Compress-Archive -Path dist/xFRAME808/* -DestinationPath xFRAME808-Windows.zip
echo.
echo To build a Setup.exe installer (requires Inno Setup 6):
echo   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=3.1.0 scripts\installer.iss
