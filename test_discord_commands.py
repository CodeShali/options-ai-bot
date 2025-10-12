#!/usr/bin/env python3
"""
Comprehensive Discord Bot Command Tester
Tests all Discord commands and flows to ensure they work properly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services import (
    get_alpaca_service,
    get_database_service,
    get_sentiment_service,
    get_news_service
)
from config import settings


async def test_status_command():
    """Test the /status command flow"""
    print("\n" + "="*60)
    print("TEST: /status command")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        db = get_database_service()
        
        # Get account
        account = await alpaca.get_account()
        print(f"✅ Account retrieved: ${float(account.get('equity', 0)):,.2f}")
        
        # Get positions
        positions = await alpaca.get_positions()
        print(f"✅ Positions retrieved: {len(positions)} positions")
        
        # Get performance metrics
        metrics = await db.get_performance_metrics(30)
        print(f"✅ Performance metrics: {metrics}")
        
        # Calculate today's P/L
        today_trades = await db.get_recent_trades(100)
        from datetime import datetime
        today = datetime.now().date()
        today_pl = sum(
            float(t.get('profit_loss', 0)) 
            for t in today_trades 
            if datetime.fromisoformat(t.get('timestamp', '')).date() == today
        )
        print(f"✅ Today's P/L: ${today_pl:.2f}")
        
        print("✅ /status command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /status command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_positions_command():
    """Test the /positions command flow"""
    print("\n" + "="*60)
    print("TEST: /positions command")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        # Get positions
        positions = await alpaca.get_positions()
        print(f"✅ Retrieved {len(positions)} positions")
        
        for pos in positions[:3]:  # Show first 3
            symbol = pos.get('symbol', 'N/A')
            qty = pos.get('qty', 0)
            unrealized_pl = float(pos.get('unrealized_pl', 0))
            print(f"  - {symbol}: {qty} shares, P/L: ${unrealized_pl:.2f}")
        
        print("✅ /positions command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /positions command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sentiment_command():
    """Test the /sentiment command flow"""
    print("\n" + "="*60)
    print("TEST: /sentiment command")
    print("="*60)
    
    try:
        sentiment_service = get_sentiment_service()
        
        # Test with AAPL
        symbol = "AAPL"
        print(f"Testing sentiment for {symbol}...")
        
        sentiment_data = await sentiment_service.analyze_symbol_sentiment(symbol)
        
        print(f"✅ Overall sentiment: {sentiment_data.get('overall_sentiment', 'N/A')}")
        print(f"✅ Overall score: {sentiment_data.get('overall_score', 0):.2f}")
        print(f"✅ News sentiment: {sentiment_data.get('news_sentiment', 'N/A')}")
        print(f"✅ Market sentiment: {sentiment_data.get('market_sentiment', 'N/A')}")
        
        print("✅ /sentiment command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /sentiment command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_status_command():
    """Test the /api-status command flow"""
    print("\n" + "="*60)
    print("TEST: /api-status command")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        news_service = get_news_service()
        
        # Test Alpaca connection
        try:
            account = await alpaca.get_account()
            alpaca_status = "✅ Connected"
            print(f"Alpaca: {alpaca_status}")
        except Exception as e:
            alpaca_status = f"❌ Error: {e}"
            print(f"Alpaca: {alpaca_status}")
        
        # Test NewsAPI connection
        try:
            news = await news_service.get_news("AAPL", max_articles=1)
            news_status = f"✅ Connected ({len(news)} articles)"
            print(f"NewsAPI: {news_status}")
        except Exception as e:
            news_status = f"❌ Error: {e}"
            print(f"NewsAPI: {news_status}")
        
        # Show settings
        print(f"\nTrading Mode: {settings.trading_mode}")
        print(f"Scan Interval: {settings.scan_interval}s")
        print(f"Max Position Size: ${settings.max_position_size:,.2f}")
        print(f"Max Daily Loss: ${settings.max_daily_loss:,.2f}")
        
        print("✅ /api-status command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /api-status command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_aggressive_mode_command():
    """Test the /aggressive-mode command flow"""
    print("\n" + "="*60)
    print("TEST: /aggressive-mode command")
    print("="*60)
    
    try:
        from config import enable_aggressive_mode, disable_aggressive_mode
        
        # Test enabling aggressive mode
        print("Testing aggressive mode enable...")
        original_interval = settings.scan_interval
        
        enable_aggressive_mode()
        print(f"✅ Aggressive mode enabled")
        print(f"  Scan interval: {settings.scan_interval}s")
        print(f"  Max position size: ${settings.max_position_size:,.2f}")
        print(f"  Max daily loss: ${settings.max_daily_loss:,.2f}")
        
        # Test disabling aggressive mode
        print("\nTesting aggressive mode disable...")
        disable_aggressive_mode()
        print(f"✅ Aggressive mode disabled")
        print(f"  Scan interval: {settings.scan_interval}s")
        print(f"  Max position size: ${settings.max_position_size:,.2f}")
        print(f"  Max daily loss: ${settings.max_daily_loss:,.2f}")
        
        print("✅ /aggressive-mode command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /aggressive-mode command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_circuit_breaker_command():
    """Test the /circuit-breaker-set command flow"""
    print("\n" + "="*60)
    print("TEST: /circuit-breaker-set command")
    print("="*60)
    
    try:
        original_loss = settings.max_daily_loss
        
        # Test setting circuit breaker
        new_loss = 500.0
        settings.max_daily_loss = new_loss
        print(f"✅ Circuit breaker set to ${new_loss:,.2f}")
        
        # Restore original
        settings.max_daily_loss = original_loss
        print(f"✅ Circuit breaker restored to ${original_loss:,.2f}")
        
        print("✅ /circuit-breaker-set command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /circuit-breaker-set command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_trades_command():
    """Test the /trades command flow"""
    print("\n" + "="*60)
    print("TEST: /trades command")
    print("="*60)
    
    try:
        db = get_database_service()
        
        # Get recent trades
        trades = await db.get_recent_trades(10)
        print(f"✅ Retrieved {len(trades)} recent trades")
        
        for trade in trades[:3]:  # Show first 3
            symbol = trade.get('symbol', 'N/A')
            action = trade.get('action', 'N/A')
            pl = float(trade.get('profit_loss', 0))
            print(f"  - {symbol} {action}: P/L ${pl:.2f}")
        
        print("✅ /trades command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /trades command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance_command():
    """Test the /performance command flow"""
    print("\n" + "="*60)
    print("TEST: /performance command")
    print("="*60)
    
    try:
        db = get_database_service()
        
        # Get performance metrics
        metrics = await db.get_performance_metrics(30)
        print(f"✅ Performance metrics retrieved")
        print(f"  Total trades: {metrics.get('total_trades', 0)}")
        print(f"  Win rate: {metrics.get('win_rate', 0):.1f}%")
        print(f"  Total P/L: ${metrics.get('total_profit_loss', 0):.2f}")
        print(f"  Avg profit: ${metrics.get('avg_profit', 0):.2f}")
        print(f"  Avg loss: ${metrics.get('avg_loss', 0):.2f}")
        
        print("✅ /performance command: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ /performance command: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("DISCORD BOT COMMAND TEST SUITE")
    print("="*60)
    print(f"Testing all Discord commands and flows...")
    
    results = {}
    
    # Run all tests
    results['status'] = await test_status_command()
    results['positions'] = await test_positions_command()
    results['sentiment'] = await test_sentiment_command()
    results['api_status'] = await test_api_status_command()
    results['aggressive_mode'] = await test_aggressive_mode_command()
    results['circuit_breaker'] = await test_circuit_breaker_command()
    results['trades'] = await test_trades_command()
    results['performance'] = await test_performance_command()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:20s}: {status}")
    
    print("="*60)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
