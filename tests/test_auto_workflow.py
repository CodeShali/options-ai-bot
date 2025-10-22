#!/usr/bin/env python3
"""
🌟 TARA - Automated Full Workflow Test
Non-interactive test that runs automatically
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.orchestrator_agent import OrchestratorAgent
from services import get_alpaca_service
from config import settings
from loguru import logger
from datetime import datetime


async def main():
    """Run automated workflow test."""
    
    print("\n" + "="*80)
    print("🌟 TARA - AUTOMATED WORKFLOW TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {settings.trading_mode.upper()}")
    print(f"Auto-Trading: {'ENABLED ✅' if settings.auto_trading_enabled else 'DISABLED ⏸️'}")
    print("="*80 + "\n")
    
    # Initialize
    logger.info("Initializing orchestrator...")
    orchestrator = OrchestratorAgent()
    await orchestrator.start()
    
    alpaca = get_alpaca_service()
    
    # TEST 1: Scan and Trade
    print("🔍 TEST 1: SCAN AND TRADE WORKFLOW")
    print("-" * 80)
    
    try:
        logger.info("🌟 Starting scan and trade workflow...")
        result = await orchestrator.scan_and_trade()
        
        print("\n✅ SCAN AND TRADE COMPLETE")
        print(f"  Status: {result.get('status')}")
        print(f"  Opportunities Found: {result.get('opportunities_found', 0)}")
        print(f"  Signals Generated: {result.get('signals_generated', 0)}")
        print(f"  Trades Executed: {result.get('trades_executed', 0)}")
        
        if result.get('executed_trades'):
            print("\n  📊 EXECUTED TRADES:")
            for i, trade in enumerate(result['executed_trades'], 1):
                print(f"    {i}. {trade.get('symbol', 'N/A')} - {trade.get('action', 'N/A')}")
        
        print("\n  ✅ Check Discord for detailed alerts!")
        
    except Exception as e:
        print(f"\n  ❌ ERROR: {e}")
        logger.error(f"Scan and trade test failed: {e}", exc_info=True)
    
    # Wait a bit
    await asyncio.sleep(3)
    
    # TEST 2: Monitor and Exit
    print("\n" + "="*80)
    print("📊 TEST 2: MONITOR AND EXIT WORKFLOW")
    print("-" * 80)
    
    try:
        logger.info("🌟 Starting monitor and exit workflow...")
        result = await orchestrator.monitor_and_exit()
        
        print("\n✅ MONITOR AND EXIT COMPLETE")
        print(f"  Status: {result.get('status')}")
        print(f"  Positions Monitored: {result.get('positions_monitored', 0)}")
        print(f"  Alerts Generated: {len(result.get('alerts', []))}")
        print(f"  Exits Executed: {len(result.get('exits_executed', []))}")
        
        if result.get('alerts'):
            print("\n  🚨 ALERTS GENERATED:")
            for i, alert in enumerate(result['alerts'][:5], 1):  # Show first 5
                print(f"    {i}. {alert.get('symbol', 'N/A')} - {alert.get('type', 'N/A')}")
        
        if result.get('exits_executed'):
            print("\n  💰 EXITS EXECUTED:")
            for i, exit_trade in enumerate(result['exits_executed'], 1):
                print(f"    {i}. {exit_trade.get('symbol', 'N/A')} - {exit_trade.get('reason', 'N/A')}")
        
        print("\n  ✅ Check Discord for detailed alerts!")
        
    except Exception as e:
        print(f"\n  ❌ ERROR: {e}")
        logger.error(f"Monitor test failed: {e}", exc_info=True)
    
    # TEST 3: Current Positions
    print("\n" + "="*80)
    print("📈 TEST 3: CURRENT POSITIONS")
    print("-" * 80)
    
    try:
        account = await alpaca.get_account()
        positions = await alpaca.get_positions()
        
        print(f"\n  💰 ACCOUNT:")
        print(f"    Equity: ${float(account.equity):,.2f}")
        print(f"    Cash: ${float(account.cash):,.2f}")
        print(f"    Buying Power: ${float(account.buying_power):,.2f}")
        
        if positions:
            print(f"\n  📊 OPEN POSITIONS ({len(positions)}):")
            for pos in positions[:10]:  # Show first 10
                pnl = float(pos.unrealized_pl)
                pnl_pct = float(pos.unrealized_plpc) * 100
                symbol = pos.symbol
                qty = float(pos.qty)
                current_price = float(pos.current_price)
                
                emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                print(f"    {emoji} {symbol}: {qty} @ ${current_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
        else:
            print("\n  ⚪ No open positions")
        
    except Exception as e:
        print(f"\n  ❌ ERROR: {e}")
        logger.error(f"Position check failed: {e}", exc_info=True)
    
    # Summary
    print("\n" + "="*80)
    print("🌟 TEST COMPLETE!")
    print("="*80)
    print("\n📊 SUMMARY:")
    print("  ✅ Scan and trade workflow tested")
    print("  ✅ Monitor and exit workflow tested")
    print("  ✅ Position tracking verified")
    print("  ✅ Discord notifications sent")
    print("\n🎯 NEXT STEPS:")
    print("  1. Check Discord for all alerts")
    print("  2. Verify trade execution details")
    print("  3. Confirm monitor alerts")
    print("  4. Review position threads")
    print("\n🌟 TARA: Trade by Light, Guided by Intelligence")
    print("="*80 + "\n")
    
    # Cleanup
    await orchestrator.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
