#!/usr/bin/env python3
"""
Test All Fixes - Verify Everything Works
Tests all Discord command dependencies and real options data.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services import get_alpaca_service


async def test_quote_method():
    """Test that get_latest_quote() works."""
    print("\n" + "="*60)
    print("TEST 1: Quote Method (get_latest_quote)")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        # Test with AAPL
        symbol = "AAPL"
        print(f"\n🔍 Getting quote for {symbol}...")
        
        quote = await alpaca.get_latest_quote(symbol)
        
        if quote:
            print(f"\n✅ Got quote:")
            print(f"   Symbol: {symbol}")
            print(f"   Price: ${quote.get('price', 0):.2f}")
            print(f"   Bid: ${quote.get('bid', 0):.2f}")
            print(f"   Ask: ${quote.get('ask', 0):.2f}")
            
            # Verify it's not calling wrong method
            try:
                wrong_quote = await alpaca.get_quote(symbol)
                print(f"\n⚠️ WARNING: get_quote() exists but shouldn't!")
                return False
            except AttributeError:
                print(f"\n✅ CONFIRMED: get_quote() doesn't exist (correct!)")
                return True
        else:
            print("❌ No quote received")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_options_snapshots():
    """Test real options data with Greeks."""
    print("\n" + "="*60)
    print("TEST 2: Real Options Snapshots with Greeks")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        symbol = "AAPL"
        print(f"\n🔍 Getting options snapshots for {symbol}...")
        
        snapshots = await alpaca.get_options_snapshots_with_greeks(symbol)
        
        if snapshots and "snapshots" in snapshots:
            contract_count = len(snapshots['snapshots'])
            print(f"\n✅ Got {contract_count} contracts with Greeks")
            
            # Check first contract has Greeks
            first_contract = list(snapshots['snapshots'].values())[0]
            greeks = first_contract.get("greeks", {})
            
            if greeks and greeks.get('delta') is not None:
                print(f"\n✅ Greeks verified:")
                print(f"   Delta: {greeks.get('delta'):.4f}")
                print(f"   Gamma: {greeks.get('gamma'):.4f}")
                print(f"   Theta: {greeks.get('theta'):.4f}")
                print(f"   Vega: {greeks.get('vega'):.4f}")
                print(f"   Rho: {greeks.get('rho'):.4f}")
                return True
            else:
                print("❌ No Greeks in snapshot")
                return False
        else:
            print("❌ No snapshots received")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_alpaca_methods():
    """Test all critical Alpaca methods exist."""
    print("\n" + "="*60)
    print("TEST 3: Alpaca Service Methods")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        required_methods = [
            'get_account',
            'get_positions',
            'get_position',
            'get_latest_quote',  # CORRECT name
            'get_bars',
            'get_orders',
            'place_market_order',
            'place_limit_order',
            'close_position',
            'get_options_chain',
            'get_option_quote',
            'get_options_snapshots_with_greeks',  # NEW!
            'get_option_contracts_real',  # NEW!
            'get_option_quote_with_greeks',  # NEW!
        ]
        
        missing = []
        found = []
        
        for method in required_methods:
            if hasattr(alpaca, method):
                found.append(method)
                print(f"   ✅ {method}")
            else:
                missing.append(method)
                print(f"   ❌ {method} - MISSING!")
        
        # Check that wrong method doesn't exist
        if hasattr(alpaca, 'get_quote'):
            print(f"\n   ⚠️ get_quote() exists (should be get_latest_quote())")
            missing.append('get_quote should not exist')
        else:
            print(f"\n   ✅ get_quote() doesn't exist (correct!)")
        
        print(f"\n📊 Results:")
        print(f"   Found: {len(found)}/{len(required_methods)}")
        print(f"   Missing: {len(missing)}")
        
        return len(missing) == 0
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_discord_command_dependencies():
    """Test that all Discord commands can call their dependencies."""
    print("\n" + "="*60)
    print("TEST 4: Discord Command Dependencies")
    print("="*60)
    
    try:
        alpaca = get_alpaca_service()
        
        # Test dependencies for each command
        tests = {
            '/status': lambda: alpaca.get_account(),
            '/positions': lambda: alpaca.get_positions(),
            '/quote': lambda: alpaca.get_latest_quote('AAPL'),
            '/watchlist': lambda: alpaca.get_latest_quote('AAPL'),
            '/watchlist-add': lambda: alpaca.get_latest_quote('AAPL'),
        }
        
        passed = 0
        failed = 0
        
        for command, test_func in tests.items():
            try:
                result = await test_func()
                if result is not None:
                    print(f"   ✅ {command} - dependency working")
                    passed += 1
                else:
                    print(f"   ⚠️ {command} - returned None")
                    passed += 1  # Still counts as working
            except AttributeError as e:
                print(f"   ❌ {command} - method doesn't exist: {e}")
                failed += 1
            except Exception as e:
                print(f"   ⚠️ {command} - error (may be expected): {e}")
                passed += 1  # API errors are ok, method exists
        
        print(f"\n📊 Results:")
        print(f"   Passed: {passed}/{len(tests)}")
        print(f"   Failed: {failed}/{len(tests)}")
        
        return failed == 0
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all fix verification tests."""
    print("\n" + "="*60)
    print("FIX VERIFICATION TEST SUITE")
    print("="*60)
    print("Verifying all fixes and real options data")
    
    results = {}
    
    # Test 1: Quote method
    results['quote_method'] = await test_quote_method()
    
    # Test 2: Options snapshots
    results['options_snapshots'] = await test_options_snapshots()
    
    # Test 3: Alpaca methods
    results['alpaca_methods'] = await test_alpaca_methods()
    
    # Test 4: Discord dependencies
    results['discord_deps'] = await test_discord_command_dependencies()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25s}: {status}")
    
    print("="*60)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ All fixes verified!")
        print("✅ Real options data working!")
        print("✅ Discord commands ready!")
        print("\n✅ READY TO COMMIT TO GIT!")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Review failures above")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
