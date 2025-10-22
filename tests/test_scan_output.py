#!/usr/bin/env python3
"""Show what the scan output looks like."""
import asyncio
from agents.data_pipeline_agent import DataPipelineAgent

async def show_scan_output():
    print("\n" + "=" * 80)
    print("INTELLIGENT SCANNER - OUTPUT EXAMPLE")
    print("=" * 80 + "\n")
    
    pipeline = DataPipelineAgent()
    
    # Test with a few symbols
    test_symbols = ["SPY", "AAPL", "NVDA"]
    
    print(f"🔍 Scanning: {', '.join(test_symbols)}")
    print("-" * 80)
    
    result = await pipeline.scan_opportunities(test_symbols)
    
    print("\n" + "=" * 80)
    print("SCAN RESULTS")
    print("=" * 80)
    
    # Basic stats
    print(f"\n📊 Statistics:")
    print(f"  Symbols Scanned: {result.get('symbols_scanned', 0)}")
    print(f"  Opportunities Found: {len(result.get('opportunities', []))}")
    
    # Check if intelligent scanner was used
    full_result = result.get('full_scan_result', {})
    if full_result:
        print(f"\n✅ Intelligent Scanner: ACTIVE")
        
        stats = full_result.get('scan_stats', {})
        print(f"\n📈 Detailed Stats:")
        print(f"  Movers Detected: {stats.get('movers_detected', 0)}")
        print(f"  Opportunities Found: {stats.get('opportunities_found', 0)}")
        print(f"  Duration: {stats.get('duration_seconds', 0):.1f}s")
        
        # Show summary
        summary = full_result.get('summary', '')
        if summary:
            print(f"\n📋 Summary:")
            print(summary)
        
        # Show opportunities
        opportunities = result.get('opportunities', [])
        if opportunities:
            print(f"\n🎯 OPPORTUNITIES FOUND:")
            print("=" * 80)
            for i, opp in enumerate(opportunities, 1):
                print(f"\n{i}. {opp['symbol']} - ${opp['current_price']:.2f}")
                print(f"   Action: {opp['action']}")
                print(f"   Confidence: {opp['confidence']}%")
                print(f"   Score: {opp['score']:.0f}/100")
                print(f"   Reasoning: {opp['reasoning'][:200]}...")
                
                # Show detailed recommendation if available
                rec = opp.get('recommendation', {})
                if rec:
                    print(f"\n   📊 Details:")
                    momentum = rec.get('momentum', {})
                    if momentum:
                        print(f"     Momentum: {momentum.get('direction', 'N/A')} {momentum.get('move_pct', 0):+.2f}%")
                        print(f"     Volume: {momentum.get('volume_ratio_5min', 0):.2f}x")
                    
                    technicals = rec.get('technicals', {})
                    if technicals:
                        print(f"     RSI: {technicals.get('rsi', 0):.1f}")
                        print(f"     vs SMA20: {technicals.get('price_vs_sma20', 'N/A')}")
                    
                    if 'entry_strategy' in rec:
                        print(f"\n   💰 Trading Plan:")
                        print(f"     Entry: {rec.get('entry_strategy', 'N/A')}")
                        print(f"     Target: ${rec.get('target_price', 0):.2f}")
                        print(f"     Stop: ${rec.get('stop_loss', 0):.2f}")
                        print(f"     Risk: {rec.get('risk_level', 'N/A')}")
                        print(f"     Position Size: {rec.get('position_size_pct', 0)}%")
        else:
            print(f"\n⏸️  No actionable opportunities at this time")
            print(f"   - Market may be consolidating")
            print(f"   - No strong momentum detected")
            print(f"   - Wait for better setups")
    else:
        print(f"\n⚠️  Old scanner (no intelligent analysis)")
    
    print("\n" + "=" * 80)
    print("END OF SCAN")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(show_scan_output())
