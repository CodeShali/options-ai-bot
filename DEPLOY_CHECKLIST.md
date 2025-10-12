# ✅ RAILWAY DEPLOYMENT CHECKLIST

## 🚀 **DEPLOY IN 15 MINUTES**

---

## **STEP 1: PREPARE CODE** (5 min)

### ✅ Files Created
- [x] `requirements.txt` - Python dependencies
- [x] `Procfile` - Railway startup command
- [x] `.railwayignore` - Files to exclude
- [x] `main.py` - Updated for cloud (PORT variable)

### ✅ Ready to Deploy!

---

## **STEP 2: PUSH TO GITHUB** (5 min)

### **2.1 Initialize Git**
```bash
cd /Users/shashank/Documents/options-AI-BOT

# Check if git is initialized
git status

# If not initialized:
git init
```

### **2.2 Create .gitignore**
```bash
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
.env
.DS_Store
logs/
data/*.db
*.log
.pytest_cache/
.vscode/
.idea/
EOF
```

### **2.3 Commit Code**
```bash
git add .
git commit -m "Ready for Railway deployment"
```

### **2.4 Create GitHub Repo**
1. Go to https://github.com/new
2. Name: `options-ai-bot`
3. Make it **Private** (contains trading logic)
4. Don't initialize with README
5. Click "Create repository"

### **2.5 Push to GitHub**
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/options-ai-bot.git
git branch -M main
git push -u origin main
```

✅ **Code is on GitHub!**

---

## **STEP 3: DEPLOY TO RAILWAY** (5 min)

### **3.1 Sign Up**
1. Go to https://railway.app/
2. Click "Login"
3. Choose "Login with GitHub"
4. Authorize Railway

### **3.2 Create Project**
1. Click "New Project"
2. Choose "Deploy from GitHub repo"
3. Select `options-ai-bot`
4. Railway will start building

### **3.3 Add Environment Variables**

Click on your service → "Variables" tab → Add these:

```
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
OPENAI_API_KEY=your_openai_api_key_here
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_discord_channel_id_here
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
OPTIONS_STRIKE_PREFERENCE=OTM
OPTIONS_OTM_STRIKES=1
```

**⚠️ IMPORTANT:** Get these from your local `.env` file!

### **3.4 Wait for Deployment**
- Railway will build (2-3 minutes)
- Watch the logs
- Should see: "✅ Trading system started successfully"

✅ **Deployed to Railway!**

---

## **STEP 4: VERIFY** (2 min)

### **4.1 Check Railway Logs**
1. In Railway dashboard
2. Click "Deployments"
3. Click latest deployment
4. View logs
5. Look for:
   ```
   ✅ Trading system started successfully
   Mode: PAPER
   Bot logged in as OptionsAI Bot
   ```

### **4.2 Test Discord**
In your Discord server:
```
/status
```

Should respond with system status! ✅

### **4.3 Check API**
Railway gives you a URL like:
```
https://options-ai-bot-production.up.railway.app
```

Visit it in browser, should see:
```json
{"name":"Options Trading System API","version":"1.0.0","status":"running"}
```

✅ **Everything Working!**

---

## **STEP 5: CONFIGURE DATABASE** (Optional, 2 min)

### **5.1 Add Persistent Volume**
1. In Railway dashboard
2. Click your service
3. Go to "Settings"
4. Scroll to "Volumes"
5. Click "Add Volume"
6. Mount path: `/app/data`
7. Click "Add"

This ensures your database persists across deployments.

✅ **Database Persistent!**

---

## 🎉 **YOU'RE DONE!**

### **Your Bot is Now:**
- ✅ Running 24/7 in the cloud
- ✅ Accessible from Discord anywhere
- ✅ Auto-restarts if it crashes
- ✅ Auto-deploys when you push to GitHub
- ✅ Costs $0/month (free tier)

---

## 📱 **MANAGE FROM DISCORD**

### **All Commands Work:**
```
/status              - System health
/simulate            - Run tests
/sentiment SPY       - Market sentiment
/positions           - Open positions
/account             - Account info
/update-limit        - Adjust limits
/watchlist-add TSLA  - Add symbol
/scan-now            - Trigger scan
```

### **Monitor from Anywhere:**
- Your phone
- Work computer
- Anywhere with Discord

---

## 🔄 **UPDATE YOUR BOT**

### **Make Changes:**
```bash
# Edit code locally
vim agents/strategy_agent.py

# Commit and push
git add .
git commit -m "Updated strategy"
git push

# Railway auto-deploys in 2-3 minutes!
```

### **Check Deployment:**
1. Railway dashboard → Deployments
2. Watch logs
3. Test in Discord

---

## 📊 **MONITOR PERFORMANCE**

### **Railway Dashboard:**
- CPU usage
- Memory usage
- Logs
- Deployments
- Metrics

### **Discord:**
```
/performance 7   - Last 7 days
/trades 10       - Last 10 trades
/positions       - Current positions
```

---

## 🚨 **TROUBLESHOOTING**

### **Bot Not Starting?**

**Check Railway logs:**
1. Dashboard → Deployments → View Logs
2. Look for errors

**Common issues:**
- Missing environment variable
- Wrong Python version
- Syntax error

**Fix:**
```bash
# Fix locally
# Test: python main.py
# Push: git push
```

---

### **Discord Not Responding?**

**Check:**
1. Bot token correct in Railway variables
2. Bot invited to Discord server
3. Bot has permissions
4. Channel ID correct

**Test:**
```bash
# In Railway logs, should see:
"Bot logged in as OptionsAI Bot"
```

---

### **Database Not Persisting?**

**Solution:**
1. Add Railway volume (see Step 5)
2. Mount path: `/app/data`
3. Redeploy

---

## 💰 **COST TRACKING**

### **Railway Free Tier:**
- $5/month credit
- Your bot uses ~$3-4/month
- **Cost: $0** (within free tier)

### **Monitor Usage:**
1. Railway dashboard
2. Click "Usage"
3. See current month usage

### **If You Exceed:**
- Add payment method
- ~$5-10/month for your bot
- Still very cheap!

---

## 🎯 **WHAT'S NEXT?**

### **Your Bot is Live!**

Now you can:
1. ✅ Close your Mac - bot keeps running
2. ✅ Travel - manage from Discord
3. ✅ Sleep - bot trades 24/7
4. ✅ Update code - auto-deploys

### **Monitor for a Week:**
- Check Discord daily
- Review Railway logs
- Watch for errors
- Verify trades

### **Then:**
- Optimize parameters
- Add Phase 2 features (optional)
- Consider live trading (after testing)

---

## 📞 **SUPPORT**

### **Railway Issues:**
- Docs: https://docs.railway.app/
- Discord: https://discord.gg/railway
- Status: https://status.railway.app/

### **Bot Issues:**
- Check Railway logs
- Test locally first
- Review Discord errors

---

## ✅ **FINAL CHECKLIST**

- [ ] Code pushed to GitHub
- [ ] Railway project created
- [ ] Environment variables added
- [ ] Deployment successful
- [ ] Logs show "Trading system started"
- [ ] Discord `/status` works
- [ ] API URL responds
- [ ] Volume added (optional)
- [ ] Tested all commands
- [ ] Monitoring set up

---

## 🎉 **CONGRATULATIONS!**

**Your AI trading bot is now running in the cloud!**

- ✅ 24/7 operation
- ✅ Managed from Discord
- ✅ Auto-deploys
- ✅ Free hosting

**Trade from anywhere!** 🚀📈

---

*Deployment Guide*  
*Platform: Railway.app*  
*Time: 15 minutes*  
*Cost: $0/month*

