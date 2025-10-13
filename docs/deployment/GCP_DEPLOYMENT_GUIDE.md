# 🚀 GCP Deployment Guide - Options Trading Bot

**Complete guide to deploy your trading bot to Google Cloud Platform**

---

## 📋 Prerequisites

### **1. GCP Account**
- Active Google Cloud Platform account
- Billing enabled
- Project created

### **2. Local Tools**
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install Docker
# Mac: Download from https://www.docker.com/products/docker-desktop
# Linux: sudo apt-get install docker.io

# Verify installations
gcloud --version
docker --version
```

### **3. API Keys Ready**
- ✅ Alpaca API Key & Secret
- ✅ Discord Bot Token
- ✅ OpenAI API Key
- ✅ Anthropic API Key
- ✅ NewsAPI Key

---

## 🎯 Deployment Options

### **Option 1: Automated Deployment (Recommended)**

**One-command deployment:**
```bash
./deploy-gcp.sh
```

**What it does:**
1. ✅ Enables required GCP APIs
2. ✅ Creates secrets for API keys
3. ✅ Builds Docker container
4. ✅ Deploys to Cloud Run
5. ✅ Configures auto-scaling
6. ✅ Sets up health checks

**Follow the prompts:**
- Enter GCP Project ID
- Enter region (default: us-central1)
- Enter service name (default: options-trading-bot)
- Provide API keys when prompted

---

### **Option 2: Manual Deployment**

#### **Step 1: Setup GCP Project**
```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com
```

#### **Step 2: Create Secrets**
```bash
# Create secrets for API keys
echo -n "YOUR_ALPACA_API_KEY" | gcloud secrets create alpaca-api-key --data-file=-
echo -n "YOUR_ALPACA_SECRET" | gcloud secrets create alpaca-secret-key --data-file=-
echo -n "YOUR_DISCORD_TOKEN" | gcloud secrets create discord-token --data-file=-
echo -n "YOUR_OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=-
echo -n "YOUR_ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "YOUR_NEWS_KEY" | gcloud secrets create news-api-key --data-file=-
```

#### **Step 3: Build Container**
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/options-trading-bot
```

#### **Step 4: Deploy to Cloud Run**
```bash
gcloud run deploy options-trading-bot \
    --image gcr.io/$PROJECT_ID/options-trading-bot \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 1 \
    --min-instances 1 \
    --port 8000 \
    --cpu-throttling=false \
    --set-env-vars TRADING_MODE=paper \
    --set-secrets ALPACA_API_KEY=alpaca-api-key:latest,ALPACA_SECRET_KEY=alpaca-secret-key:latest,DISCORD_TOKEN=discord-token:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,NEWS_API_KEY=news-api-key:latest
```

---

## 🐳 Local Docker Testing

### **Test before deploying:**

```bash
# Build image
docker build -t options-trading-bot .

# Run locally
docker run -d \
    --name trading-bot \
    --env-file .env \
    -p 8000:8000 \
    options-trading-bot

# Check logs
docker logs -f trading-bot

# Test health endpoint
curl http://localhost:8000/health

# Stop container
docker stop trading-bot
docker rm trading-bot
```

### **Using Docker Compose:**
```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 📊 GCP Configuration Details

### **Cloud Run Settings:**

| Setting | Value | Reason |
|---------|-------|--------|
| **Memory** | 2 GiB | Bot needs memory for data processing |
| **CPU** | 2 vCPU | Handles concurrent operations |
| **Timeout** | 3600s (1 hour) | Long-running operations |
| **Min Instances** | 1 | Always running (24/7 bot) |
| **Max Instances** | 1 | Single instance (state management) |
| **CPU Throttling** | Disabled | Continuous operation needed |
| **Port** | 8000 | FastAPI default |

### **Cost Estimate:**

**Cloud Run (Always-on):**
```
CPU: 2 vCPU × 730 hours = $105/month
Memory: 2 GiB × 730 hours = $15/month
Requests: Minimal (health checks)
Total: ~$120-130/month
```

**Cost Optimization:**
- Use preemptible instances for testing
- Scale to 0 during off-hours (if acceptable)
- Use smaller instance for paper trading

---

## 🔐 Security Best Practices

### **1. Use Secret Manager**
✅ All API keys stored in Secret Manager
✅ Never commit secrets to Git
✅ Rotate secrets regularly

### **2. IAM Permissions**
```bash
# Create service account
gcloud iam service-accounts create trading-bot-sa \
    --display-name="Trading Bot Service Account"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:trading-bot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### **3. Network Security**
- Enable VPC if needed
- Use Cloud Armor for DDoS protection
- Restrict API access by IP (optional)

---

## 📈 Monitoring & Logging

### **View Logs:**
```bash
# Real-time logs
gcloud run services logs tail options-trading-bot \
    --region=us-central1

# Recent logs
gcloud run services logs read options-trading-bot \
    --region=us-central1 \
    --limit=100
```

