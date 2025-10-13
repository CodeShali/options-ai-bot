#!/bin/bash

# Quick Start Script for Options Trading AI Bot
# This script helps you set up and run the trading system

set -e

echo "============================================================"
echo "Options Trading AI Bot - Quick Start"
echo "============================================================"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Check if Python 3.9+
required_version="3.9"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.9 or higher is required"
    exit 1
fi
echo "✅ Python version OK"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs
echo "✅ Directories created"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚙️  Setting up environment variables..."
    cp .env.example .env
    echo "✅ .env file created from template"
    echo ""
    echo "⚠️  IMPORTANT: You need to edit .env with your API keys!"
    echo ""
    echo "Required credentials:"
    echo "  1. Alpaca API keys (get from https://alpaca.markets)"
    echo "  2. Discord bot token (get from https://discord.com/developers)"
    echo "  3. Discord channel ID"
    echo "  4. OpenAI API key (get from https://platform.openai.com)"
    echo ""
    read -p "Press Enter to open .env file for editing..."
    
    # Try to open with default editor
    if command -v nano &> /dev/null; then
        nano .env
    elif command -v vim &> /dev/null; then
        vim .env
    elif command -v code &> /dev/null; then
        code .env
    else
        echo "Please edit .env manually with your credentials"
    fi
else
    echo "✅ .env file already exists"
fi
echo ""

# Test connections
echo "🧪 Testing API connections..."
echo ""
python scripts/test_connection.py
test_result=$?
echo ""

if [ $test_result -eq 0 ]; then
    echo "============================================================"
    echo "✅ Setup Complete!"
    echo "============================================================"
    echo ""
    echo "Your trading system is ready to run!"
    echo ""
    echo "Next steps:"
    echo "  1. Review your configuration in .env"
    echo "  2. Start the system: python main.py"
    echo "  3. Test Discord commands in your server"
    echo "  4. Monitor logs: tail -f logs/trading.log"
    echo ""
    echo "Useful commands:"
    echo "  - View positions: python scripts/view_positions.py"
    echo "  - Manual trade: python scripts/manual_trade.py AAPL"
    echo "  - API docs: http://localhost:8000/docs (when running)"
    echo ""
    echo "⚠️  Remember: System starts in PAPER trading mode"
    echo "   Test thoroughly before switching to live trading!"
    echo ""
    read -p "Start the trading system now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Starting trading system..."
        echo ""
        python main.py
    fi
else
    echo "============================================================"
    echo "⚠️  Setup Complete with Warnings"
    echo "============================================================"
    echo ""
    echo "Some API connection tests failed."
    echo "Please review the errors above and fix your .env file."
    echo ""
    echo "Common issues:"
    echo "  - Incorrect API keys"
    echo "  - Missing credentials in .env"
    echo "  - No internet connection"
    echo ""
    echo "After fixing, run: python scripts/test_connection.py"
fi

echo ""
echo "============================================================"
echo "For help, see:"
echo "  - README.md - Main documentation"
echo "  - SETUP_GUIDE.md - Detailed setup instructions"
echo "  - PROJECT_OVERVIEW.md - System architecture"
echo "============================================================"
