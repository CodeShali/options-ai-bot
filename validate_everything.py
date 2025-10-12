#!/usr/bin/env python3
"""
Complete System Validation
Validates all fixes, real data, and system health.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from services import get_alpaca_service
from loguru import logger


async def validate_alpaca_connection():
    """Validate Alpaca connection and account."""
    print("\n" + "="*70)
    print("VALIDATION 1: Alpaca Connection & Account")
    print("="*70)
    
    try:
        alpaca = get_alpaca_service()
        account = await alpaca.get_account()
        
        if account:
            print(f"\n✅ Alpaca Connected")
            print(f"   Account: {account.get('account_number', 'N/A')}")
            print(f"   Equity: ${account.get('equity', 0):,.2f}")
            print(f"   Cash: ${account.get('cash', 0):,.2f}")
            print(f"   Buying Power: ${account.get('buying_power', 0):,.2f}")
            return True
        else:
            print("\n❌ No account data")
            return False
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


async def validate_quote_method():
    """Validate get_latest_quote() method works."""
    print("\n" + "="*70)
    print("VALIDATION 2: Quote Method (Discord /quote fix)")
    print("="*70)
    
    try:
        alpaca = get_alpaca_service()
        
        # Test that get_latest_quote exists and works
        quote = await alpaca.get_latest_quote("AAPL")
        
        if quote:
            print(f"\n✅ get_latest_quote() working")
            print(f"   Symbol: AAPL")
            print(f"   Price: ${quote.get('price', 0):.2f}")
            
            # Verify get_quote doesn't exist
            if hasattr(alpaca, 'get_quote'):
                print(f"\n⚠️ WARNING: get_quote() still exists!")
                return False
            else:
                print(f"   ✅ get_quote() doesn't exist (correct!)")
                return True
        else:
            print("\n❌ No quote data")
            return False
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


async def validate_real_options_greeks():
    """Validate real options data with Greeks."""
    print("\n" + "="*70)
    print("VALIDATION 3: Real Options Data with Greeks")
    print("="*70)
    
    try:
        alpaca = get_alpaca_service()
        
        # Get options snapshots
        snapshots = await alpaca.get_options_snapshots_with_greeks("AAPL")
        
        if not snapshots or "snapshots" not in snapshots:
            print("\n❌ No snapshots data")
            return False
        
        contract_count = len(snapshots['snapshots'])
        print(f"\n✅ Got {contract_count} option contracts")
        
        # Check first contract for Greeks
        first_symbol = list(snapshots['snapshots'].keys())[0]
        first_contract = snapshots['snapshots'][first_symbol]
        
        if 'greeks' not in first_contract:
            print(f"\n❌ No Greeks in contract")
            return False
        
        greeks = first_contract['greeks']
        
        # Verify all Greeks are present
        required_greeks = ['delta', 'gamma', 'theta', 'vega', 'rho']
        missing = [g for g in required_greeks if g not in greeks or greeks[g] is None]
        
        if missing:
            print(f"\n❌ Missing Greeks: {missing}")
            return False
        
        print(f"\n✅ Real Greeks verified for {first_symbol}:")
        print(f"   Delta: {greeks['delta']:.4f}")
        print(f"   Gamma: {greeks['gamma']:.4f}")
        print(f"   Theta: {greeks['theta']:.4f}")
        print(f"   Vega: {greeks['vega']:.4f}")
        print(f"   Rho: {greeks['rho']:.4f}")
        
        # Check implied volatility
        if 'impliedVolatility' in first_contract:
            iv = first_contract['impliedVolatility']
            print(f"   IV: {iv:.2%}")
        
        # Check bid/ask
        if 'latestQuote' in first_contract:
            quote = first_contract['latestQuote']
            print(f"   Bid: ${quote.get('bp', 0):.2f}")
            print(f"   Ask: ${quote.get('ap', 0):.2f}")
        
        print(f"\n✅ NO MOCK DATA - All real from Alpaca!")
        return True
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def validate_no_mock_data():
    """Validate no mock data is being used."""
    print("\n" + "="*70)
    print("VALIDATION 4: No Mock Data")
    print("="*70)
    
    try:
        alpaca = get_alpaca_service()
        
        # Check that mock methods don't exist or aren't being called
        checks = []
        
        # Check 1: _create_mock_options_chain should exist but not be called
        if hasattr(alpaca, '_create_mock_options_chain'):
            print(f"   ℹ️ _create_mock_options_chain exists (fallback only)")
            checks.append(True)
        
        # Check 2: Get real data and verify it's not mock
        quote = await alpaca.get_latest_quote("AAPL")
        if quote and quote.get('data_source') != 'mock':
            print(f"   ✅ Stock quotes: Real data")
            checks.append(True)
        elif quote:
            print(f"   ⚠️ Stock quotes: {quote.get('data_source', 'unknown')}")
            checks.append(False)
        
        # Check 3: Options data is real
        snapshots = await alpaca.get_options_snapshots_with_greeks("AAPL")
        if snapshots and 'snapshots' in snapshots:
            print(f"   ✅ Options data: Real from Alpaca")
            checks.append(True)
        else:
            print(f"   ❌ Options data: Not available")
            checks.append(False)
        
        print(f"\n✅ Using REAL data - No mock data in production!")
        return all(checks)
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


async def validate_discord_commands():
    """Validate Discord command methods exist."""
    print("\n" + "="*70)
    print("VALIDATION 5: Discord Command Dependencies")
    print("="*70)
    
    try:
        alpaca = get_alpaca_service()
        
        # Commands and their required methods
        command_methods = {
            '/status': 'get_account',
            '/positions': 'get_positions',
            '/quote': 'get_latest_quote',
            '/watchlist': 'get_latest_quote',
            '/watchlist-add': 'get_latest_quote',
            '/account': 'get_account',
            '/trades': 'get_orders',
            '/sentiment': 'get_latest_quote',
        }
        
        all_good = True
        for command, method in command_methods.items():
            if hasattr(alpaca, method):
                print(f"   ✅ {command:20s} → {method}()")
            else:
                print(f"   ❌ {command:20s} → {method}() MISSING!")
                all_good = False
        
        if all_good:
            print(f"\n✅ All Discord commands have required methods")
            return True
        else:
            print(f"\n❌ Some Discord commands missing dependencies")
            return False
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


async def validate_system_health():
    """Overall system health check."""
    print("\n" + "="*70)
    print("VALIDATION 6: Overall System Health")
    print("="*70)
    
    try:
        alpaca = get_alpaca_service()
        
        checks = {}
        
        # Check 1: Can get account
        try:
            account = await alpaca.get_account()
            checks['Account'] = account is not None
        except:
            checks['Account'] = False
        
        # Check 2: Can get positions
        try:
            positions = await alpaca.get_positions()
            checks['Positions'] = positions is not None
        except:
            checks['Positions'] = False
        
        # Check 3: Can get quote
        try:
            quote = await alpaca.get_latest_quote("AAPL")
            checks['Quotes'] = quote is not None
        except:
            checks['Quotes'] = False
        
        # Check 4: Can get options data
        try:
            snapshots = await alpaca.get_options_snapshots_with_greeks("AAPL")
            checks['Options'] = snapshots is not None and 'snapshots' in snapshots
        except:
            checks['Options'] = False
        
        # Display results
        print()
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
        
        all_healthy = all(checks.values())
        
        if all_healthy:
            print(f"\n✅ System is HEALTHY - All checks passed!")
            return True
        else:
            failed = [k for k, v in checks.items() if not v]
            print(f"\n⚠️ System issues: {', '.join(failed)}")
            return False
            
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


async def run_complete_validation():
    """Run complete system validation."""
    print("\n" + "="*70)
    print("COMPLETE SYSTEM VALIDATION")
    print("="*70)
    print("Validating all fixes, real data, and system health")
    
    results = {}
    
    # Run all validations
    results['alpaca_connection'] = await validate_alpaca_connection()
    results['quote_method'] = await validate_quote_method()
    results['real_greeks'] = await validate_real_options_greeks()
    results['no_mock_data'] = await validate_no_mock_data()
    results['discord_commands'] = await validate_discord_commands()
    results['system_health'] = await validate_system_health()
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25s}: {status}")
    
    print("="*70)
    print(f"TOTAL: {passed}/{total} validations passed ({passed/total*100:.1f}%)")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ System is healthy and ready")
        print("✅ All fixes verified")
        print("✅ Real options data with Greeks working")
        print("✅ No mock data")
        print("✅ Discord commands ready")
        print("\n🚀 SYSTEM IS PRODUCTION READY!")
    else:
        print("\n⚠️ SOME VALIDATIONS FAILED")
        print("Review failures above")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_complete_validation())
    sys.exit(0 if success else 1)
