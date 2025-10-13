#!/usr/bin/env python3
"""Test the intelligent scanner."""
import asyncio
import sys
from agents.data_pipeline_agent import DataPipelineAgent

async def test_scan():
    print("=" * 80)
    print("Testing Intelligent Scanner")
    print("=" * 80)
    
    pipeline = DataPipelineAgent()
    
    # Test with just one symbol for speed
    test_symbols = ["SPY"]
    
    print(f"\nScanning: {test_symbols}")
    print("-" * 80)
    
    try:
        result = await pipeline.scan_opportunities(test_symbols)
        
        print(f"\n✅ Scan completed!")
        print(f"\nResults:")
        print(f"  Symbols Scanned: {result.get('symbols_scanned', 0)}")
        print(f"  Opportunities Found: {len(result.get('opportunities', []))}")
        
        # Check if intelligent scanner was used
        full_result = result.get('full_scan_result', {})
        if full_result:
            print(f"\n🎯 Intelligent Scanner: ACTIVE")
            stats = full_result.get('scan_stats', {})
            print(f"  Movers Detected: {stats.get('movers_detected', 0)}")
            print(f"  Duration: {stats.get('duration_seconds', 0):.1f}s")
            
            # Show opportunities
            opportunities = result.get('opportunities', [])
            if opportunities:
                print(f"\n📊 Opportunities:")
                for opp in opportunities:
                    print(f"\n  Symbol: {opp['symbol']}")
                    print(f"  Action: {opp['action']}")
                    print(f"  Confidence: {opp['confidence']}%")
                    print(f"  Score: {opp['score']:.0f}/100")
                    print(f"  Reasoning: {opp['reasoning'][:100]}...")
        else:
            print(f"\n⚠️  Old scanner still in use (no full_scan_result)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_scan())
