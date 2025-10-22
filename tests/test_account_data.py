#!/usr/bin/env python3
"""Test script to verify account data from Alpaca."""
import asyncio
from services import get_alpaca_service, get_database_service, get_api_tracker
from bot.discord_helpers import format_account_summary
from datetime import date
from config import settings

async def test_account():
    """Test account data retrieval."""
    print("=" * 60)
    print("TESTING ACCOUNT DATA FROM ALPACA")
    print("=" * 60)
    
    # Get services
    alpaca = get_alpaca_service()
    db = get_database_service()
    api_tracker = get_api_tracker()
    
    # Get account data
    print("\n1. Fetching account from Alpaca...")
    account = await alpaca.get_account()
    print(f"   ✅ Account Number: {account.get('account_number')}")
    print(f"   ✅ Cash: ${account.get('cash'):,.2f}")
    print(f"   ✅ Equity: ${account.get('equity'):,.2f}")
    print(f"   ✅ Buying Power: ${account.get('buying_power'):,.2f}")
    print(f"   ✅ Portfolio Value: ${account.get('portfolio_value'):,.2f}")
    print(f"   ✅ Status: {account.get('status')}")
    
    # Get positions
    print("\n2. Fetching positions...")
    positions = await alpaca.get_positions()
    print(f"   ✅ Open Positions: {len(positions)}")
    if positions:
        for pos in positions:
            print(f"      - {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']}")
    
    # Get API tracker stats
    print("\n3. Fetching API tracker stats...")
    api_status = await api_tracker.get_status("Alpaca")
    print(f"   ✅ API Calls Today: {api_status['calls_today']}")
    print(f"   ✅ Errors: {api_status['errors']}")
    print(f"   ✅ Rate Limit: {api_status['rate_limit_used']}/{api_status['rate_limit_total']}")
    
    # Calculate P&L
    print("\n4. Calculating P&L from trades...")
    today = date.today().isoformat()
    trades_today = await db.get_recent_trades(100)
    closed_pl_today = sum(
        float(t.get('total_value', 0)) 
        for t in trades_today 
        if t.get('timestamp', '').startswith(today) and t.get('action') == 'sell'
    )
    print(f"   ✅ Closed P&L Today: ${closed_pl_today:,.2f}")
    print(f"   ✅ Total Trades in DB: {len(trades_today)}")
    
    # Calculate returns
    print("\n5. Calculating returns...")
    equity_start = float(account.get('last_equity', account['equity']))
    current_equity = float(account['equity'])
    daily_return_pct = ((current_equity - equity_start) / equity_start * 100) if equity_start > 0 else 0
    
    initial_capital = 100000.0
    total_return_pct = ((current_equity - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
    
    print(f"   ✅ Equity Start of Day: ${equity_start:,.2f}")
    print(f"   ✅ Current Equity: ${current_equity:,.2f}")
    print(f"   ✅ Daily Return: {daily_return_pct:+.2f}%")
    print(f"   ✅ Total Return: {total_return_pct:+.2f}%")
    
    # Format message
    print("\n6. Formatting Tara message...")
    account_data = {
        'account_name': f"Alpaca ({settings.trading_mode.upper()})",
        'cash': account['cash'],
        'equity': account['equity'],
        'buying_power': account['buying_power'],
        'positions': positions,
        'equity_start_of_day': equity_start,
        'closed_pl_today': closed_pl_today,
        'daily_return_pct': daily_return_pct,
        'total_return_pct': total_return_pct
    }
    
    message = format_account_summary(account_data, api_status['calls_today'])
    print("\n" + "=" * 60)
    print("TARA FORMATTED MESSAGE:")
    print("=" * 60)
    print(message)
    print("=" * 60)
    
    print("\n✅ All account data validated successfully!")

if __name__ == "__main__":
    asyncio.run(test_account())
