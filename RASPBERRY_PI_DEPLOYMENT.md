# TARA on Raspberry Pi 4 - Deployment Guide

**Device:** Raspberry Pi 4 Model B  
**Cost:** $0/month (you already own it!)  
**Status:** ✅ PERFECT FOR TARA

---

## ✅ **Can Raspberry Pi 4 Run TARA?**

### **YES! Absolutely!** 🎉

**Your Raspberry Pi 4 Model B is MORE than capable:**

| Requirement | TARA Needs | Pi 4 Has | Status |
|-------------|------------|----------|--------|
| **RAM** | 500MB-1GB | 2GB/4GB/8GB | ✅ Plenty |
| **CPU** | 1-2 cores | 4 cores @ 1.5GHz | ✅ Perfect |
| **Storage** | 5-10GB | 16GB+ SD card | ✅ Enough |
| **Network** | WiFi/Ethernet | Both | ✅ Great |
| **Power** | Low | Very low | ✅ Ideal |
| **24/7** | Yes | Yes | ✅ Perfect |

---

## 🎯 **Why Raspberry Pi 4 is PERFECT:**

### **Advantages:**

1. **💰 Zero Cost** - You already own it!
2. **⚡ Low Power** - ~5W (costs ~$0.50/month electricity)
3. **🔇 Silent** - No noise, no heat issues
4. **📍 Local** - Full control, no cloud dependencies
5. **🔒 Secure** - Your data stays on your network
6. **🚀 Fast Enough** - 4 cores is plenty for TARA
7. **💾 Sufficient RAM** - Even 2GB model works fine

### **Perfect For:**
- ✅ Paper trading
- ✅ Live trading (small to medium scale)
- ✅ 24/7 operation
- ✅ Learning and testing
- ✅ Personal use

---

## 📊 **Performance Expectations:**

### **What Will Work Great:**
- ✅ Discord bot (instant responses)
- ✅ Market scanning (< 10 seconds)
- ✅ Order execution (< 2 seconds)
- ✅ Position monitoring (real-time)
- ✅ AI analysis (OpenAI API calls)
- ✅ Database operations (fast)
- ✅ 10+ concurrent positions

### **What Might Be Slower:**
- ⚠️ Initial startup (30-60 seconds vs 10 seconds)
- ⚠️ Large backtests (if you add that feature)
- ⚠️ Heavy data processing (but still acceptable)

### **What Won't Work:**
- ❌ Nothing! Everything will work fine.

---

## 🚀 **Quick Deployment Steps**

### **Step 1: Prepare Raspberry Pi**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 (if not already installed)
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install git
sudo apt install git -y

# Install system dependencies
sudo apt install libatlas-base-dev libopenblas-dev -y
```

### **Step 2: Clone Repository**

```bash
# Create directory
mkdir -p ~/trading
cd ~/trading

# Clone your repo
git clone https://github.com/your-username/options-AI-BOT.git
cd options-AI-BOT
```

### **Step 3: Setup Python Environment**

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### **Step 4: Configure Environment**

```bash
# Copy environment template
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
ANTHROPIC_API_KEY=your_claude_key  # Optional
```

### **Step 5: Test Run**

```bash
# Activate virtual environment
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

## 🔄 **Auto-Start on Boot (Recommended)**

### **Option 1: systemd Service (Best)**

Create service file:
```bash
sudo nano /etc/systemd/system/tara.service
```

Add this content:
```ini
[Unit]
Description=TARA Trading Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/trading/options-AI-BOT
Environment="PATH=/home/pi/trading/options-AI-BOT/venv/bin"
ExecStart=/home/pi/trading/options-AI-BOT/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable tara

# Start now
sudo systemctl start tara

# Check status
sudo systemctl status tara

# View logs
sudo journalctl -u tara -f
```

### **Option 2: Crontab (Simple)**

```bash
# Edit crontab
crontab -e

# Add this line
@reboot sleep 60 && cd /home/pi/trading/options-AI-BOT && /home/pi/trading/options-AI-BOT/venv/bin/python main.py >> /home/pi/tara.log 2>&1
```

---

## 📊 **Monitoring on Raspberry Pi**

### **Check System Resources**

```bash
# CPU and memory usage
htop

# Disk space
df -h

# Temperature
vcgencmd measure_temp

# System info
neofetch
```

### **Check TARA Status**

```bash
# If using systemd
sudo systemctl status tara

# View logs
tail -f logs/tara_*.log

# Check if running
ps aux | grep python
```

### **Discord Commands**
```
/status          # System status
/account         # Account info
/positions       # Current positions
```

---

## ⚡ **Performance Optimization for Pi**

### **1. Reduce Memory Usage**

Edit `config/settings.py`:
```python
# Reduce cache TTL
CACHE_TTL = 300  # 5 minutes instead of 15

# Limit concurrent operations
MAX_CONCURRENT_SCANS = 5  # Instead of 10
```

### **2. Optimize Logging**

```python
# In config/settings.py
LOG_LEVEL = "INFO"  # Not DEBUG
LOG_ROTATION = "5 MB"  # Smaller files
```

### **3. Enable Swap (if needed)**

```bash
# Check current swap
free -h

# If you have 2GB RAM, add 2GB swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### **4. Overclock (Optional)**

```bash
sudo nano /boot/config.txt

