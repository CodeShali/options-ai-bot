#!/usr/bin/env python3
"""
Test Alpaca API to check volume data.
"""
import sys
import asyncio
sys.path.insert(0, '/Users/shashank/Documents/options-AI-BOT')

from services.alpaca_service import AlpacaService
from datetime import datetime, timedelta

async def test_volume_data():
    """Test volume data from Alpaca API."""
    
    print("=" * 80)
    print("Testing Alpaca Volume Data")
    print("=" * 80)
    
    service = AlpacaService()
    
    # Test with high-volume stocks
    test_symbols = ["SPY", "AAPL", "TSLA", "NVDA", "MSFT"]
    
    for symbol in test_symbols:
        print(f"\n{'='*80}")
        print(f"Testing: {symbol}")
        print(f"{'='*80}")
        
        try:
            # Test 1: Get latest quote
            print("\n1. Latest Quote:")
            quote = await service.get_latest_quote(symbol)
            if quote:
                print(f"   Price: ${quote['price']:.2f}")
                print(f"   Bid: ${quote['bid']:.2f}")
                print(f"   Ask: ${quote['ask']:.2f}")
                print(f"   Bid Size: {quote['bid_size']}")
                print(f"   Ask Size: {quote['ask_size']}")
                print(f"   Timestamp: {quote['timestamp']}")
            else:
                print("   ❌ No quote data")
            
            # Test 2: Get bars (last 5 days)
            print("\n2. Recent Bars (5 days):")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            bars = await service.get_bars(
                symbol, 
                timeframe="1Day", 
                limit=5,
                start=start_date,
                end=end_date
            )
            
            if bars:
                print(f"   Found {len(bars)} bars:")
                for i, bar in enumerate(bars[-5:], 1):  # Show last 5
                    print(f"\n   Bar {i}:")
                    print(f"     Date: {bar['timestamp']}")
                    print(f"     Open: ${bar['open']:.2f}")
                    print(f"     High: ${bar['high']:.2f}")
                    print(f"     Low: ${bar['low']:.2f}")
                    print(f"     Close: ${bar['close']:.2f}")
                    print(f"     Volume: {bar['volume']:,}")
                    
                    if bar['volume'] == 0:
                        print(f"     ⚠️  WARNING: Volume is 0!")
                    else:
                        print(f"     ✅ Volume looks good")
            else:
                print("   ❌ No bar data")
            
            # Test 3: Calculate volume metrics
            if bars and len(bars) > 0:
                print("\n3. Volume Metrics:")
                volumes = [bar['volume'] for bar in bars]
                avg_volume = sum(volumes) / len(volumes)
                current_volume = volumes[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                
                print(f"   Average Volume: {avg_volume:,.0f}")
                print(f"   Current Volume: {current_volume:,}")
                print(f"   Volume Ratio: {volume_ratio:.2f}x")
                
                if avg_volume == 0:
                    print(f"   ❌ ERROR: Average volume is 0!")
                elif current_volume == 0:
                    print(f"   ⚠️  WARNING: Current volume is 0!")
                else:
                    print(f"   ✅ Volume metrics look good")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)
    
    # Summary
    print("\n📊 Summary:")
    print("If you see volume = 0, possible reasons:")
    print("1. Market is closed (weekend/holiday)")
    print("2. IEX feed delay (15 minutes)")
    print("3. Stock has very low volume")
    print("4. API issue")
    print("\nCheck the timestamps - if they're old, market is closed.")

if __name__ == "__main__":
    asyncio.run(test_volume_data())
