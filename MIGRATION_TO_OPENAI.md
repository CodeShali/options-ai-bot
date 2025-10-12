# Migration from Claude AI to OpenAI

## ✅ Changes Completed

The system has been successfully updated to use **OpenAI GPT-4** instead of Claude AI (Anthropic).

---

## 📝 Files Modified

### Core Service
- **`services/llm_service.py`**
  - Changed from `AsyncAnthropic` to `AsyncOpenAI`
  - Updated model to `gpt-4o` (can also use `gpt-4-turbo` or `gpt-3.5-turbo`)
  - Changed API call format from `messages.create()` to `chat.completions.create()`
  - Added system message role for better context
  - Updated response parsing from `response.content[0].text` to `response.choices[0].message.content`

### Configuration
- **`config/settings.py`**
  - Changed `anthropic_api_key` to `openai_api_key`
  
- **`.env.example`**
  - Changed `ANTHROPIC_API_KEY` to `OPENAI_API_KEY`

### Dependencies
- **`requirements.txt`**
  - Replaced `anthropic==0.25.0` with `openai==1.12.0`

### Testing
- **`scripts/test_connection.py`**
  - Updated `test_anthropic()` to `test_openai()`
  - Changed API test to use OpenAI chat completions format

### Documentation
Updated all references from Claude/Anthropic to OpenAI in:
- `README.md`
- `SETUP_GUIDE.md`
- `PROJECT_OVERVIEW.md`
- `IMPLEMENTATION_SUMMARY.md`
- `ARCHITECTURE.md`
- `quickstart.sh`
- `quickstart.bat`

---

## 🔑 API Key Changes

### Before (Claude AI)
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### After (OpenAI)
```env
OPENAI_API_KEY=sk-...
```

---

## 🚀 How to Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to "API Keys" section
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)
6. Add to your `.env` file

---

## 📊 Model Options

The system is configured to use **GPT-4o** by default, but you can change it in `services/llm_service.py`:

```python
self.model = "gpt-4o"  # Current default (most capable)
# self.model = "gpt-4-turbo"  # Fast and capable
# self.model = "gpt-3.5-turbo"  # Faster and cheaper
```

### Model Comparison

| Model | Speed | Cost | Capability |
|-------|-------|------|------------|
| `gpt-4o` | Fast | Medium | Highest |
| `gpt-4-turbo` | Fast | Medium | High |
| `gpt-3.5-turbo` | Fastest | Lowest | Good |

---

## 🔄 Migration Steps

If you're upgrading from the Claude version:

### 1. Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### 2. Update Environment Variables
```bash
# Edit your .env file
nano .env

# Change:
# ANTHROPIC_API_KEY=sk-ant-...
# To:
# OPENAI_API_KEY=sk-...
```

### 3. Get OpenAI API Key
- Visit https://platform.openai.com/
- Create an API key
- Add to `.env`

### 4. Test Connection
```bash
python scripts/test_connection.py
```

### 5. Start System
```bash
python main.py
```

---

## 🆚 API Differences

### Request Format

**Claude (Before)**
```python
response = await self.client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2000,
    temperature=0.7,
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)
analysis_text = response.content[0].text
```

**OpenAI (After)**
```python
response = await self.client.chat.completions.create(
    model="gpt-4o",
    max_tokens=2000,
    temperature=0.7,
    messages=[
        {
            "role": "system",
            "content": "You are an expert options trading analyst."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
)
analysis_text = response.choices[0].message.content
```

### Key Differences
1. **System Message**: OpenAI supports a separate system message for context
2. **Response Format**: Different response structure
3. **Model Names**: Different model naming conventions
4. **API Client**: Different client library

---

## ✨ Benefits of OpenAI

1. **More Model Options**: GPT-4o, GPT-4-turbo, GPT-3.5-turbo
2. **Flexible Pricing**: Choose speed vs cost
3. **System Messages**: Better context control
4. **Wider Adoption**: More community support
5. **Function Calling**: Advanced features available

---

## 💰 Pricing Comparison

### OpenAI GPT-4o (Recommended)
- Input: $2.50 / 1M tokens
- Output: $10.00 / 1M tokens

### OpenAI GPT-3.5-turbo (Budget Option)
- Input: $0.50 / 1M tokens
- Output: $1.50 / 1M tokens

### Estimated Costs
For typical usage (scanning every 5 minutes, 8 hours/day):
- **GPT-4o**: ~$5-10/month
- **GPT-3.5-turbo**: ~$1-2/month

---

## 🧪 Testing

After migration, test all AI features:

```bash
# Test API connection
python scripts/test_connection.py

# Test manual trade (includes AI analysis)
python scripts/manual_trade.py AAPL

# Start system and monitor
python main.py
```

Check Discord for AI analysis notifications to verify it's working.

---

## 🐛 Troubleshooting

### Error: "Invalid API key"
- Verify your OpenAI API key in `.env`
- Ensure it starts with `sk-`
- Check you have credits in your OpenAI account

### Error: "Module 'openai' not found"
```bash
pip install --upgrade openai
```

### Error: "Rate limit exceeded"
- You've hit OpenAI's rate limit
- Wait a few minutes or upgrade your OpenAI plan
- Consider using GPT-3.5-turbo for higher limits

### AI Analysis Not Working
- Check logs: `tail -f logs/trading.log`
- Verify OpenAI API key is valid
- Test connection: `python scripts/test_connection.py`

---

## 📚 Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenAI Pricing](https://openai.com/pricing)
- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)
- [GPT-4 Guide](https://platform.openai.com/docs/guides/gpt)

---

## ✅ Verification Checklist

After migration, verify:

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] OpenAI API key added to `.env`
- [ ] Connection test passes
- [ ] System starts without errors
- [ ] AI analysis works in manual trades
- [ ] Discord notifications include AI reasoning
- [ ] No errors in logs

---

## 🎉 Migration Complete!

Your system now uses OpenAI GPT-4 for market analysis. The functionality remains the same, but you now have access to OpenAI's powerful models and flexible pricing options.

**Next Steps:**
1. Test the system thoroughly in paper trading mode
2. Monitor AI analysis quality
3. Adjust model if needed (GPT-4o vs GPT-3.5-turbo)
4. Review costs in OpenAI dashboard

---

*Last Updated: 2024-01-XX*
