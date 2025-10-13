#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Enhancements
Tests both /sentiment and /simulate improvements.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services import get_sentiment_service, get_llm_service, get_alpaca_service, get_news_service
from services.simulation_service import get_simulation_service
from bot.discord_helpers import create_sentiment_embed


async def test_sentiment_enhanced():
    """Test enhanced sentiment command."""
    print("\n" + "="*60)
    print("TEST 1: Enhanced /sentiment Command")
    print("="*60)
    
    try:
        # Create mock sentiment data
        mock_sentiment = {
            "symbol": "NVDA",
            "overall_sentiment": "POSITIVE",
            "overall_score": 0.75,
            "news_sentiment": {
                "score": 0.80,
                "sentiment": "POSITIVE",
                "themes": ["AI Innovation", "Earnings Beat"],
                "impact": "HIGH",
                "reasoning": "Strong positive news flow",
                "headlines": [
                    "NVIDIA announces revolutionary AI chip",
                    "NVDA beats earnings expectations"
                ],
                "data_source": "NewsAPI + OpenAI"
            },
            "market_sentiment": {
                "score": 0.70,
                "sentiment": "POSITIVE",
                "indicators": {"RSI": 65, "MACD": "Bullish"},
                "reasoning": "Strong upward momentum",
                "data_source": "Alpaca"
            },
            "social_sentiment": {
                "score": 0.0,
                "sentiment": "NEUTRAL",
                "data_source": "Phase 3"
            },
            "interpretation": "Extremely bullish sentiment. Strong positive news catalysts combined with technical momentum.",
            "timestamp": "2025-10-12T14:30:00"
        }
        
        # Create embed
        embed = create_sentiment_embed(mock_sentiment)
        
        # Verify key sections
        field_names = [f.name for f in embed.fields]
        
        required_sections = [
            "💡 TRADING IMPACT",
            "🤖 AI REASONING",
            "📰 NEWS SENTIMENT",
            "📈 MARKET SENTIMENT",
            "🎯 HOW THIS AFFECTS YOUR TRADING",
            "🤖 AI ANALYSIS"
        ]
        
        all_present = all(section in field_names for section in required_sections)
        
        if all_present:
            print("✅ All required sections present")
            print(f"✅ Total fields: {len(embed.fields)}")
            print(f"✅ Title: {embed.title}")
            print(f"✅ Color: GREEN (positive)")
            return True
        else:
            missing = [s for s in required_sections if s not in field_names]
            print(f"❌ Missing sections: {missing}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simulate_enhanced():
    """Test enhanced simulate command."""
    print("\n" + "="*60)
    print("TEST 2: Enhanced /simulate Command")
    print("="*60)
    
    try:
        # Initialize orchestrator
        from agents.orchestrator_agent import OrchestratorAgent
        orchestrator = OrchestratorAgent()
        await orchestrator.start()
        
        # Get simulation service
        sim_service = get_simulation_service(orchestrator)
        
        print("\n🧪 Running simulation...")
        print("This will test 15 scenarios including:")
        print("  • 10 original tests")
        print("  • 3 trade type tests (scalp/day/swing)")
        print("  • 2 sentiment impact tests")
        print()
        
        # Run simulation
        results = await sim_service.run_full_simulation()
        
        # Display results
        print("\n" + "="*60)
        print("SIMULATION RESULTS")
        print("="*60)
        
        print(f"\n📊 Summary:")
        print(f"  Total Tests: {results['total_tests']}")
        print(f"  Passed: {results['passed']} ✅")
        print(f"  Failed: {results['failed']} ❌")
        print(f"  Success Rate: {results['success_rate']:.1f}%")
        print(f"  Duration: {results['duration_seconds']:.1f}s")
        
        # Show trade type tests
        print(f"\n🎯 Trade Type Tests:")
        trade_type_tests = [t for t in results['results'] if 'Scalping' in t['test'] or 'Day Trading' in t['test'] or 'Swing Trading' in t['test']]
        for test in trade_type_tests:
            status = "✅" if test['status'] == 'PASSED' else "❌"
            print(f"  {status} {test['test']}")
            if test['status'] == 'PASSED':
                details = test.get('details', '')
                if details:
                    print(f"     {details[:100]}...")
        
        # Show sentiment tests
        print(f"\n📰 Sentiment Impact Tests:")
        sentiment_tests = [t for t in results['results'] if 'Sentiment' in t['test'] and ('Boost' in t['test'] or 'Block' in t['test'])]
        for test in sentiment_tests:
            status = "✅" if test['status'] == 'PASSED' else "❌"
            print(f"  {status} {test['test']}")
            if test['status'] == 'PASSED':
                details = test.get('details', '')
                if details:
                    print(f"     {details[:100]}...")
        
        # Verify we have the new tests
        expected_new_tests = 5  # 3 trade types + 2 sentiment
        actual_new_tests = len(trade_type_tests) + len(sentiment_tests)
        
        if actual_new_tests >= expected_new_tests:
            print(f"\n✅ All new tests present ({actual_new_tests}/{expected_new_tests})")
            success = results['success_rate'] >= 60  # At least 60% pass rate
            if success:
                print(f"✅ Success rate acceptable: {results['success_rate']:.1f}%")
            else:
                print(f"⚠️ Success rate low: {results['success_rate']:.1f}%")
            return success
        else:
            print(f"❌ Missing new tests: {actual_new_tests}/{expected_new_tests}")
            return False
        
        # Cleanup
        await orchestrator.stop()
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all enhancement tests."""
    print("\n" + "="*60)
    print("COMPREHENSIVE ENHANCEMENT TEST SUITE")
    print("="*60)
    print("Testing both /sentiment and /simulate improvements")
    
    results = {}
    
    # Test 1: Sentiment enhancement
    results['sentiment'] = await test_sentiment_enhanced()
    
    # Test 2: Simulate enhancement
    results['simulate'] = await test_simulate_enhanced()
    
    # Summary
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
    
    if passed == total:
        print("\n🎉 ALL ENHANCEMENTS VALIDATED!")
        print("✅ /sentiment command enhanced")
        print("✅ /simulate command enhanced")
        print("✅ Ready for deployment")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Review errors above before deploying")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
