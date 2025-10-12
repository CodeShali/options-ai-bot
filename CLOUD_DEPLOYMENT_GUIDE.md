# ☁️ CLOUD DEPLOYMENT GUIDE

**Goal:** Run your trading system 24/7 in the cloud, manage via Discord  
**Current:** Running locally on your Mac  
**Target:** Cloud server running continuously

---

## 🎯 **BEST FREE OPTIONS**

### **Option 1: Railway.app** ⭐ **RECOMMENDED**
**Why:** Easiest, generous free tier, perfect for this use case

**Free Tier:**
- ✅ $5/month credit (enough for 24/7 small app)
- ✅ 512 MB RAM, 1 vCPU
- ✅ Automatic deployments from GitHub
- ✅ Built-in PostgreSQL (if needed)
- ✅ Easy environment variables
- ✅ Logs viewer
- ✅ No credit card required initially

**Limitations:**
- Sleeps after 500 hours/month (still plenty)
- Limited to 100 GB outbound bandwidth

**Best for:** Your trading bot (lightweight, runs 24/7)

---

### **Option 2: Render.com** 
**Why:** Similar to Railway, also very easy

**Free Tier:**
- ✅ 750 hours/month free
- ✅ 512 MB RAM
- ✅ Auto-deploy from GitHub
- ✅ Free PostgreSQL
- ✅ SSL included

**Limitations:**
- Spins down after 15 min inactivity (not ideal for trading bot)
- Takes 30-60 sec to wake up

**Best for:** Web apps, not ideal for 24/7 bots

---

### **Option 3: Google Cloud (GCP) Free Tier**
**Why:** Most powerful free tier, but more complex

**Free Tier (Always Free):**
- ✅ 1 f1-micro instance (0.6 GB RAM)
- ✅ 30 GB disk
- ✅ 1 GB outbound traffic/month
- ✅ Runs 24/7 forever

**Limitations:**
- Requires credit card
- More complex setup
- Need to manage server yourself

**Best for:** If you want full control and know Linux

---

### **Option 4: Oracle Cloud Free Tier** 💎 **MOST GENEROUS**
**Why:** Best free tier specs, runs forever

**Free Tier (Always Free):**
- ✅ 2 AMD VMs (1 GB RAM each) OR
- ✅ 4 ARM VMs (24 GB RAM total!)
- ✅ 200 GB storage
- ✅ 10 TB outbound traffic/month
- ✅ Runs 24/7 forever

**Limitations:**
- Requires credit card
- More complex setup
- ARM architecture (may need adjustments)

**Best for:** If you want maximum free resources

---

### **Option 5: AWS Free Tier**
**Why:** Industry standard, but limited free tier

**Free Tier (12 months):**
- ✅ 750 hours/month t2.micro (1 GB RAM)
- ✅ 30 GB storage
- ✅ Only free for first 12 months

**Limitations:**
- Credit card required
- Complex pricing (easy to accidentally pay)
- Free tier expires after 1 year

**Best for:** If you're already familiar with AWS

---

## 🏆 **RECOMMENDATION**

### **For You: Railway.app** ⭐

**Why Railway is best for your use case:**
1. ✅ **Easiest setup** - Deploy in 10 minutes
2. ✅ **No credit card** - Start immediately
3. ✅ **Perfect for bots** - Runs 24/7
4. ✅ **GitHub integration** - Auto-deploy on push
5. ✅ **Good free tier** - $5/month credit
6. ✅ **Great logs** - Easy debugging
7. ✅ **Environment variables** - Easy config

**Your bot will:**
- Run 24/7 in the cloud
- Auto-restart if it crashes
- Deploy automatically when you update code
- Cost $0-5/month (likely $0)

---

## 🚀 **DEPLOYMENT GUIDE: RAILWAY**

### **Step 1: Prepare Your Code** (5 minutes)

#### **1.1 Create requirements.txt**
```bash
cd /Users/shashank/Documents/options-AI-BOT
pip freeze > requirements.txt
```

#### **1.2 Create Procfile**
```bash
cat > Procfile << 'EOF'
web: python main.py
EOF
```

#### **1.3 Update main.py for Railway**
Add this at the top of `main.py`:

```python
import os

# Railway provides PORT environment variable
PORT = int(os.getenv("PORT", 8000))

# Update uvicorn.run() call
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",  # Important: bind to all interfaces
        port=PORT,       # Use Railway's port
        log_level="info"
    )
```

#### **1.4 Create .railwayignore**
```bash
cat > .railwayignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
.DS_Store
logs/
data/
*.db
EOF
```

---

### **Step 2: Push to GitHub** (5 minutes)

#### **2.1 Create GitHub repo**
```bash
# Initialize git (if not already)
cd /Users/shashank/Documents/options-AI-BOT
git init

# Create .gitignore
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
.DS_Store
logs/
data/*.db
*.log
EOF

# Commit code
git add .
git commit -m "Initial commit - Trading bot"

# Create repo on GitHub (via web or CLI)
# Then push
git remote add origin https://github.com/YOUR_USERNAME/options-ai-bot.git
git branch -M main
git push -u origin main
```

