@echo off
REM Quick Start Script for Options Trading AI Bot (Windows)

echo ============================================================
echo Options Trading AI Bot - Quick Start
echo ============================================================
echo.

REM Check Python
echo Checking Python version...
python --version
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.9 or higher.
    pause
    exit /b 1
)
echo Python OK
echo.

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo Dependencies installed
echo.

REM Create directories
echo Creating directories...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo Directories created
echo.

REM Check for .env file
if not exist ".env" (
    echo Setting up environment variables...
    copy .env.example .env
    echo .env file created from template
    echo.
    echo WARNING: You need to edit .env with your API keys!
    echo.
    echo Required credentials:
    echo   1. Alpaca API keys (get from https://alpaca.markets)
    echo   2. Discord bot token (get from https://discord.com/developers)
    echo   3. Discord channel ID
    echo   4. OpenAI API key (get from https://platform.openai.com)
    echo.
    echo Opening .env file for editing...
    notepad .env
) else (
    echo .env file already exists
)
echo.

REM Test connections
echo Testing API connections...
echo.
python scripts\test_connection.py
echo.

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Your trading system is ready to run!
echo.
echo Next steps:
echo   1. Review your configuration in .env
echo   2. Start the system: python main.py
echo   3. Test Discord commands in your server
echo   4. Monitor logs in logs\trading.log
echo.
echo Useful commands:
echo   - View positions: python scripts\view_positions.py
echo   - Manual trade: python scripts\manual_trade.py AAPL
echo   - API docs: http://localhost:8000/docs (when running)
echo.
echo WARNING: System starts in PAPER trading mode
echo          Test thoroughly before switching to live trading!
echo.

set /p start="Start the trading system now? (y/n): "
if /i "%start%"=="y" (
    echo.
    echo Starting trading system...
    echo.
    python main.py
)

echo.
echo ============================================================
echo For help, see:
echo   - README.md - Main documentation
echo   - SETUP_GUIDE.md - Detailed setup instructions
echo   - PROJECT_OVERVIEW.md - System architecture
echo ============================================================
echo.
pause
