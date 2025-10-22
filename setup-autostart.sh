#!/bin/bash
# TARA Trading Bot - Setup Auto-Start Service
# Run this after installing dependencies

set -e  # Exit on error

echo "🔧 TARA Trading Bot - Auto-Start Setup"
echo "======================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: main.py not found!${NC}"
    echo "Please run this script from the options-ai-bot directory"
    exit 1
fi

# Get current directory
CURRENT_DIR=$(pwd)
VENV_PATH="$CURRENT_DIR/venv"

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run install-dependencies.sh first"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found virtual environment"
echo ""

# Create systemd service
echo "🔧 Creating systemd service..."

SERVICE_FILE="/etc/systemd/system/tara.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=TARA Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Service file created: $SERVICE_FILE"
echo ""

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling auto-start..."
sudo systemctl enable tara

echo -e "${GREEN}✓${NC} Auto-start enabled"
echo ""

# Create backup script
echo "💾 Setting up backup script..."
mkdir -p "$HOME/backups"

BACKUP_SCRIPT="$HOME/backup-tara.sh"
cat > "$BACKUP_SCRIPT" <<EOF
#!/bin/bash
cd $CURRENT_DIR
tar -czf $HOME/backups/tara-\$(date +%Y%m%d).tar.gz .env data/ logs/ 2>/dev/null
find $HOME/backups -name "tara-*.tar.gz" -mtime +7 -delete
EOF

chmod +x "$BACKUP_SCRIPT"

# Add to crontab if not already there
(crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT") || \
    (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT") | crontab -

echo -e "${GREEN}✓${NC} Backup script created (runs daily at 2 AM)"
echo ""

# Summary
echo "======================================="
echo "🎉 Auto-Start Setup Complete!"
echo "======================================="
echo ""
echo "📋 Service Commands:"
echo ""
echo "Start TARA:"
echo "  sudo systemctl start tara"
echo ""
echo "Stop TARA:"
echo "  sudo systemctl stop tara"
echo ""
echo "Restart TARA:"
echo "  sudo systemctl restart tara"
echo ""
echo "Check status:"
echo "  sudo systemctl status tara"
echo ""
echo "View logs:"
echo "  sudo journalctl -u tara -f"
echo ""
echo "💡 TARA will now auto-start on boot!"
echo ""
echo "🚀 Start TARA now with: sudo systemctl start tara"
echo ""
