# 🚀 GCP Quick Start - 5 Minutes to Deploy

---

## ⚡ Super Fast Deployment

### **Step 1: Install gcloud CLI** (if not installed)
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### **Step 2: Run Deployment Script**
```bash
cd /Users/shashank/Documents/options-AI-BOT
./deploy-gcp.sh
```

### **Step 3: Follow Prompts**
```
Enter your GCP Project ID: your-project-id
Enter region: us-central1
Enter service name: options-trading-bot
```

### **Step 4: Provide API Keys**
When prompted, enter:
- Alpaca API Key
- Alpaca Secret Key
- Discord Bot Token
- OpenAI API Key
- Anthropic API Key
- NewsAPI Key

### **Step 5: Wait for Deployment**
```
🐳 Building container... (5-10 min)
🚀 Deploying to Cloud Run... (2-3 min)
✅ Deployment Complete!
```

---

## 🎯 That's It!

**Your bot is now running on GCP!**

**Service URL:** `https://options-trading-bot-XXXXX-uc.a.run.app`

**Test it:**
```bash
curl https://your-service-url/health
```

**View logs:**
```bash
gcloud run services logs tail options-trading-bot --region=us-central1
```

**Test Discord:**
```
/status
/help
/quote AAPL
```

---

## 💰 Cost

**~$120-130/month** for always-on bot

---

## 🔄 Update Bot

```bash
# Make changes to code
git add .
git commit -m "Update"

# Redeploy
gcloud builds submit --tag gcr.io/PROJECT_ID/options-trading-bot
gcloud run deploy options-trading-bot --image gcr.io/PROJECT_ID/options-trading-bot --region=us-central1
```

---

## 📊 Monitor

**Cloud Console:**
```
https://console.cloud.google.com/run
```

**Logs:**
```bash
gcloud run services logs read options-trading-bot --region=us-central1 --limit=100
```

---

## 🛑 Stop Bot

```bash
gcloud run services delete options-trading-bot --region=us-central1
```

---

**That's all you need!** 🎉

For detailed guide, see: `GCP_DEPLOYMENT_GUIDE.md`
