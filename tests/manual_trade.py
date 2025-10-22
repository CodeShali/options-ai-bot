#!/usr/bin/env python3
"""
Manual trading script for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import OrchestratorAgent
from services import get_database_service
from utils import setup_logging


async def manual_trade(symbol: str):
    """Execute a manual trade."""
    setup_logging()
    
    print(f"\n🔍 Analyzing {symbol}...")
    
    # Initialize database
    db = get_database_service()
    await db.initialize()
    
    # Create orchestrator
    orchestrator = OrchestratorAgent()
    await orchestrator.start()
    
    try:
        # Execute manual trade
        result = await orchestrator.manual_trade(symbol)
        
        print("\n" + "=" * 60)
        print("TRADE RESULT")
        print("=" * 60)
        
        status = result.get('status')
        
        if status == 'success':
            execution = result['execution']
            analysis = result['analysis']
            
            print(f"✅ Trade executed successfully!")
            print(f"\nSymbol: {execution['symbol']}")
            print(f"Action: {execution['action'].upper()}")
            print(f"Quantity: {execution['quantity']}")
            print(f"Order ID: {execution['order']['id']}")
            
            print(f"\nAI Analysis:")
            print(f"Recommendation: {analysis['recommendation']}")
            print(f"Confidence: {analysis['confidence']}%")
            print(f"Risk Level: {analysis['risk_level']}")
            print(f"Reasoning: {analysis['reasoning'][:200]}...")
            
        elif status == 'not_recommended':
            analysis = result['analysis']
            print(f"⚠️  AI does not recommend buying {symbol}")
            print(f"\nRecommendation: {analysis['recommendation']}")
            print(f"Confidence: {analysis['confidence']}%")
            print(f"Reasoning: {analysis['reasoning']}")
            
        elif status == 'not_approved':
            print(f"❌ Trade not approved")
            print(f"Reason: {result['message']}")
            
        else:
            print(f"❌ Trade failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("=" * 60)
        
    finally:
        await orchestrator.stop()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python manual_trade.py <SYMBOL>")
        print("Example: python manual_trade.py AAPL")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    asyncio.run(manual_trade(symbol))


if __name__ == "__main__":
    main()
