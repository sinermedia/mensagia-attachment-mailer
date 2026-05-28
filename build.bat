@echo off
echo ================================================
echo  Building Mensagia Attachment Mailer (.exe)
echo ================================================

:: Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)

:: Install/update dependencies
echo Installing dependencies...
pip install -r requirements-dev.txt -q

:: Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist mensagia-mailer-gui.spec del mensagia-mailer-gui.spec
if exist mensagia-mailer-console.spec del mensagia-mailer-console.spec

:: Build GUI executable
echo.
echo Building GUI version...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "mensagia-mailer-gui" ^
    --icon NONE ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --collect-all customtkinter ^
    main_gui.py

if errorlevel 1 (
    echo ERROR: GUI build failed.
    pause
    exit /b 1
)

:: Build console executable
echo.
echo Building console version...
pyinstaller ^
    --onefile ^
    --console ^
    --name "mensagia-mailer-console" ^
    main.py

if errorlevel 1 (
    echo ERROR: Console build failed.
    pause
    exit /b 1
)

echo.
echo ================================================
echo  Build complete!
echo  Files in: dist\
echo    mensagia-mailer-gui.exe     (graphical mode)
echo    mensagia-mailer-console.exe (console mode)
echo.
echo  IMPORTANT: Place a .env file next to the .exe
echo  with your API token:
echo    MENSAGIA_API_TOKEN=your_token_here
echo ================================================
pause
