# Test Scripts

This directory contains all test and utility scripts for the TARA trading system.

## 🧪 Test Scripts

### API Tests
- **test_claude_api.py** - Test Claude/OpenAI API connection
- **test_connection.py** - Test Alpaca API connection
- **check_prices.py** - Check real-time price data

### System Tests
- **test_all_fixes.py** - Test all recent fixes
- **test_all_enhancements.py** - Test system enhancements
- **test_discord_commands.py** - Test Discord bot commands
- **test_enhanced_bot.py** - Test enhanced bot features

### Workflow Tests
- **test_full_workflow.py** - End-to-end trading workflow
- **test_auto_workflow.py** - Automated trading workflow
- **test_intelligent_scan.py** - Scanner functionality

### Component Tests
- **test_account_data.py** - Account data retrieval
- **test_aggressive_mode.py** - Aggressive trading mode
- **test_strategies.py** - Strategy execution
- **test_option_parser.py** - Options data parsing
- **test_real_data.py** - Real market data
- **test_volume_data.py** - Volume analysis

### Utility Scripts
- **manual_trade.py** - Execute manual trades
- **close_all.py** - Close all positions
- **view_positions.py** - View current positions

## 🚀 Running Tests

### Quick Test
```bash
# Test API connections
python tests/test_connection.py

# Test Claude/OpenAI
python tests/test_claude_api.py
```

### Full Test Suite
```bash
# Run all tests
python tests/test_all_fixes.py
```

### Discord Bot Tests
```bash
# Test Discord commands
python tests/test_discord_commands.py
```

### Workflow Tests
```bash
# Test complete workflow
python tests/test_full_workflow.py
```

## 📝 Notes

- All tests require proper `.env` configuration
- Some tests require market hours to be active
- Paper trading mode is recommended for testing
- Check logs in `logs/` directory for detailed output

## ⚠️ Important

Before running tests:
1. Ensure `.env` file is configured
2. System should be running (`python main.py`)
3. Discord bot should be connected
4. API keys should be valid

## 🔧 Troubleshooting

If tests fail:
1. Check `.env` configuration
2. Verify API keys are valid
3. Ensure system is running
4. Check market hours
5. Review logs for errors
