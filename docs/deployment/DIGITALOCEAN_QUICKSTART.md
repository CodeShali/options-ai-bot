# 🚀 DigitalOcean Deployment - Quick Start

**Deploy your trading bot to DigitalOcean in 10 minutes for $12/month**

---

## 💰 Why DigitalOcean?

- **Cost**: $12/month (vs $125/month on GCP)
- **Savings**: $1,356/year
- **Free Credit**: $200 (16 months free!)
- **Specs**: 2 vCPU, 2 GB RAM (perfect for your bot)
- **Reliability**: 99.99% uptime SLA
- **Simple**: Deploy in 10 minutes

---

## 📋 Prerequisites

- DigitalOcean account ([Sign up here](https://www.digitalocean.com/) - get $200 credit!)
- Your API keys ready:
  - Alpaca API Key & Secret
  - Discord Bot Token
  - OpenAI API Key
  - Anthropic API Key
  - NewsAPI Key

---

## 🚀 Deployment Steps

### Step 1: Create Droplet (2 minutes)

1. **Sign up for DigitalOcean**
   - Go to https://www.digitalocean.com/
   - Sign up and get **$200 free credit**

2. **Create a Droplet**
   - Click "Create" → "Droplets"
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Regular ($12/month)
     - 2 vCPU
     - 2 GB RAM
     - 50 GB SSD
   - **Region**: Choose closest to you (e.g., New York, San Francisco)
   - **Authentication**: SSH keys (recommended) or Password
   - **Hostname**: `trading-bot`
   - Click "Create Droplet"

3. **Wait for droplet to be ready** (~60 seconds)

---

### Step 2: Connect to Droplet (1 minute)

```bash
# Get your droplet IP from DigitalOcean dashboard
# Then SSH in:

ssh root@your-droplet-ip

# If using password, enter it when prompted
# If using SSH key, you'll connect automatically
```

---

### Step 3: Deploy Bot (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/your-username/options-AI-BOT.git
cd options-AI-BOT

# 2. Run deployment script
./scripts/deployment/deploy-digitalocean.sh

# 3. Follow prompts and enter your API keys when asked:
#    - Alpaca API Key
#    - Alpaca Secret Key
#    - Discord Bot Token
#    - OpenAI API Key
#    - Anthropic API Key
#    - NewsAPI Key

# 4. Wait for deployment to complete (~3-5 minutes)
```

**That's it! Your bot is now running 24/7!** 🎉

---

### Step 4: Verify Deployment (2 minutes)

```bash
# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f

# Test health endpoint
curl http://localhost:8000/health

# Test Discord bot
# Go to Discord and type: /status
```

---

## 🎯 What the Script Does

The deployment script automatically:

1. ✅ Updates system packages
2. ✅ Installs Docker & Docker Compose
3. ✅ Installs Git
4. ✅ Sets up application directory
5. ✅ Configures environment variables
6. ✅ Creates necessary directories
7. ✅ Builds and starts containers
8. ✅ Configures firewall
9. ✅ Sets up auto-restart on reboot
10. ✅ Provides service URLs and commands

---

## 📊 Post-Deployment

### Access Your Bot

**API Endpoint:**
```
http://your-droplet-ip:8000
```

**Health Check:**
```bash
curl http://your-droplet-ip:8000/health
```

**Discord Bot:**
- Bot should be online in your Discord server
- Test with: `/status`, `/help`, `/quote AAPL`

---

### Useful Commands

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
git pull
docker-compose up -d --build

# Check status
docker-compose ps

# View resource usage
docker stats
```

---

## 🔧 Configuration

### Update API Keys

```bash
cd /opt/options-trading-bot
nano .env

# Edit your keys, then restart:
docker-compose restart
```

### Update Watchlist

```bash
nano agents/data_pipeline_agent.py

# Edit watchlist array, then restart:
docker-compose restart
```

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f trading-bot
```

---

## 📈 Monitoring

### Check Bot Status

```bash
# Container status
docker-compose ps

# Resource usage
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

### Discord Monitoring

Use Discord commands:
```
/status              - System status
/account             - Account info
/positions           - Open positions
/performance         - Performance metrics
```

---

## 🔄 Updates

### Update Bot Code

```bash
cd /opt/options-trading-bot
git pull
docker-compose up -d --build
```

### Update Dependencies

```bash
cd /opt/options-trading-bot
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Bot Not Starting

```bash
# Check logs
docker-compose logs

# Check if ports are in use
lsof -i :8000

# Restart Docker
systemctl restart docker
docker-compose up -d
```

### Discord Bot Offline

```bash
# Check logs for Discord errors
docker-compose logs | grep discord

# Verify Discord token
grep DISCORD_BOT_TOKEN .env

# Restart bot
docker-compose restart
```

### Out of Memory

```bash
# Check memory
free -h

# Upgrade droplet to 4GB RAM
# (DigitalOcean dashboard → Resize)
```

### Disk Full

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean logs
docker-compose logs --tail=0
```

---

## 💰 Cost Management

### Current Cost

```
Droplet (2GB):        $12/month
Backups (optional):   $2.40/month
Total:                $12-14.40/month
```

### Using Free Credit

```
$200 credit / $12/month = 16 months FREE!
```

### Reduce Costs

**Option 1: Smaller Droplet ($6/month)**
- 1 vCPU, 1 GB RAM
- May be slower but works

**Option 2: Destroy when not needed**
- Take snapshot ($0.05/GB/month)
- Destroy droplet
- Recreate from snapshot when needed

---

## 🔐 Security

### Firewall

Already configured by deployment script:
- Port 22 (SSH) - Open
- Port 8000 (API) - Open
- All other ports - Closed

### SSH Security

```bash
# Disable password authentication (use SSH keys only)
nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
systemctl restart sshd

# Change SSH port (optional)
nano /etc/ssh/sshd_config
# Set: Port 2222
systemctl restart sshd
ufw allow 2222/tcp
```

### Auto-Updates

```bash
# Enable automatic security updates
apt install unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 📊 Performance

### Expected Performance

- **CPU Usage**: 10-30% average
- **Memory Usage**: 500MB-1GB
- **Disk Usage**: 2-5GB
- **Network**: Minimal (API calls only)

### Optimize Performance

```bash
# Increase swap (if needed)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 🎯 Next Steps

### 1. Test Everything

```bash
# Test health
curl http://your-droplet-ip:8000/health

# Test Discord
/status
/quote AAPL
/sentiment TSLA
```

### 2. Monitor for 24 Hours

```bash
# Watch logs
docker-compose logs -f

# Check for errors
docker-compose logs | grep ERROR
```

### 3. Configure Alerts

Set up DigitalOcean monitoring:
- CPU alerts
- Memory alerts
- Disk alerts

### 4. Set Up Backups

Enable automated backups in DigitalOcean dashboard:
- Weekly backups
- 4 backup slots
- Cost: 20% of droplet price

---

## 📞 Support

### DigitalOcean Support

- Documentation: https://docs.digitalocean.com/
- Community: https://www.digitalocean.com/community
- Tutorials: https://www.digitalocean.com/community/tutorials

### Bot Support

- Check logs: `docker-compose logs`
- GitHub Issues: Open an issue
- Discord: Test with `/help`

---

## ✅ Deployment Checklist

- [ ] DigitalOcean account created
- [ ] $200 free credit claimed
- [ ] Droplet created (Ubuntu 22.04, $12/month)
- [ ] SSH access working
- [ ] Repository cloned
- [ ] Deployment script run successfully
- [ ] API keys configured
- [ ] Containers running
- [ ] Health check passing
- [ ] Discord bot online
- [ ] Test commands working
- [ ] Monitoring set up
- [ ] Backups enabled (optional)

---

## 🎉 Success!

**Your trading bot is now running 24/7 on DigitalOcean!**

**What you get:**
- ✅ 24/7 uptime
- ✅ Auto-restart on failure
- ✅ Professional hosting
- ✅ 95% cheaper than GCP
- ✅ 16 months free with credit

**Total Time:** 10 minutes  
**Total Cost:** $0 for first 16 months (with credit)  
**Savings vs GCP:** $1,356/year

---

**Happy Trading! 🚀📈**
