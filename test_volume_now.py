#!/usr/bin/env python3
"""Quick test to check volume data in sentiment analysis."""
import asyncio
import sys
from services.alpaca_service import AlpacaService
from services.trading_sentiment_service import TradingSentimentAnalyzer
from services.llm_service import LLMService
from services.news_service import NewsService
from services.claude_service import ClaudeService

async def test_volume():
    print("=" * 80)
    print("Testing Volume Data in Sentiment Analysis")
    print("=" * 80)
    
    # Initialize services
    alpaca = AlpacaService()
    llm = LLMService()
    news = NewsService()
    claude = ClaudeService()
    
    analyzer = TradingSentimentAnalyzer(llm, alpaca, news, claude)
    
    # Test with SPY
    symbol = "SPY"
    print(f"\nTesting {symbol}...")
    
    # Get stock data directly
    stock_data = await analyzer._get_stock_data(symbol)
    
    print(f"\n📊 Stock Data Results:")
    print(f"  Price: ${stock_data.get('price', 0):.2f}")
    print(f"  Volume: {stock_data.get('volume', 0):,}")
    print(f"  Avg Volume: {stock_data.get('avg_volume', 0):,}")
    print(f"  Volume Ratio: {stock_data.get('volume_ratio', 0):.2f}x")
    
    if stock_data.get('volume', 0) == 0:
        print(f"\n❌ PROBLEM: Volume is 0!")
        print(f"  This means get_bars() returned no data")
    else:
        print(f"\n✅ SUCCESS: Volume data is working!")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_volume())
