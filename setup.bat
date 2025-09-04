@echo off
REM ServiceNow Documentation Vectorizer - Setup Script for Windows

echo ==========================================
echo ServiceNow Documentation Vectorizer Setup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org
    pause
    exit /b 1
)

echo Python detected
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Dependencies installed
echo.

REM Run environment setup
echo Setting up environment configuration...
if not exist ".env" (
    python setup_env.py
) else (
    echo .env file already exists. Run 'python setup_env.py' to reconfigure.
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Activate virtual environment: venv\Scripts\activate
echo 2. Verify setup: python test_setup.py
echo 3. Index documentation: python index_docs.py
echo 4. Test queries: python query_docs.py --interactive
echo 5. Start MCP server: python mcp_server.py
echo.
pause
