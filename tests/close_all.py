#!/usr/bin/env python3
"""
Close all positions script (emergency use).
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import get_alpaca_service
from utils import setup_logging


async def close_all_positions():
    """Close all open positions."""
    setup_logging()
    
    alpaca = get_alpaca_service()
    
    try:
        # Get positions
        positions = await alpaca.get_positions()
        
        if not positions:
            print("\n📭 No open positions to close")
            return
        
        print(f"\n⚠️  WARNING: About to close {len(positions)} positions:")
        for pos in positions:
            pl = pos['unrealized_pl']
            print(f"   - {pos['symbol']}: {pos['qty']} shares (P/L: ${pl:,.2f})")
        
        # Confirm
        response = input("\nAre you sure you want to close ALL positions? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
        
        print("\n🔄 Closing all positions...")
        
        # Close all
        success = await alpaca.close_all_positions()
        
        if success:
            print("✅ All positions closed successfully")
        else:
            print("❌ Failed to close some positions")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    asyncio.run(close_all_positions())


if __name__ == "__main__":
    main()