### **Cloud Console:**
```
https://console.cloud.google.com/run
```

### **Set up Alerts:**
```bash
# Create alert for errors
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="Trading Bot Errors" \
    --condition-display-name="Error rate > 5%" \
    --condition-threshold-value=5 \
    --condition-threshold-duration=60s
```

### **Metrics to Monitor:**
- Request latency
- Error rate
- Memory usage
- CPU utilization
- Discord connection status
- Trade execution success rate

---

## 🔄 CI/CD with Cloud Build

### **Automatic Deployment on Git Push:**

**1. Connect Repository:**
```bash
gcloud builds triggers create github \
    --repo-name=options-ai-bot \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

**2. Push to Deploy:**
```bash
git add .
git commit -m "Update bot"
git push origin main
# Automatically builds and deploys!
```

---

## 🧪 Testing Deployment

### **1. Health Check:**
```bash
SERVICE_URL=$(gcloud run services describe options-trading-bot \
    --region=us-central1 \
    --format='value(status.url)')

curl $SERVICE_URL/health
```

**Expected Response:**
```json
{
  "orchestrator": "healthy",
  "data_pipeline": "healthy",
  "strategy": "healthy",
  "risk_manager": "healthy",
  "execution": "healthy",
  "monitor": "healthy"
}
```

### **2. Test Discord Bot:**
```
/status
/help
/quote AAPL
```

### **3. Check Logs:**
```bash
gcloud run services logs read options-trading-bot \
    --region=us-central1 \
    --limit=50
```

---

## 🔧 Troubleshooting

### **Container Won't Start:**
```bash
# Check build logs
gcloud builds list --limit=5

# View specific build
gcloud builds log BUILD_ID

# Check service status
gcloud run services describe options-trading-bot --region=us-central1
```

### **Discord Bot Not Connecting:**
```bash
# Check secrets
gcloud secrets versions access latest --secret=discord-token

# View logs
gcloud run services logs read options-trading-bot --region=us-central1 | grep discord
```

### **High Memory Usage:**
```bash
# Increase memory
gcloud run services update options-trading-bot \
    --memory 4Gi \
    --region=us-central1
```

### **Timeout Issues:**
```bash
# Increase timeout
gcloud run services update options-trading-bot \
    --timeout 7200 \
    --region=us-central1
```

---

## 📦 Update Deployment

### **Deploy New Version:**
```bash
# Rebuild and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/options-trading-bot

gcloud run deploy options-trading-bot \
    --image gcr.io/$PROJECT_ID/options-trading-bot \
    --region=us-central1
```

### **Rollback:**
```bash
# List revisions
gcloud run revisions list --service=options-trading-bot --region=us-central1

# Rollback to previous
gcloud run services update-traffic options-trading-bot \
    --to-revisions=REVISION_NAME=100 \
    --region=us-central1
```

---

## 💰 Cost Management

### **Monitor Costs:**
```bash
# View billing
gcloud billing accounts list

# Set budget alerts
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="Trading Bot Budget" \
    --budget-amount=150USD
```

### **Reduce Costs:**
```bash
# Scale to 0 during off-hours (loses state!)
gcloud run services update options-trading-bot \
    --min-instances=0 \
    --region=us-central1

# Use smaller instance
gcloud run services update options-trading-bot \
    --memory=1Gi \
    --cpu=1 \
    --region=us-central1
```

---

## 🎯 Production Checklist

- [ ] All secrets created in Secret Manager
- [ ] Service account configured with proper permissions
- [ ] Monitoring and alerting set up
- [ ] Budget alerts configured
- [ ] Backup strategy for database
- [ ] CI/CD pipeline configured
- [ ] Health checks passing
- [ ] Discord bot responding
- [ ] Trading in paper mode first
- [ ] Logs reviewed for errors
- [ ] Performance metrics acceptable

---

## 📞 Support

**Issues?**
- Check logs: `gcloud run services logs read options-trading-bot`
- View metrics: Cloud Console → Cloud Run → options-trading-bot
- Test health: `curl SERVICE_URL/health`

**Common Issues:**
1. **Bot not starting:** Check secrets and environment variables
2. **Discord not connecting:** Verify Discord token
3. **High costs:** Review instance configuration
4. **Timeouts:** Increase timeout or optimize code

---

## 🚀 Quick Start Commands

```bash
# Deploy
./deploy-gcp.sh

# View logs
gcloud run services logs tail options-trading-bot --region=us-central1

# Update
gcloud builds submit --tag gcr.io/$PROJECT_ID/options-trading-bot
gcloud run deploy options-trading-bot --image gcr.io/$PROJECT_ID/options-trading-bot --region=us-central1

# Stop (delete service)
gcloud run services delete options-trading-bot --region=us-central1
```

---

**Your trading bot is ready for GCP!** 🎉
