"""
Check actual stock prices from Alpaca
"""
import asyncio
from services.alpaca_service import get_alpaca_service

async def check_prices():
    alpaca = get_alpaca_service()
    
    symbols = ['AAPL', 'PLTR', 'TSLA', 'MSFT', 'SPY']
    
    print("=" * 60)
    print("CHECKING STOCK PRICES FROM ALPACA")
    print("=" * 60)
    
    for symbol in symbols:
        print(f"\n{symbol}:")
        quote = await alpaca.get_latest_quote(symbol)
        if quote:
            print(f"  Price (mid): ${quote['price']:.2f}")
            print(f"  Bid: ${quote['bid']:.2f}")
            print(f"  Ask: ${quote['ask']:.2f}")
            print(f"  Spread: ${quote['spread']:.2f}")
            print(f"  Timestamp: {quote['timestamp']}")
        else:
            print(f"  No quote available")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check_prices())
