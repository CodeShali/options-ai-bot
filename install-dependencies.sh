#!/bin/bash
# TARA Trading Bot - Install Dependencies Only
# Run this in your already-cloned repository

set -e  # Exit on error

echo "🌟 TARA Trading Bot - Dependency Installation"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: main.py not found!${NC}"
    echo "Please run this script from the options-ai-bot directory"
    echo ""
    echo "Example:"
    echo "  cd ~/trading/options-ai-bot"
    echo "  bash install-dependencies.sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found main.py - in correct directory"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    libopenblas-dev \
    python3-dev \
    build-essential \
    htop

echo -e "${GREEN}✓${NC} System dependencies installed"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version)
echo "🐍 Python version: $PYTHON_VERSION"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${YELLOW}⚠${NC}  Virtual environment already exists, skipping creation"
fi
echo ""

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
echo "⏱️  This may take 10-15 minutes on Raspberry Pi, please be patient..."
echo ""

pip install -r requirements.txt

echo ""
echo -e "${GREEN}✓${NC} Python dependencies installed"
echo ""

# Setup environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Setting up environment configuration..."
    cp .env.example .env
    
    echo ""
    echo "📝 Please configure your .env file with API keys:"
    echo "   nano .env"
    echo ""
    echo "Required keys:"
    echo "  - ALPACA_API_KEY"
    echo "  - ALPACA_SECRET_KEY"
    echo "  - DISCORD_BOT_TOKEN"
    echo "  - DISCORD_CHANNEL_ID"
    echo "  - OPENAI_API_KEY"
    echo ""
    
    read -p "Would you like to edit .env now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        nano .env
    fi
else
    echo -e "${YELLOW}⚠${NC}  .env file already exists, skipping configuration"
fi
echo ""

# Test run
echo "🧪 Testing TARA..."
echo "Starting test run (will stop after 5 seconds)..."
echo ""

timeout 5 python main.py || true

echo ""
echo -e "${GREEN}✓${NC} Test run complete"
echo ""

# Summary
echo "=============================================="
echo "🎉 Installation Complete!"
echo "=============================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure .env file (if not done):"
echo "   nano .env"
echo ""
echo "2. Start TARA:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "3. Or set up auto-start (optional):"
echo "   bash setup-autostart.sh"
echo ""
echo "💡 To activate virtual environment in future:"
echo "   source venv/bin/activate"
echo ""
echo "🚀 Ready to trade!"
echo ""
