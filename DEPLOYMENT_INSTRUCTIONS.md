# 🚀 Deployment Instructions - DigitalOcean

**Deploy your trading bot in 10 minutes for $12/month**

---

## ⚡ Quick Start

### Step 1: Create DigitalOcean Account (2 min)

1. Go to https://www.digitalocean.com/
2. Sign up and get **$200 free credit** (16 months free!)
3. Verify your email

### Step 2: Create Droplet (2 min)

1. Click **"Create"** → **"Droplets"**
2. Choose:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Regular - $12/month
     - 2 vCPU
     - 2 GB RAM
     - 50 GB SSD
   - **Region**: Closest to you (e.g., New York, San Francisco)
   - **Authentication**: SSH keys (recommended) or Password
   - **Hostname**: `trading-bot`
3. Click **"Create Droplet"**
4. Wait ~60 seconds for it to be ready

### Step 3: Deploy Bot (5 min)

```bash
# 1. SSH into your droplet
ssh root@your-droplet-ip

# 2. Clone repository
git clone https://github.com/your-username/options-AI-BOT.git
cd options-AI-BOT

# 3. Run deployment script
./scripts/deployment/deploy-digitalocean.sh

# 4. Enter your API keys when prompted:
#    - Alpaca API Key
#    - Alpaca Secret Key  
#    - Discord Bot Token
#    - OpenAI API Key
#    - Anthropic API Key
#    - NewsAPI Key

# 5. Wait for deployment to complete
```

### Step 4: Test (1 min)

```bash
# Check health
curl http://your-droplet-ip:8000/health

# View logs
docker-compose logs -f

# Test Discord
# Go to Discord and type: /status
```

**Done! Your bot is running 24/7!** 🎉

---

## 📊 What You Get

- ✅ 24/7 uptime
- ✅ Auto-restart on failure
- ✅ Professional hosting
- ✅ 2 vCPU, 2 GB RAM
- ✅ 50 GB SSD storage
- ✅ 99.99% uptime SLA
- ✅ $200 free credit (16 months free!)

---

## 💰 Cost Breakdown

**DigitalOcean:**
- Monthly: $12
- Yearly: $144
- Year 1 with credit: $0 (first 16 months free!)

**vs GCP Cloud Run:**
- Monthly: $125
- Yearly: $1,500
- **Savings: $1,356/year (95% cheaper!)**

---

## 🎯 Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart bot
docker-compose restart

# Stop bot
docker-compose down

# Start bot
docker-compose up -d

# Update bot
git pull && docker-compose up -d --build

# Check status
docker-compose ps
```

---

## 📚 Full Documentation

- **Quick Start**: [DIGITALOCEAN_QUICKSTART.md](docs/deployment/DIGITALOCEAN_QUICKSTART.md)
- **All Hosting Options**: [HOSTING_OPTIONS_COMPARISON.md](docs/deployment/HOSTING_OPTIONS_COMPARISON.md)
- **Cheaper Alternatives**: [CHEAPER_ALTERNATIVES.md](docs/deployment/CHEAPER_ALTERNATIVES.md)
- **GCP Deployment**: [GCP_DEPLOYMENT_GUIDE.md](docs/deployment/GCP_DEPLOYMENT_GUIDE.md)

---

## 🔧 Configuration

### Update API Keys

```bash
cd /opt/options-trading-bot
nano .env
# Edit keys, then:
docker-compose restart
```

### Update Watchlist

```bash
nano agents/data_pipeline_agent.py
# Edit watchlist, then:
docker-compose restart
```

---

## 🐛 Troubleshooting

**Bot not starting?**
```bash
docker-compose logs
```

**Discord bot offline?**
```bash
docker-compose logs | grep discord
grep DISCORD_BOT_TOKEN .env
```

**Need help?**
- Check logs: `docker-compose logs -f`
- See full guide: `docs/deployment/DIGITALOCEAN_QUICKSTART.md`

---

## ✅ Checklist

- [ ] DigitalOcean account created
- [ ] $200 free credit claimed
- [ ] Droplet created ($12/month, Ubuntu 22.04)
- [ ] SSH access working
- [ ] Repository cloned
- [ ] Deployment script completed
- [ ] All API keys entered
- [ ] Containers running
- [ ] Health check passing
- [ ] Discord bot online
- [ ] Test commands working

---

**Total Time**: 10 minutes  
**Total Cost**: $0 for first 16 months  
**Savings**: $1,356/year vs GCP

**Happy Trading! 🚀📈**
