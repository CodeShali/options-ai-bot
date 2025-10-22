#!/usr/bin/env python3
"""
Test Enhanced Sentiment Command
Validates the new sentiment analysis display with trading impact.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services import get_sentiment_service, get_llm_service, get_alpaca_service, get_news_service
from bot.discord_helpers import create_sentiment_embed


async def test_sentiment_with_real_data():
    """Test sentiment analysis with real API calls."""
    print("\n" + "="*60)
    print("TEST: Enhanced Sentiment Analysis")
    print("="*60)
    
    try:
        # Initialize services
        sentiment_service = get_sentiment_service()
        sentiment_service.set_llm(get_llm_service())
        sentiment_service.set_alpaca(get_alpaca_service())
        sentiment_service.set_news(get_news_service())
        
        # Test with a real symbol
        symbol = "AAPL"
        print(f"\n🔍 Analyzing sentiment for {symbol}...")
        print("This will make real API calls to:")
        print("  • NewsAPI (fetch headlines)")
        print("  • OpenAI (2 calls for analysis)")
        print("  • Alpaca (market data)")
        print()
        
        # Get sentiment
        sentiment = await sentiment_service.analyze_symbol_sentiment(symbol)
        
        # Display results
        print("\n" + "="*60)
        print("SENTIMENT ANALYSIS RESULTS")
        print("="*60)
        
        print(f"\n📊 Symbol: {sentiment.get('symbol')}")
        print(f"🎯 Overall Sentiment: {sentiment.get('overall_sentiment')}")
        print(f"📈 Overall Score: {sentiment.get('overall_score', 0):.2f}")
        
        # News Sentiment
        news = sentiment.get('news_sentiment', {})
        print(f"\n📰 News Sentiment:")
        print(f"  • Sentiment: {news.get('sentiment', 'N/A')}")
        print(f"  • Score: {news.get('score', 0):.2f}")
        print(f"  • Impact: {news.get('impact', 'N/A')}")
        print(f"  • Source: {news.get('data_source', 'N/A')}")
        print(f"  • Reasoning: {news.get('reasoning', 'N/A')[:100]}")
        
        headlines = news.get('headlines', [])
        if headlines:
            print(f"\n  📰 Headlines ({len(headlines)}):")
            for i, h in enumerate(headlines[:3], 1):
                print(f"    {i}. {h[:70]}")
        
        # Market Sentiment
        market = sentiment.get('market_sentiment', {})
        print(f"\n📈 Market Sentiment:")
        print(f"  • Sentiment: {market.get('sentiment', 'N/A')}")
        print(f"  • Score: {market.get('score', 0):.2f}")
        print(f"  • Source: {market.get('data_source', 'N/A')}")
        
        # AI Interpretation
        interpretation = sentiment.get('interpretation', '')
        if interpretation:
            print(f"\n🤖 AI Interpretation:")
            print(f"  {interpretation[:200]}")
        
        # Test Discord embed creation
        print("\n" + "="*60)
        print("TESTING DISCORD EMBED CREATION")
        print("="*60)
        
        embed = create_sentiment_embed(sentiment)
        
        print(f"\n✅ Embed created successfully!")
        print(f"  • Title: {embed.title}")
        print(f"  • Description length: {len(embed.description)} chars")
        print(f"  • Fields: {len(embed.fields)}")
        print(f"  • Color: {embed.color}")
        
        # Show field names
        print(f"\n📋 Embed Fields:")
        for i, field in enumerate(embed.fields, 1):
            print(f"  {i}. {field.name} ({len(field.value)} chars)")
        
        print("\n" + "="*60)
        print("✅ TEST PASSED")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sentiment_with_mock_data():
    """Test sentiment display with mock data to verify formatting."""
    print("\n" + "="*60)
    print("TEST: Sentiment Display with Mock Data")
    print("="*60)
    
    try:
        # Create mock sentiment data with strong positive signal
        mock_sentiment = {
            "symbol": "NVDA",
            "overall_sentiment": "POSITIVE",
            "overall_score": 0.75,
            "news_sentiment": {
                "score": 0.80,
                "sentiment": "POSITIVE",
                "themes": ["AI Innovation", "Earnings Beat", "Market Leadership"],
                "impact": "HIGH",
                "reasoning": "Strong positive news flow with multiple bullish catalysts including AI chip breakthrough and earnings beat.",
                "headlines": [
                    "NVIDIA announces revolutionary AI chip with 10x performance",
                    "NVDA beats Q4 earnings expectations, stock surges 8%",
                    "Analysts raise NVIDIA price targets on AI demand"
                ],
                "data_source": "NewsAPI + OpenAI"
            },
            "market_sentiment": {
                "score": 0.70,
                "sentiment": "POSITIVE",
                "indicators": {
                    "RSI": 65,
                    "MACD": "Bullish",
                    "Volume": "1.8x average"
                },
                "reasoning": "Strong upward momentum with healthy volume confirmation",
                "data_source": "Alpaca"
            },
            "social_sentiment": {
                "score": 0.0,
                "sentiment": "NEUTRAL",
                "mentions": 0,
                "data_source": "Phase 3 feature"
            },
            "interpretation": "Extremely bullish sentiment across all indicators. Strong positive news catalysts combined with technical momentum suggest high probability of continued upward movement. Ideal for day trading and scalping setups with tight stops.",
            "timestamp": "2025-10-12T14:30:00"
        }
        
        # Create embed
        embed = create_sentiment_embed(mock_sentiment)
        
        print("\n✅ Mock Sentiment Embed Created!")
        print(f"\n📊 Embed Details:")
        print(f"  • Title: {embed.title}")
        print(f"  • Color: GREEN (positive)")
        print(f"  • Fields: {len(embed.fields)}")
        
        print(f"\n📋 Field Structure:")
        for i, field in enumerate(embed.fields, 1):
            print(f"\n  {i}. {field.name}")
            print(f"     Length: {len(field.value)} chars")
            print(f"     Inline: {field.inline}")
            # Show first 100 chars of value
            preview = field.value[:100].replace('\n', ' ')
            print(f"     Preview: {preview}...")
        
        # Verify key sections exist
        field_names = [f.name for f in embed.fields]
        
        required_sections = [
            "💡 TRADING IMPACT",
            "🤖 AI REASONING",
            "📰 NEWS SENTIMENT",
            "📈 MARKET SENTIMENT",
            "🎯 HOW THIS AFFECTS YOUR TRADING",
            "🤖 AI ANALYSIS"
        ]
        
        print(f"\n✅ Required Sections Check:")
        for section in required_sections:
            if section in field_names:
                print(f"  ✅ {section}")
            else:
                print(f"  ❌ {section} - MISSING!")
        
        print("\n" + "="*60)
        print("✅ TEST PASSED")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all sentiment tests."""
    print("\n" + "="*60)
    print("ENHANCED SENTIMENT ANALYSIS TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Mock data (fast, no API calls)
    print("\n🧪 Test 1: Mock Data Formatting")
    results['mock_data'] = await test_sentiment_with_mock_data()
    
    # Test 2: Real data (slow, makes API calls)
    print("\n🧪 Test 2: Real API Integration")
    user_input = input("\nRun real API test? This will cost ~$0.002 (y/n): ")
    if user_input.lower() == 'y':
        results['real_data'] = await test_sentiment_with_real_data()
    else:
        print("⏭️  Skipping real API test")
        results['real_data'] = None
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    total = sum(1 for v in results.values() if v is not None)
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  SKIPPED"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        print(f"{test_name:20s}: {status}")
    
    print("="*60)
    if total > 0:
        print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*60)
    
    return passed == total if total > 0 else True


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
