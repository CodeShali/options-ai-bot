# Quick Raspberry Pi Setup (Debian/Raspberry Pi OS)

**For Raspberry Pi 4 running Debian/Raspberry Pi OS**

---

## ⚡ **Simplest Method (Recommended)**

TARA works with **Python 3.9+**, which is already on your Raspberry Pi!

### **Step 1: Install Dependencies**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    libopenblas-dev \
    python3-dev \
    build-essential
```

### **Step 2: Clone Repository**

```bash
# Create directory
mkdir -p ~/trading
cd ~/trading

# Clone repository
git clone https://github.com/CodeShali/options-ai-bot.git
cd options-ai-bot
```

### **Step 3: Setup Python Environment**

```bash
# Create virtual environment with system Python
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Note:** This may take 10-15 minutes on Raspberry Pi. Be patient!

### **Step 4: Configure Environment**

```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
```

**Add your keys:**
```env
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
DISCORD_BOT_TOKEN=your_token_here
DISCORD_CHANNEL_ID=your_channel_id
OPENAI_API_KEY=your_openai_key
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### **Step 5: Test Run**

```bash
# Make sure venv is activated
source venv/bin/activate

# Run TARA
python main.py
```

**Expected output:**
```
✅ Trading system started successfully
Mode: PAPER
API: http://0.0.0.0:8000
🌟 TARA logged in as Tara Assistant#7936
```

---

## 🔄 **Auto-Start on Boot**

### **Create systemd Service**

```bash
# Create service file
sudo nano /etc/systemd/system/tara.service
```

**Add this content** (adjust paths if needed):

```ini
[Unit]
Description=TARA Trading Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/trading/options-ai-bot
Environment="PATH=/home/pi/trading/options-ai-bot/venv/bin"
ExecStart=/home/pi/trading/options-ai-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable tara

# Start now
sudo systemctl start tara

# Check status
sudo systemctl status tara
```

---

## 📊 **Useful Commands**

### **Control TARA**

```bash
# Start
sudo systemctl start tara

# Stop
sudo systemctl stop tara

# Restart
sudo systemctl restart tara

# Check status
sudo systemctl status tara

# View logs
sudo journalctl -u tara -f
```

### **View TARA Logs**

```bash
# Real-time logs
tail -f ~/trading/options-ai-bot/logs/tara_*.log

# Last 100 lines
tail -100 ~/trading/options-ai-bot/logs/tara_*.log
```

### **Monitor System**

```bash
# CPU and memory
htop

# Temperature
vcgencmd measure_temp

# Disk space
df -h
```

---

## 🐛 **Troubleshooting**

### **Issue: pip install fails with "externally-managed-environment"**

**Solution:** Use virtual environment (which you already did!)

If you see this error, make sure you're in the venv:
```bash
source ~/trading/options-ai-bot/venv/bin/activate
```

### **Issue: Some packages fail to install**

**Solution:** Install system dependencies first:
```bash
sudo apt install -y \
    python3-dev \
    libopenblas-dev \
    build-essential \
    gfortran
```

Then retry:
```bash
pip install -r requirements.txt
```

### **Issue: Out of memory during pip install**

**Solution:** Install packages one at a time or add swap:
```bash
# Add 2GB swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### **Issue: TARA won't start**

**Check logs:**
```bash
sudo journalctl -u tara -n 50
```

**Common fixes:**
1. Check .env file has correct API keys
2. Ensure venv is activated
3. Check network connection
4. Verify Discord token is valid

---

## ✅ **Quick Checklist**

- [ ] System updated
- [ ] Python 3 and dependencies installed
- [ ] Repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed (pip install -r requirements.txt)
- [ ] .env file configured with API keys
- [ ] Test run successful
- [ ] systemd service created
- [ ] Auto-start enabled
- [ ] TARA running and responding in Discord

---

## 🎉 **You're Done!**

TARA is now running on your Raspberry Pi 4!

**Check Discord** - Your bot should be online and responding to `/status`

**Monitor:** Use Discord commands from anywhere - no need to access the Pi!

---

## 💡 **Pro Tips**

1. **Use Ethernet** - More stable than WiFi
2. **Static IP** - Easier to find your Pi
3. **Good power supply** - Use official Pi power adapter
4. **Cooling** - Add heatsinks or small fan
5. **Backup** - Copy .env file somewhere safe

---

**Need help?** Check the full guide: `RASPBERRY_PI_DEPLOYMENT.md`
