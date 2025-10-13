#!/bin/bash

# Deploy Options Trading Bot to DigitalOcean
# Simple, affordable, reliable hosting

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Options Trading Bot - DigitalOcean${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${BLUE}This script will help you deploy to DigitalOcean${NC}"
echo -e "${BLUE}Cost: \$6-12/month (vs \$125/month on GCP!)${NC}"
echo ""

# Check if running on DigitalOcean droplet
if [ -f /etc/digitalocean ]; then
    echo -e "${GREEN}✅ Running on DigitalOcean droplet${NC}"
    IS_DROPLET=true
else
    echo -e "${YELLOW}⚠️  Not on DigitalOcean droplet${NC}"
    echo -e "${YELLOW}This script should be run ON your droplet${NC}"
    echo ""
    echo -e "${BLUE}Steps to deploy:${NC}"
    echo "1. Create a DigitalOcean droplet (Ubuntu 22.04)"
    echo "2. SSH into your droplet: ssh root@your-droplet-ip"
    echo "3. Run this script on the droplet"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    IS_DROPLET=false
fi

echo ""
echo -e "${YELLOW}📋 Starting deployment...${NC}"
echo ""

# Update system
echo -e "${YELLOW}1️⃣  Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# Install Docker
echo -e "${YELLOW}2️⃣  Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker installed${NC}"
else
    echo -e "${GREEN}✅ Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${YELLOW}3️⃣  Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose
    echo -e "${GREEN}✅ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✅ Docker Compose already installed${NC}"
fi

# Install Git
echo -e "${YELLOW}4️⃣  Installing Git...${NC}"
if ! command -v git &> /dev/null; then
    apt-get install -y git
    echo -e "${GREEN}✅ Git installed${NC}"
else
    echo -e "${GREEN}✅ Git already installed${NC}"
fi

# Clone or update repository
echo -e "${YELLOW}5️⃣  Setting up application...${NC}"
APP_DIR="/opt/options-trading-bot"

if [ -d "$APP_DIR" ]; then
    echo "Application directory exists. Updating..."
    cd $APP_DIR
    git pull
else
    echo "Cloning repository..."
    read -p "Enter your GitHub repository URL: " REPO_URL
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

# Setup environment file
echo -e "${YELLOW}6️⃣  Configuring environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Please enter your API keys:${NC}"
    echo ""
    
    read -p "Alpaca API Key: " ALPACA_KEY
    read -p "Alpaca Secret Key: " ALPACA_SECRET
    read -p "Discord Bot Token: " DISCORD_TOKEN
    read -p "OpenAI API Key: " OPENAI_KEY
    read -p "Anthropic API Key: " ANTHROPIC_KEY
    read -p "NewsAPI Key: " NEWS_KEY
    
    # Update .env file
    sed -i "s/your_alpaca_api_key_here/$ALPACA_KEY/" .env
    sed -i "s/your_alpaca_secret_key_here/$ALPACA_SECRET/" .env
    sed -i "s/your_discord_token_here/$DISCORD_TOKEN/" .env
    sed -i "s/your_openai_api_key_here/$OPENAI_KEY/" .env
    sed -i "s/your_anthropic_api_key_here/$ANTHROPIC_KEY/" .env
    sed -i "s/your_news_api_key_here/$NEWS_KEY/" .env
    
    echo -e "${GREEN}✅ Environment configured${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Create directories
echo -e "${YELLOW}7️⃣  Creating directories...${NC}"
mkdir -p data logs
chmod -R 755 data logs
echo -e "${GREEN}✅ Directories created${NC}"

# Build and start containers
echo -e "${YELLOW}8️⃣  Building and starting containers...${NC}"
docker-compose down 2>/dev/null || true
docker-compose build
docker-compose up -d

# Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Check if running
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Containers are running${NC}"
else
    echo -e "${RED}❌ Containers failed to start${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

# Setup firewall
echo -e "${YELLOW}9️⃣  Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow 22/tcp    # SSH
    ufw allow 8000/tcp  # API
    echo -e "${GREEN}✅ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠️  UFW not installed, skipping firewall setup${NC}"
fi

# Setup auto-restart on reboot
echo -e "${YELLOW}🔟 Setting up auto-restart...${NC}"
cat > /etc/systemd/system/trading-bot.service <<EOF
[Unit]
Description=Options Trading Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-bot.service
echo -e "${GREEN}✅ Auto-restart configured${NC}"

# Get droplet IP
DROPLET_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Service Information:${NC}"
echo "  Droplet IP: $DROPLET_IP"
echo "  API URL: http://$DROPLET_IP:8000"
echo "  Health Check: http://$DROPLET_IP:8000/health"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:      docker-compose logs -f"
echo "  Restart bot:    docker-compose restart"
echo "  Stop bot:       docker-compose down"
echo "  Start bot:      docker-compose up -d"
echo "  Update bot:     git pull && docker-compose up -d --build"
echo ""
echo -e "${YELLOW}Test Your Bot:${NC}"
echo "  1. Test health: curl http://$DROPLET_IP:8000/health"
echo "  2. Check logs:  docker-compose logs -f"
echo "  3. Test Discord commands: /status, /help"
echo ""
echo -e "${YELLOW}Cost:${NC}"
echo "  DigitalOcean: \$6-12/month"
echo "  vs GCP: \$125/month"
echo "  Savings: \$113-119/month (95% cheaper!)"
echo ""
echo -e "${GREEN}🎉 Your trading bot is now running!${NC}"
echo -e "${BLUE}💡 Tip: Get \$200 free credit at https://www.digitalocean.com/${NC}"