---

### **Step 3: Deploy to Railway** (5 minutes)

#### **3.1 Sign up for Railway**
1. Go to https://railway.app/
2. Click "Start a New Project"
3. Sign in with GitHub

#### **3.2 Create new project**
1. Click "Deploy from GitHub repo"
2. Select your `options-ai-bot` repository
3. Railway will auto-detect Python

#### **3.3 Add environment variables**
In Railway dashboard:
1. Click on your service
2. Go to "Variables" tab
3. Add all your `.env` variables:

```
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
OPENAI_API_KEY=your_key
DISCORD_BOT_TOKEN=your_token
DISCORD_CHANNEL_ID=your_channel_id
TRADING_MODE=paper
MAX_POSITION_SIZE=5000
MAX_DAILY_LOSS=1000
PROFIT_TARGET_PCT=0.50
STOP_LOSS_PCT=0.30
MAX_OPEN_POSITIONS=5
SCAN_INTERVAL_MINUTES=5
ENABLE_OPTIONS_TRADING=true
ENABLE_STOCK_TRADING=true
OPTIONS_MAX_CONTRACTS=2
OPTIONS_MAX_PREMIUM=500
OPTIONS_MIN_DTE=30
OPTIONS_MAX_DTE=45
OPTIONS_CLOSE_DTE=7
```

#### **3.4 Deploy**
1. Railway will automatically build and deploy
2. Wait 2-3 minutes for deployment
3. Check logs to verify it's running

---

### **Step 4: Verify Deployment** (2 minutes)

#### **4.1 Check logs**
In Railway dashboard:
1. Click "Deployments"
2. Click latest deployment
3. View logs
4. Should see: "✅ Trading system started successfully"

#### **4.2 Test Discord**
In Discord:
```
/status
```
Should respond with system status!

#### **4.3 Check API**
Railway gives you a URL like: `https://your-app.railway.app`
Visit it to see: `{"name":"Options Trading System API"...}`

---

## 🔧 **CONFIGURATION FOR CLOUD**

### **Database: Use SQLite with Persistent Volume**

Railway provides persistent storage. Update your code:

```python
# services/database_service.py
import os

# Use Railway's volume path if available
if os.getenv("RAILWAY_VOLUME_MOUNT_PATH"):
    DB_PATH = os.path.join(
        os.getenv("RAILWAY_VOLUME_MOUNT_PATH"),
        "trading.db"
    )
else:
    DB_PATH = "./data/trading.db"
```

In Railway:
1. Go to service settings
2. Add a volume
3. Mount path: `/app/data`

---

### **Logs: Use Railway's Log Viewer**

Your logs will automatically appear in Railway dashboard.

Optional: Send critical logs to Discord:

```python
# In orchestrator_agent.py
async def _send_critical_log(self, message: str):
    """Send critical logs to Discord."""
    if self.discord_bot:
        await self.discord_bot.send_message(
            f"🚨 **CRITICAL:** {message}"
        )
```

---

## 💰 **COST ESTIMATE**

### **Railway Pricing**

**Free Tier:**
- $5/month credit
- Your bot uses ~$3-4/month
- **Cost: $0/month** (within free tier)

**If you exceed free tier:**
- $0.000231/GB-hour RAM
- $0.000463/vCPU-hour
- Your bot: ~$5-10/month

**Recommendation:** Start free, upgrade if needed

---

## 🔄 **CONTINUOUS DEPLOYMENT**

### **Auto-Deploy on Code Changes**

Railway automatically deploys when you push to GitHub:

```bash
# Make changes locally
vim agents/strategy_agent.py

# Commit and push
git add .
git commit -m "Updated strategy logic"
git push

# Railway automatically deploys!
# Check Discord in 2-3 minutes
```

---

## 📊 **MONITORING**

### **From Discord**

All your commands work:
```
/status          - System health
/simulate        - Run tests
/positions       - Check positions
/account         - Account info
/sentiment SPY   - Market sentiment
```

### **Railway Dashboard**

Monitor:
- CPU usage
- Memory usage
- Logs
- Deployments
- Metrics

---

## 🛡️ **SECURITY**

### **Best Practices**

1. **Never commit .env**
   ```bash
   # Already in .gitignore
   .env
   ```

2. **Use Railway environment variables**
   - All secrets in Railway dashboard
   - Never in code

3. **Keep API keys secure**
   - Rotate keys periodically
   - Use paper trading initially

4. **Monitor logs**
   - Check Railway logs daily
   - Watch for errors

---

## 🚨 **TROUBLESHOOTING**

### **Bot not starting?**

**Check Railway logs:**
1. Go to Railway dashboard
2. Click "Deployments"
3. View logs
4. Look for errors

