#!/bin/bash
# TARA Trading Bot - Raspberry Pi Setup Script
# Run this on your Raspberry Pi 4

set -e  # Exit on error

echo "🌟 TARA Trading Bot - Raspberry Pi Setup"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} Running on: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown device')"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install dependencies
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

# Create directory
INSTALL_DIR="$HOME/trading"
echo "📁 Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Clone repository (or update if exists)
if [ -d "options-AI-BOT" ]; then
    echo "📥 Updating existing repository..."
    cd options-AI-BOT
    git pull
else
    echo "📥 Cloning repository..."
    echo "Enter your GitHub repository URL:"
    read -r REPO_URL
    git clone "$REPO_URL" options-AI-BOT
    cd options-AI-BOT
fi

echo -e "${GREEN}✓${NC} Repository ready"
echo ""

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies (this may take 5-10 minutes)..."
pip install -r requirements.txt

echo -e "${GREEN}✓${NC} Python dependencies installed"
echo ""

# Setup environment file
if [ ! -f .env ]; then
    echo "⚙️  Setting up environment configuration..."
    cp .env.example .env
    
    echo ""
    echo "Please enter your API keys:"
    echo ""
    
    read -p "Alpaca API Key: " ALPACA_KEY
    read -p "Alpaca Secret Key: " ALPACA_SECRET
    read -p "Discord Bot Token: " DISCORD_TOKEN
    read -p "Discord Channel ID: " DISCORD_CHANNEL
    read -p "OpenAI API Key: " OPENAI_KEY
    read -p "Anthropic API Key (optional, press Enter to skip): " ANTHROPIC_KEY
    
    # Update .env file
    sed -i "s/your_alpaca_api_key/$ALPACA_KEY/" .env
    sed -i "s/your_alpaca_secret_key/$ALPACA_SECRET/" .env
    sed -i "s/your_discord_bot_token/$DISCORD_TOKEN/" .env
    sed -i "s/your_channel_id/$DISCORD_CHANNEL/" .env
    sed -i "s/your_openai_key/$OPENAI_KEY/" .env
    
    if [ ! -z "$ANTHROPIC_KEY" ]; then
        sed -i "s/your_anthropic_key/$ANTHROPIC_KEY/" .env
    fi
    
    echo -e "${GREEN}✓${NC} Environment configured"
else
    echo -e "${YELLOW}⚠${NC}  .env file already exists, skipping configuration"
fi
echo ""

# Create systemd service
echo "🔧 Setting up systemd service for auto-start..."

SERVICE_FILE="/etc/systemd/system/tara.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=TARA Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/options-AI-BOT
Environment="PATH=$INSTALL_DIR/options-AI-BOT/venv/bin"
ExecStart=$INSTALL_DIR/options-AI-BOT/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tara

echo -e "${GREEN}✓${NC} Systemd service created and enabled"
echo ""

# Create backup script
echo "💾 Setting up backup script..."
mkdir -p "$HOME/backups"

BACKUP_SCRIPT="$HOME/backup-tara.sh"
cat > "$BACKUP_SCRIPT" <<'EOF'
#!/bin/bash
cd $HOME/trading/options-AI-BOT
tar -czf $HOME/backups/tara-$(date +%Y%m%d).tar.gz .env data/ logs/
find $HOME/backups -name "tara-*.tar.gz" -mtime +7 -delete
EOF

chmod +x "$BACKUP_SCRIPT"

# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT") | crontab -

echo -e "${GREEN}✓${NC} Backup script created (runs daily at 2 AM)"
echo ""

# Test run
echo "🧪 Testing TARA..."
echo "Starting test run (will stop after 10 seconds)..."

timeout 10 python main.py || true

echo ""
echo -e "${GREEN}✓${NC} Test run complete"
echo ""

# Summary
echo "========================================"
echo "🎉 TARA Setup Complete!"
echo "========================================"
echo ""
echo "Installation directory: $INSTALL_DIR/options-AI-BOT"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Start TARA now:"
echo "   sudo systemctl start tara"
echo ""
echo "2. Check status:"
echo "   sudo systemctl status tara"
echo ""
echo "3. View logs:"
echo "   sudo journalctl -u tara -f"
echo ""
echo "4. Stop TARA:"
echo "   sudo systemctl stop tara"
echo ""
echo "5. Restart TARA:"
echo "   sudo systemctl restart tara"
echo ""
echo "📊 Monitoring:"
echo "   - System resources: htop"
echo "   - Temperature: vcgencmd measure_temp"
echo "   - Logs: tail -f $INSTALL_DIR/options-AI-BOT/logs/tara_*.log"
echo ""
echo "💡 TARA will auto-start on boot!"
echo ""
echo "🚀 Ready to trade! Start TARA with: sudo systemctl start tara"
echo ""
