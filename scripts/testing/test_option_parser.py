#!/usr/bin/env python3
"""
Test option symbol parser with various ticker lengths.
"""
import sys
sys.path.insert(0, '/Users/shashank/Documents/options-AI-BOT')

from services.alpaca_service import AlpacaService
from datetime import datetime

def test_option_parser():
    """Test option symbol parsing with various ticker lengths."""
    
    service = AlpacaService()
    
    # Test cases: (symbol, expected_ticker, expected_date, expected_type, expected_strike)
    test_cases = [
        # 1 character ticker
        ("F251017C00010000", "F", "2025-10-17", "call", 10.0),
        
        # 2 character ticker
        ("GM251017C00045000", "GM", "2025-10-17", "call", 45.0),
        
        # 3 character ticker
        ("AMD251220C00150000", "AMD", "2025-12-20", "call", 150.0),
        
        # 4 character ticker
        ("AAPL251220C00180000", "AAPL", "2025-12-20", "call", 180.0),
        ("OKLO251017C00017500", "OKLO", "2025-10-17", "call", 17.5),  # $17.50 strike
        ("OKLO251017C00175000", "OKLO", "2025-10-17", "call", 175.0),  # $175.00 strike
        ("TSLA251220P00250000", "TSLA", "2025-12-20", "put", 250.0),
        
        # 5 character ticker
        ("GOOGL251220C01500000", "GOOGL", "2025-12-20", "call", 1500.0),
        
        # 6 character ticker (padded)
        ("AAPL  251220C00180000", "AAPL", "2025-12-20", "call", 180.0),
    ]
    
    print("Testing Option Symbol Parser")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for symbol, exp_ticker, exp_date, exp_type, exp_strike in test_cases:
        result = service.parse_option_symbol(symbol)
        
        # Check all fields
        ticker_ok = result["underlying"].strip() == exp_ticker
        date_ok = result["expiration"] == exp_date
        type_ok = result["option_type"] == exp_type
        strike_ok = abs(result["strike"] - exp_strike) < 0.01
        
        all_ok = ticker_ok and date_ok and type_ok and strike_ok
        
        status = "✅ PASS" if all_ok else "❌ FAIL"
        
        print(f"\n{status} | {symbol}")
        print(f"  Expected: {exp_ticker} {exp_date} {exp_type} ${exp_strike}")
        print(f"  Got:      {result['underlying']} {result['expiration']} {result['option_type']} ${result['strike']}")
        
        if not ticker_ok:
            print(f"  ⚠️  Ticker mismatch!")
        if not date_ok:
            print(f"  ⚠️  Date mismatch!")
        if not type_ok:
            print(f"  ⚠️  Type mismatch!")
        if not strike_ok:
            print(f"  ⚠️  Strike mismatch!")
        
        if all_ok:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = test_option_parser()
    sys.exit(0 if success else 1)
