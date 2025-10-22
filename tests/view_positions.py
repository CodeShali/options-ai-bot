#!/usr/bin/env python3
"""
View current positions script.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import get_alpaca_service
from utils import setup_logging


async def view_positions():
    """View all current positions."""
    setup_logging()
    
    print("\n📊 Fetching positions...")
    
    alpaca = get_alpaca_service()
    
    try:
        # Get account info
        account = await alpaca.get_account()
        
        # Get positions
        positions = await alpaca.get_positions()
        
        print("\n" + "=" * 80)
        print("ACCOUNT SUMMARY")
        print("=" * 80)
        print(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        print(f"Cash: ${account['cash']:,.2f}")
        print(f"Buying Power: ${account['buying_power']:,.2f}")
        
        if not positions:
            print("\n📭 No open positions")
        else:
            print(f"\n📈 OPEN POSITIONS ({len(positions)})")
            print("=" * 80)
            
            total_pl = 0
            
            for pos in positions:
                pl = pos['unrealized_pl']
                pl_pct = pos['unrealized_plpc'] * 100
                total_pl += pl
                
                emoji = "🟢" if pl > 0 else "🔴"
                
                print(f"\n{emoji} {pos['symbol']}")
                print(f"   Quantity: {pos['qty']}")
                print(f"   Entry Price: ${pos['avg_entry_price']:.2f}")
                print(f"   Current Price: ${pos['current_price']:.2f}")
                print(f"   Market Value: ${pos['market_value']:,.2f}")
                print(f"   P/L: ${pl:,.2f} ({pl_pct:+.2f}%)")
            
            print("\n" + "=" * 80)
            print(f"Total Unrealized P/L: ${total_pl:,.2f}")
        
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    asyncio.run(view_positions())


if __name__ == "__main__":
    main()