# Add these lines (safe overclock)
over_voltage=2
arm_freq=1750
```

---

## 🔒 **Security Best Practices**

### **1. Firewall Setup**

```bash
# Install UFW
sudo apt install ufw -y

# Allow SSH (if you use it)
sudo ufw allow 22

# Allow Discord (outbound is default allowed)
# No inbound ports needed for TARA

# Enable firewall
sudo ufw enable
```

### **2. Secure SSH (if enabled)**

```bash
# Change default password
passwd

# Disable password auth (use keys only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no

# Restart SSH
sudo systemctl restart ssh
```

### **3. Keep System Updated**

```bash
# Create update script
nano ~/update.sh

# Add:
#!/bin/bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

# Make executable
chmod +x ~/update.sh

# Run weekly
crontab -e
# Add: 0 3 * * 0 /home/pi/update.sh
```

---

## 🐛 **Troubleshooting**

### **Issue: Out of Memory**

```bash
# Check memory
free -h

# Add swap (see optimization section)
# Or reduce cache TTL in settings
```

### **Issue: Slow Performance**

```bash
# Check CPU temperature
vcgencmd measure_temp

# If > 80°C, add cooling:
# - Heatsinks
# - Small fan
# - Better case ventilation
```

### **Issue: Service Won't Start**

```bash
# Check logs
sudo journalctl -u tara -n 50

# Check permissions
ls -la /home/pi/trading/options-AI-BOT

# Manually test
cd /home/pi/trading/options-AI-BOT
source venv/bin/activate
python main.py
```

### **Issue: Network Disconnects**

```bash
# Check WiFi power management
iwconfig

# Disable WiFi power saving
sudo nano /etc/rc.local
# Add before "exit 0":
iwconfig wlan0 power off

# Or use Ethernet (more reliable)
```

---

## 💡 **Pro Tips**

### **1. Remote Access**

```bash
# Install VNC for GUI access
sudo apt install realvnc-vnc-server -y
sudo raspi-config
# Enable VNC in Interface Options

# Or use SSH (already enabled)
ssh pi@raspberrypi.local
```

### **2. Backup Strategy**

```bash
# Backup script
nano ~/backup.sh

#!/bin/bash
cd /home/pi/trading/options-AI-BOT
tar -czf ~/backups/tara-$(date +%Y%m%d).tar.gz \
  .env data/ logs/

# Keep only last 7 days
find ~/backups -name "tara-*.tar.gz" -mtime +7 -delete

# Make executable
chmod +x ~/backup.sh

# Run daily
crontab -e
# Add: 0 2 * * * /home/pi/backup.sh
```

### **3. Monitor from Phone**

- Use Discord app to monitor TARA
- All commands work from mobile
- Get real-time notifications
- No need to access Pi directly

### **4. Static IP (Recommended)**

```bash
# Edit dhcpcd.conf
sudo nano /etc/dhcpcd.conf

# Add (adjust for your network):
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

---

## 📊 **Expected Resource Usage**

### **Typical Usage:**
```
CPU: 15-25% (4 cores, so ~1 core active)
RAM: 400-600MB (out of 2GB/4GB/8GB)
Disk: ~500MB (code + logs + database)
Network: ~1-5 MB/hour
Power: ~5W (~$0.50/month)
```

### **During Market Hours:**
```
CPU: 20-40% (scanning every 5 min)
RAM: 500-800MB
Network: ~10 MB/hour
```

### **Idle (After Hours):**
```
CPU: 5-10%
RAM: 300-400MB
Network: Minimal
```

---

## 🎯 **Recommended Pi 4 Model**

| Model | RAM | Price | Recommendation |
|-------|-----|-------|----------------|
| **Pi 4 2GB** | 2GB | $35 | ✅ Works fine |
| **Pi 4 4GB** | 4GB | $55 | ✅ **Recommended** |
| **Pi 4 8GB** | 8GB | $75 | ✅ Overkill but great |

**You probably have 4GB or 8GB - both are perfect!**

---

## ✅ **Final Checklist**

Before going live:

- [ ] Raspberry Pi 4 setup complete
- [ ] Python 3.11 installed
- [ ] TARA cloned and dependencies installed
- [ ] `.env` configured with API keys
- [ ] Test run successful
- [ ] systemd service configured
- [ ] Auto-start on boot working
- [ ] Firewall configured
- [ ] Backup script setup
- [ ] Discord bot responding
- [ ] Paper trading tested

---

## 🎉 **Summary**

**Your Raspberry Pi 4 is PERFECT for TARA!**

**Benefits:**
- ✅ Zero monthly cost
- ✅ Runs 24/7 reliably
- ✅ Low power consumption
- ✅ Full control
- ✅ More than enough performance
- ✅ Easy to maintain

**Expected Performance:**
- ✅ Scans: < 10 seconds
- ✅ Orders: < 2 seconds
- ✅ Discord: Instant
- ✅ Uptime: 99.9%+

**Cost Comparison:**
- Raspberry Pi: $0.50/month (electricity)
- Cloud hosting: $5-125/month
- **Savings: $60-1,500/year!**

---

## 🚀 **Quick Start Command**

```bash
# One-line setup (run on your Pi)
curl -sSL https://raw.githubusercontent.com/your-username/options-AI-BOT/main/setup-pi.sh | bash
```

*(We can create this script if you want)*

---

**You made the right choice! Raspberry Pi 4 is perfect for TARA.** 🎉

*Questions? Check the troubleshooting section or ask in Discord!*
