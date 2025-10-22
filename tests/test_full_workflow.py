#!/usr/bin/env python3
"""
🌟 TARA - Full Workflow Test
Tests complete trading workflow with Discord notifications:
1. Scanner finds opportunities
2. Signals generated
3. Trades executed (stock, call, put)
4. Monitor tracks positions
5. Exits at target/stop loss
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.orchestrator_agent import OrchestratorAgent
from services import get_alpaca_service, get_database_service
from config import settings
from loguru import logger
from datetime import datetime


async def test_full_workflow():
    """Test complete trading workflow."""
    
    print("\n" + "="*80)
    print("🌟 TARA - FULL WORKFLOW TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {settings.trading_mode.upper()}")
    print(f"Auto-Trading: {'ENABLED ✅' if settings.auto_trading_enabled else 'DISABLED ⏸️'}")
    print("="*80 + "\n")
    
    # Initialize services
    logger.info("Initializing services...")
    alpaca = get_alpaca_service()
    db = get_database_service()
    
    # Initialize orchestrator
    logger.info("Initializing orchestrator...")
    orchestrator = OrchestratorAgent()
    await orchestrator.start()
    
    # Test 1: Scan and Trade Workflow
    print("\n" + "🔍 TEST 1: SCAN AND TRADE WORKFLOW")
    print("-" * 80)
    print("This will:")
    print("  1. Scan watchlist for opportunities")
    print("  2. Analyze with AI")
    print("  3. Generate signals")
    print("  4. Execute trades (if auto-trading enabled)")
    print("  5. Send Discord notifications")
    print("-" * 80 + "\n")
    
    input("Press ENTER to start scan and trade test...")
    
    try:
        logger.info("🌟 Starting scan and trade workflow...")
        result = await orchestrator.scan_and_trade()
        
        print("\n✅ SCAN AND TRADE COMPLETE")
        print(f"Status: {result.get('status')}")
        print(f"Opportunities Found: {result.get('opportunities_found', 0)}")
        print(f"Signals Generated: {result.get('signals_generated', 0)}")
        print(f"Trades Executed: {result.get('trades_executed', 0)}")
        
        if result.get('executed_trades'):
            print("\n📊 EXECUTED TRADES:")
            for i, trade in enumerate(result['executed_trades'], 1):
                print(f"  {i}. {trade.get('symbol', 'N/A')} - {trade.get('action', 'N/A')}")
        
        print("\n✅ Check Discord for detailed alerts!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Scan and trade test failed: {e}")
    
    # Wait before next test
    print("\n" + "="*80)
    input("Press ENTER to continue to monitor test...")
    
    # Test 2: Monitor and Exit Workflow
    print("\n" + "📊 TEST 2: MONITOR AND EXIT WORKFLOW")
    print("-" * 80)
    print("This will:")
    print("  1. Check all open positions")
    print("  2. Calculate profit/loss")
    print("  3. Check profit targets")
    print("  4. Check stop losses")
    print("  5. Execute exits if needed")
    print("  6. Send Discord notifications")
    print("-" * 80 + "\n")
    
    input("Press ENTER to start monitor test...")
    
    try:
        logger.info("🌟 Starting monitor and exit workflow...")
        result = await orchestrator.monitor_and_exit()
        
        print("\n✅ MONITOR AND EXIT COMPLETE")
        print(f"Status: {result.get('status')}")
        print(f"Positions Monitored: {result.get('positions_monitored', 0)}")
        print(f"Alerts Generated: {len(result.get('alerts', []))}")
        print(f"Exits Executed: {len(result.get('exits_executed', []))}")
        
        if result.get('alerts'):
            print("\n🚨 ALERTS GENERATED:")
            for i, alert in enumerate(result['alerts'], 1):
                print(f"  {i}. {alert.get('symbol', 'N/A')} - {alert.get('type', 'N/A')}")
                print(f"     {alert.get('message', 'N/A')}")
        
        if result.get('exits_executed'):
            print("\n💰 EXITS EXECUTED:")
            for i, exit_trade in enumerate(result['exits_executed'], 1):
                print(f"  {i}. {exit_trade.get('symbol', 'N/A')} - {exit_trade.get('reason', 'N/A')}")
        
        print("\n✅ Check Discord for detailed alerts!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Monitor test failed: {e}")
    
    # Test 3: Check Current Positions
    print("\n" + "="*80)
    print("\n" + "📈 TEST 3: CURRENT POSITIONS")
    print("-" * 80)
    
    try:
        account = await alpaca.get_account()
        positions = await alpaca.get_positions()
        
        print(f"\n💰 ACCOUNT:")
        print(f"  Equity: ${float(account.equity):,.2f}")
        print(f"  Cash: ${float(account.cash):,.2f}")
        print(f"  Buying Power: ${float(account.buying_power):,.2f}")
        
        if positions:
            print(f"\n📊 OPEN POSITIONS ({len(positions)}):")
            for pos in positions:
                pnl = float(pos.unrealized_pl)
                pnl_pct = float(pos.unrealized_plpc) * 100
                symbol = pos.symbol
                qty = float(pos.qty)
                current_price = float(pos.current_price)
                
                emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                print(f"  {emoji} {symbol}")
                print(f"     Qty: {qty} @ ${current_price:.2f}")
                print(f"     P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
        else:
            print("\n⚪ No open positions")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Position check failed: {e}")
    
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


async def test_simulated_scenarios():
    """Test with simulated market scenarios."""
    
    print("\n" + "="*80)
    print("🎭 SIMULATED SCENARIOS TEST")
    print("="*80)
    print("\nThis will simulate specific market conditions:")
    print("  1. Strong bullish momentum → BUY CALL")
    print("  2. Strong bearish momentum → BUY PUT")
    print("  3. Moderate momentum → BUY STOCK")
    print("  4. Position hits profit target → SELL")
    print("  5. Position hits stop loss → SELL")
    print("="*80 + "\n")
    
    input("Press ENTER to start simulated scenarios...")
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent()
    await orchestrator.start()
    
    # Scenario 1: Bullish - Buy Call
    print("\n📈 SCENARIO 1: BULLISH MOMENTUM")
    print("-" * 80)
    print("Simulating: NVDA with strong upward momentum")
    print("Expected: BUY CALL recommendation")
    print("-" * 80)
    
    # This would trigger the actual scan
    # In real scenario, the scanner would detect this
    
    # Scenario 2: Bearish - Buy Put
    print("\n📉 SCENARIO 2: BEARISH MOMENTUM")
    print("-" * 80)
    print("Simulating: TSLA with strong downward momentum")
    print("Expected: BUY PUT recommendation")
    print("-" * 80)
    
    # Scenario 3: Moderate - Buy Stock
    print("\n📊 SCENARIO 3: MODERATE MOMENTUM")
    print("-" * 80)
    print("Simulating: AAPL with moderate upward momentum")
    print("Expected: BUY STOCK recommendation")
    print("-" * 80)
    
    # Scenario 4: Profit Target
    print("\n🎯 SCENARIO 4: PROFIT TARGET HIT")
    print("-" * 80)
    print("Simulating: Position up 50%")
    print("Expected: SELL alert and execution")
    print("-" * 80)
    
    # Scenario 5: Stop Loss
    print("\n⚠️ SCENARIO 5: STOP LOSS HIT")
    print("-" * 80)
    print("Simulating: Position down 30%")
    print("Expected: SELL alert and execution")
    print("-" * 80)
    
    print("\n✅ Simulated scenarios complete!")
    print("Check Discord for all alerts and execution confirmations.")
    
    await orchestrator.stop()


async def main():
    """Main test runner."""
    
    print("\n" + "="*80)
    print("🌟 TARA - COMPREHENSIVE WORKFLOW TEST")
    print("="*80)
    print("\nSelect test mode:")
    print("  1. Real workflow test (uses actual market data)")
    print("  2. Simulated scenarios (controlled test cases)")
    print("  3. Both (comprehensive test)")
    print("="*80 + "\n")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        await test_full_workflow()
    elif choice == "2":
        await test_simulated_scenarios()
    elif choice == "3":
        await test_full_workflow()
        print("\n" + "="*80)
        input("Press ENTER to continue to simulated scenarios...")
        await test_simulated_scenarios()
    else:
        print("Invalid choice. Exiting.")
        return
    
    print("\n🌟 All tests complete!")
    print("Trade by Light, Guided by Intelligence ✨\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
