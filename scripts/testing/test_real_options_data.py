#!/usr/bin/env python3
"""
Test Real Options Data from Alpaca
Verifies that we're getting real Greeks and quotes.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services import get_alpaca_service


async def test_real_options_snapshots():
    """Test getting real options snapshots with Greeks."""
    print("\n" + "="*60)
    print("TEST 1: Real Options Snapshots with Greeks")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        # Test with AAPL
        symbol = "AAPL"
        print(f"\n🔍 Getting options snapshots for {symbol}...")
        
        snapshots = await alpaca.get_options_snapshots_with_greeks(symbol)
        
        if snapshots and "snapshots" in snapshots:
            print(f"\n✅ Got snapshots for {len(snapshots['snapshots'])} contracts")
            
            # Show first 3 contracts with Greeks
            for i, (contract_symbol, data) in enumerate(list(snapshots['snapshots'].items())[:3], 1):
                print(f"\n{i}. {contract_symbol}:")
                
                # Latest quote
                quote = data.get("latestQuote", {})
                if quote:
                    print(f"   Bid: ${quote.get('bp', 0):.2f}")
                    print(f"   Ask: ${quote.get('ap', 0):.2f}")
                
                # Greeks
                greeks = data.get("greeks", {})
                if greeks:
                    print(f"   Greeks:")
                    print(f"     Delta: {greeks.get('delta', 0):.4f}")
                    print(f"     Gamma: {greeks.get('gamma', 0):.4f}")
                    print(f"     Theta: {greeks.get('theta', 0):.4f}")
                    print(f"     Vega: {greeks.get('vega', 0):.4f}")
                    print(f"     Rho: {greeks.get('rho', 0):.4f}")
                else:
                    print(f"   ⚠️ No Greeks available")
                
                # Implied volatility
                iv = data.get("impliedVolatility")
                if iv:
                    print(f"   IV: {iv:.2%}")
            
            return True
        else:
            print("❌ No snapshots data received")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_real_option_contracts():
    """Test getting real option contracts."""
    print("\n" + "="*60)
    print("TEST 2: Real Option Contracts")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        symbol = "AAPL"
        print(f"\n🔍 Getting option contracts for {symbol}...")
        
        from datetime import datetime, timedelta
        today = datetime.now()
        min_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        max_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")
        
        contracts = await alpaca.get_option_contracts_real(
            symbol,
            expiration_date_gte=min_date,
            expiration_date_lte=max_date
        )
        
        if contracts:
            print(f"\n✅ Got {len(contracts)} real contracts")
            
            # Show first 5
            for i, contract in enumerate(contracts[:5], 1):
                print(f"\n{i}. {contract.get('symbol')}:")
                print(f"   Type: {contract.get('type')}")
                print(f"   Strike: ${contract.get('strike_price')}")
                print(f"   Expiration: {contract.get('expiration_date')}")
                print(f"   Status: {contract.get('status')}")
            
            return True
        else:
            print("❌ No contracts received")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_real_option_quote():
    """Test getting real option quote with Greeks."""
    print("\n" + "="*60)
    print("TEST 3: Real Option Quote with Greeks")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        # First get a real contract symbol
        contracts = await alpaca.get_option_contracts_real("AAPL")
        
        if not contracts:
            print("⚠️ No contracts available to test quote")
            return False
        
        # Use first contract
        option_symbol = contracts[0].get("symbol")
        print(f"\n🔍 Getting quote for {option_symbol}...")
        
        quote = await alpaca.get_option_quote_with_greeks(option_symbol)
        
        if quote:
            print(f"\n✅ Got real quote:")
            print(f"   Symbol: {quote.get('symbol')}")
            print(f"   Bid: ${quote.get('bid', 0):.2f}")
            print(f"   Ask: ${quote.get('ask', 0):.2f}")
            print(f"   Data Source: {quote.get('data_source')}")
            
            greeks = quote.get('greeks', {})
            if greeks:
                print(f"\n   Greeks:")
                print(f"     Delta: {greeks.get('delta', 0):.4f}")
                print(f"     Gamma: {greeks.get('gamma', 0):.4f}")
                print(f"     Theta: {greeks.get('theta', 0):.4f}")
                print(f"     Vega: {greeks.get('vega', 0):.4f}")
                print(f"     Rho: {greeks.get('rho', 0):.4f}")
            
            iv = quote.get('implied_volatility')
            if iv:
                print(f"   Implied Volatility: {iv:.2%}")
            
            # Verify it's real data
            if quote.get('data_source') == 'alpaca_real':
                print("\n✅ CONFIRMED: Using REAL Alpaca data!")
                return True
            else:
                print(f"\n⚠️ Data source: {quote.get('data_source')}")
                return False
        else:
            print("❌ No quote received")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all real options data tests."""
    print("\n" + "="*60)
    print("REAL OPTIONS DATA TEST SUITE")
    print("="*60)
    print("Testing Alpaca's real options data with Greeks")
    
    results = {}
    
    # Test 1: Snapshots with Greeks
    results['snapshots'] = await test_real_options_snapshots()
    
    # Test 2: Option contracts
    results['contracts'] = await test_real_option_contracts()
    
    # Test 3: Option quote with Greeks
    results['quote'] = await test_real_option_quote()
    
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
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Real options data with Greeks is working!")
        print("✅ No more mock data!")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Check API credentials and permissions")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