**Common issues:**
- Missing environment variables
- Wrong Python version
- Missing dependencies

**Fix:**
```bash
# Update requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Updated dependencies"
git push
```

---

### **Discord not responding?**

**Check:**
1. Bot token correct in Railway variables
2. Bot has permissions in Discord server
3. Channel ID correct

**Test:**
```bash
# Check Railway logs for Discord connection
# Should see: "Bot logged in as OptionsAI Bot"
```

---

### **Database issues?**

**Solution:**
1. Add Railway volume
2. Update database path
3. Redeploy

```bash
# In Railway dashboard
Settings → Volumes → Add Volume
Mount path: /app/data
```

---

## 🎯 **ALTERNATIVE: ORACLE CLOUD** (Most Powerful Free)

### **If You Want Maximum Free Resources**

**Oracle Cloud Free Tier:**
- 4 ARM VMs with 24 GB RAM total
- Runs forever (not trial)
- Free forever

**Setup (30 minutes):**

1. **Sign up**
   - https://www.oracle.com/cloud/free/
   - Requires credit card (not charged)

2. **Create VM**
   - Choose ARM instance
   - Ubuntu 22.04
   - 1 GB RAM (or more)

3. **Install dependencies**
   ```bash
   ssh ubuntu@your-vm-ip
   
   # Install Python
   sudo apt update
   sudo apt install python3.9 python3-pip git -y
   
   # Clone repo
   git clone https://github.com/YOUR_USERNAME/options-ai-bot.git
   cd options-ai-bot
   
   # Install dependencies
   pip3 install -r requirements.txt
   
   # Create .env
   nano .env
   # Paste your environment variables
   
   # Run with systemd (auto-restart)
   sudo nano /etc/systemd/system/trading-bot.service
   ```

4. **Create systemd service**
   ```ini
   [Unit]
   Description=Options Trading Bot
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/options-ai-bot
   ExecStart=/usr/bin/python3 main.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

5. **Start service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable trading-bot
   sudo systemctl start trading-bot
   
   # Check status
   sudo systemctl status trading-bot
   
   # View logs
   sudo journalctl -u trading-bot -f
   ```

**Pros:**
- Most powerful free tier
- Runs forever
- Full control

**Cons:**
- More complex setup
- Need to manage server
- Need Linux knowledge

---

## 📋 **COMPARISON TABLE**

| Feature | Railway | Render | GCP | Oracle | AWS |
|---------|---------|--------|-----|--------|-----|
| **Ease of Setup** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Free Tier** | $5/mo credit | 750 hrs | f1-micro | 4 VMs | t2.micro |
| **RAM** | 512 MB | 512 MB | 600 MB | 24 GB | 1 GB |
| **Always On** | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Auto Deploy** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Credit Card** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Best For** | Bots | Web apps | Control | Power | AWS users |

---

## 🎯 **FINAL RECOMMENDATION**

### **For Your Trading Bot:**

**Start with Railway:**
1. ✅ Easiest setup (10 minutes)
2. ✅ No credit card needed
3. ✅ Perfect for 24/7 bots
4. ✅ Auto-deploy from GitHub
5. ✅ Free tier is enough

**Later, if needed:**
- Upgrade Railway ($5-10/month)
- Or migrate to Oracle Cloud (free forever, more power)

---

## 🚀 **QUICK START CHECKLIST**

### **Deploy to Railway in 15 Minutes**

- [ ] Create `requirements.txt`
- [ ] Create `Procfile`
- [ ] Update `main.py` for PORT
- [ ] Create `.railwayignore`
- [ ] Push to GitHub
- [ ] Sign up for Railway
- [ ] Connect GitHub repo
- [ ] Add environment variables
- [ ] Deploy
- [ ] Test with `/status` in Discord
- [ ] Done! ✅

---

## 📞 **SUPPORT**

### **Railway Support**
- Docs: https://docs.railway.app/
- Discord: https://discord.gg/railway
- Twitter: @Railway

### **If You Get Stuck**
1. Check Railway logs
2. Check Discord bot connection
3. Verify environment variables
4. Test locally first

---

## 🎉 **BENEFITS OF CLOUD DEPLOYMENT**

### **What You Get**

✅ **24/7 Operation**
- Runs even when your Mac is off
- Never miss a trading opportunity
- Continuous monitoring

✅ **Reliability**
- Auto-restart on crashes
- Redundant infrastructure
- Better uptime than local

✅ **Accessibility**
- Manage from anywhere via Discord
- No VPN needed
- Works on phone

✅ **Scalability**
- Easy to upgrade resources
- Add more features
- Handle more load

✅ **Peace of Mind**
- System always running
- Logs always available
- Easy to debug

---

**Ready to deploy?** Start with Railway! 🚀

*Guide created: 2025-10-12 1:10 AM*  
*Recommended: Railway.app*  
*Time to deploy: 15 minutes*

