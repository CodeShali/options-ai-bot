# Raspberry Pi - Quick Commands

**For already cloned repository**

---

## 🚀 **First Time Setup (3 Commands)**

```bash
# 1. Go to your repository
cd ~/trading/options-ai-bot

# 2. Install dependencies
bash install-dependencies.sh

# 3. Configure API keys
nano .env
```

**That's it!** Now you can run TARA.

---

## ▶️ **Running TARA**

### **Manual Run:**
```bash
cd ~/trading/options-ai-bot
source venv/bin/activate
python main.py
```

### **Auto-Start Setup (Optional):**
```bash
cd ~/trading/options-ai-bot
bash setup-autostart.sh
sudo systemctl start tara
```

---

## 🎮 **Control Commands**

### **If Using Auto-Start:**
```bash
# Start
sudo systemctl start tara

# Stop
sudo systemctl stop tara

# Restart
sudo systemctl restart tara

# Status
sudo systemctl status tara

# Logs
sudo journalctl -u tara -f
```

### **If Running Manually:**
```bash
# Stop: Press Ctrl+C in terminal

# View logs
tail -f logs/tara_*.log
```

---

## 📊 **Monitoring**

```bash
# System resources
htop

# Temperature
vcgencmd measure_temp

# Disk space
df -h

# TARA logs
tail -f ~/trading/options-ai-bot/logs/tara_*.log
```

---

## 🔄 **Updating TARA**

```bash
cd ~/trading/options-ai-bot

# Stop if running
sudo systemctl stop tara  # or Ctrl+C if manual

# Pull updates
git pull

# Activate venv
source venv/bin/activate

# Update dependencies (if needed)
pip install -r requirements.txt --upgrade

# Restart
sudo systemctl start tara  # or python main.py
```

---

## 🐛 **Troubleshooting**

### **Check if TARA is running:**
```bash
ps aux | grep python
```

### **Check logs for errors:**
```bash
# If using systemd
sudo journalctl -u tara -n 50

# If running manually
tail -50 ~/trading/options-ai-bot/logs/tara_*.log
```

### **Reinstall dependencies:**
```bash
cd ~/trading/options-ai-bot
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### **Reset virtual environment:**
```bash
cd ~/trading/options-ai-bot
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📝 **Configuration**

### **Edit API keys:**
```bash
cd ~/trading/options-ai-bot
nano .env
```

### **Edit settings:**
```bash
nano config/settings.py
```

---

## 💾 **Backup**

### **Manual backup:**
```bash
cd ~/trading/options-ai-bot
tar -czf ~/tara-backup-$(date +%Y%m%d).tar.gz .env data/ logs/
```

### **Restore backup:**
```bash
cd ~/trading/options-ai-bot
tar -xzf ~/tara-backup-YYYYMMDD.tar.gz
```

---

## 🎯 **Quick Reference**

| Task | Command |
|------|---------|
| **Install** | `bash install-dependencies.sh` |
| **Configure** | `nano .env` |
| **Run** | `python main.py` |
| **Auto-start** | `bash setup-autostart.sh` |
| **Start** | `sudo systemctl start tara` |
| **Stop** | `sudo systemctl stop tara` |
| **Status** | `sudo systemctl status tara` |
| **Logs** | `sudo journalctl -u tara -f` |
| **Update** | `git pull` |

---

## 📚 **Full Guides**

- **QUICK_PI_SETUP.md** - Complete setup guide
- **RASPBERRY_PI_DEPLOYMENT.md** - Detailed deployment
- **START_HERE.md** - General quick start

---

**Keep this file handy for quick reference!** 📌
