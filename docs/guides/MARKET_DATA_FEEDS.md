# 📊 Market Data Feeds - IEX vs SIP

**Understanding Alpaca's market data options**

---

## 🎯 Quick Answer

**Your bot is already using REAL-TIME market data** - it's NOT using paper trading data!

The market data API is **completely separate** from paper/live trading accounts.

---

## 📡 Data Feed Options

### **IEX Feed** (Free) - Currently Active ✅

**What you get:**
- ✅ Real-time stock quotes
- ✅ Real-time price data
- ✅ Bid/Ask spreads
- ⚠️ Volume data (15-minute delayed)
- ⚠️ May have occasional gaps

**Cost:** FREE (included with Alpaca account)

**Good for:**
- Paper trading
- Testing strategies
- Small accounts
- Most retail traders

---

### **SIP Feed** (Premium) - Optional Upgrade

**What you get:**
- ✅ Real-time stock quotes
- ✅ Real-time price data
- ✅ Bid/Ask spreads
- ✅ **Full real-time volume** from all exchanges
- ✅ No gaps or delays
- ✅ Complete market depth

**Cost:** $9/month (Alpaca Market Data Pro subscription)

**Good for:**
- Live trading
- Volume-based strategies
- Day trading
- Professional traders

---

## 🔍 Why Volume Might Look Low

### **Possible Reasons:**

1. **IEX Feed Limitation** (Most likely)
   - IEX volume is delayed 15 minutes
   - May not show full volume during active trading
   - Solution: Upgrade to SIP feed

2. **Market Hours**
   - Pre-market/After-hours has lower volume
   - Weekend = No volume
   - Solution: Check during market hours (9:30 AM - 4:00 PM ET)

3. **Low-Volume Stocks**
   - Some stocks naturally have low volume
   - Small-cap stocks may have gaps
   - Solution: Focus on high-volume stocks (SPY, AAPL, TSLA)

4. **Data Caching**
   - Alpaca may cache data briefly
   - Solution: Wait a few seconds and refresh

---

## 🔧 How to Switch to SIP Feed

### **Step 1: Subscribe to Alpaca Market Data Pro**

1. Go to https://alpaca.markets/
2. Login to your account
3. Go to **Billing** → **Market Data**
4. Subscribe to **Market Data Pro** ($9/month)
5. Wait for activation (usually instant)

### **Step 2: Update Your Bot**

```bash
# Edit .env file
nano .env

# Change this line:
ALPACA_DATA_FEED=iex

# To this:
ALPACA_DATA_FEED=sip

# Save and restart bot
kill <PID>
python main.py
```

### **Step 3: Verify**

```bash
# Check logs
tail -f logs/bot.log | grep "Market data feed"

# Should see:
# Market data feed: SIP (Premium)
```

---

## 📊 Data Feed Comparison

| Feature | IEX (Free) | SIP (Premium) |
|---------|------------|---------------|
| **Price Quotes** | ✅ Real-time | ✅ Real-time |
| **Bid/Ask** | ✅ Real-time | ✅ Real-time |
| **Volume** | ⚠️ 15-min delayed | ✅ Real-time |
| **All Exchanges** | ❌ IEX only | ✅ All exchanges |
| **Market Depth** | ❌ Limited | ✅ Full |
| **Gaps** | ⚠️ Possible | ✅ None |
| **Cost** | FREE | $9/month |

---

## 🧪 Test Your Current Feed

### **Check Volume Data:**

```bash
# In Discord, test with high-volume stock:
/quote SPY

# Check the volume field
# If volume is 0 or very low during market hours = IEX delay
# If volume is accurate = SIP or outside market hours
```

### **Check Logs:**

```bash
tail -f logs/bot.log | grep "Market data"

# You should see:
# Market data feed: IEX (Free)
# Using IEX feed: Volume data may be delayed or incomplete
```

---

## 💡 Recommendations

### **For Paper Trading** (Your current setup)
```
✅ Use IEX (Free)
- Prices are real-time
- Good enough for testing
- Save $9/month
```

### **For Live Trading**
```
⭐ Upgrade to SIP ($9/month)
- Full real-time volume
- Better for volume-based strategies
- More reliable data
- Professional-grade
```

### **For Volume-Based Strategies**
```
⭐ Upgrade to SIP
- Volume is critical
- Need real-time data
- Worth the $9/month
```

---

## 🔄 Current Configuration

**Your bot is configured to:**
```
Trading Mode: PAPER
Data Feed: IEX (Free)
Data Source: Real-time Alpaca market data
Volume: 15-minute delayed
Prices: Real-time ✅
```

**This is NOT paper trading data** - it's real market data from IEX!

---

## ❓ FAQ

### **Q: Is my bot using fake paper trading data?**
**A:** No! Your bot uses REAL market data from Alpaca's IEX feed. The paper/live setting only affects where orders go, not the data source.

### **Q: Why is volume 0 or very low?**
**A:** IEX feed has 15-minute delayed volume. Upgrade to SIP for real-time volume, or check during market hours.

### **Q: Do I need SIP for paper trading?**
**A:** No, IEX is fine for paper trading. Prices are real-time, which is what matters most.

### **Q: Will SIP make my bot better?**
**A:** Only if your strategy uses volume. For price-based strategies, IEX is sufficient.

### **Q: How much does SIP cost?**
**A:** $9/month for Alpaca Market Data Pro subscription.

### **Q: Can I test SIP before paying?**
**A:** Alpaca sometimes offers free trials. Check their website.

---

## 🎯 Summary

**Current Setup:**
- ✅ Real-time market data (NOT paper data!)
- ✅ Real-time prices
- ✅ Real-time bid/ask
- ⚠️ Volume delayed 15 minutes (IEX limitation)

**To Get Real-Time Volume:**
1. Subscribe to Alpaca Market Data Pro ($9/month)
2. Change `ALPACA_DATA_FEED=sip` in `.env`
3. Restart bot

**Recommendation:**
- **Paper trading**: Stay with IEX (free)
- **Live trading**: Upgrade to SIP ($9/month)

---

**Your bot is already using real market data!** 🎉

The volume delay is just an IEX limitation, not a paper trading issue.
