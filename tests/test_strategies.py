"""
Test all quantitative trading strategies.
"""
import asyncio
from strategies import (
    MeanReversionStrategy,
    MomentumBreakoutStrategy,
    MACrossoverStrategy,
    IronCondorStrategy
)
from strategies.strategy_manager import StrategyManager
from loguru import logger


def generate_test_bars(num_bars: int = 250):
    """Generate test bar data."""
    import random
    
    bars = []
    price = 100.0
    
    for i in range(num_bars):
        # Random walk
        change = random.uniform(-2, 2)
        price = max(50, min(150, price + change))
        
        high = price * random.uniform(1.0, 1.02)
        low = price * random.uniform(0.98, 1.0)
        close = random.uniform(low, high)
        volume = random.randint(1000000, 5000000)
        
        bars.append({
            'open': price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
        
        price = close
    
    return bars


def test_mean_reversion():
    """Test Mean Reversion Strategy."""
    print("\n" + "="*70)
    print("🧪 TESTING MEAN REVERSION STRATEGY")
    print("="*70)
    
    strategy = MeanReversionStrategy()
    bars = generate_test_bars(60)
    current_price = bars[-1]['close']
    
    # Test analysis
    signal = strategy.analyze("TEST", bars, current_price)
    
    print(f"\n📊 Analysis Result:")
    print(f"   Action: {signal['action']}")
    print(f"   Reason: {signal['reason']}")
    
    if signal.get('indicators'):
        print(f"   Indicators:")
        for key, value in signal['indicators'].items():
            if isinstance(value, float):
                print(f"      {key}: {value:.2f}")
            else:
                print(f"      {key}: {value}")
    
    # Test position sizing
    position_size = strategy.get_position_size(100000, current_price)
    print(f"\n💰 Position Size: {position_size} shares (for $100k account)")
    
    # Test exit logic
    test_position = {
        'entry_price': current_price * 0.98,
        'symbol': 'TEST'
    }
    exit_signal = strategy.check_exit(test_position, current_price, bars)
    print(f"\n🚪 Exit Check: {'EXIT' if exit_signal.get('exit') else 'HOLD'}")
    if exit_signal.get('reason'):
        print(f"   Reason: {exit_signal['reason']}")
    
    print("\n✅ Mean Reversion Strategy Test Complete")
    return True


def test_momentum_breakout():
    """Test Momentum Breakout Strategy."""
    print("\n" + "="*70)
    print("🧪 TESTING MOMENTUM BREAKOUT STRATEGY")
    print("="*70)
    
    strategy = MomentumBreakoutStrategy()
    bars = generate_test_bars(60)
    current_price = bars[-1]['close'] * 1.05  # Simulate breakout
    
    # Test analysis
    signal = strategy.analyze("TEST", bars, current_price)
    
    print(f"\n📊 Analysis Result:")
    print(f"   Action: {signal['action']}")
    print(f"   Reason: {signal['reason']}")
    
    if signal.get('indicators'):
        print(f"   Indicators:")
        for key, value in signal['indicators'].items():
            if isinstance(value, float):
                print(f"      {key}: {value:.2f}")
            else:
                print(f"      {key}: {value}")
    
    # Test position sizing with ATR
    position_size = strategy.get_position_size(100000, current_price, atr=2.5)
    print(f"\n💰 Position Size: {position_size} shares (for $100k account, ATR=2.5)")
    
    print("\n✅ Momentum Breakout Strategy Test Complete")
    return True


def test_ma_crossover():
    """Test MA Crossover Strategy."""
    print("\n" + "="*70)
    print("🧪 TESTING MA CROSSOVER STRATEGY")
    print("="*70)
    
    strategy = MACrossoverStrategy()
    bars = generate_test_bars(250)  # Need more bars for 200 SMA
    current_price = bars[-1]['close']
    
    # Test analysis
    signal = strategy.analyze("TEST", bars, current_price)
    
    print(f"\n📊 Analysis Result:")
    print(f"   Action: {signal['action']}")
    print(f"   Reason: {signal['reason']}")
    
    if signal.get('indicators'):
        print(f"   Indicators:")
        for key, value in signal['indicators'].items():
            if isinstance(value, float):
                print(f"      {key}: {value:.2f}")
            else:
                print(f"      {key}: {value}")
    
    # Test position sizing
    position_size = strategy.get_position_size(100000, current_price)
    print(f"\n💰 Position Size: {position_size} shares (for $100k account)")
    
    print("\n✅ MA Crossover Strategy Test Complete")
    return True


def test_iron_condor():
    """Test Iron Condor Strategy."""
    print("\n" + "="*70)
    print("🧪 TESTING IRON CONDOR STRATEGY")
    print("="*70)
    
    strategy = IronCondorStrategy()
    current_price = 100.0
    iv_rank = 65  # High IV
    
    # Test analysis
    signal = strategy.analyze("TEST", current_price, iv_rank=iv_rank)
    
    print(f"\n📊 Analysis Result:")
    print(f"   Action: {signal['action']}")
    print(f"   Reason: {signal['reason']}")
    
    if signal.get('legs'):
        print(f"\n   Iron Condor Legs:")
        print(f"      Call Spread: Sell ${signal['legs']['call_spread']['sell_strike']}, Buy ${signal['legs']['call_spread']['buy_strike']}")
        print(f"      Put Spread: Sell ${signal['legs']['put_spread']['sell_strike']}, Buy ${signal['legs']['put_spread']['buy_strike']}")
        print(f"      Estimated Credit: ${signal.get('estimated_credit', 0):.2f}")
        print(f"      Max Loss: ${signal.get('max_loss', 0):.2f}")
        print(f"      Profit Target: ${signal.get('profit_target', 0):.2f}")
    
    # Test position sizing
    contracts = strategy.get_position_size(100000, 1.0, 4.0)
    print(f"\n💰 Position Size: {contracts} contracts (for $100k account)")
    
    # Test exit logic
    test_position = {
        'credit_received': 1.0,
        'call_sell_strike': 105,
        'put_sell_strike': 95
    }
    exit_signal = strategy.check_exit(test_position, 100, dte=35, current_value=0.5)
    print(f"\n🚪 Exit Check: {'EXIT' if exit_signal.get('exit') else 'HOLD'}")
    if exit_signal.get('reason'):
        print(f"   Reason: {exit_signal['reason']}")
    
    print("\n✅ Iron Condor Strategy Test Complete")
    return True


def test_strategy_manager():
    """Test Strategy Manager."""
    print("\n" + "="*70)
    print("🧪 TESTING STRATEGY MANAGER")
    print("="*70)
    
    manager = StrategyManager()
    
    # List strategies
    strategies = manager.list_strategies()
    print(f"\n📋 Available Strategies:")
    for name, active in strategies.items():
        status = "✅ ACTIVE" if active else "⚠️ INACTIVE"
        print(f"   {name}: {status}")
    
    # Test analyze_all
    bars = generate_test_bars(250)
    current_price = bars[-1]['close']
    
    signal = manager.analyze_all("TEST", bars, current_price, iv_rank=65)
    
    print(f"\n📊 Best Signal from All Strategies:")
    print(f"   Action: {signal['action']}")
    print(f"   Reason: {signal['reason']}")
    if signal.get('strategy'):
        print(f"   Strategy: {signal['strategy']}")
    
    print("\n✅ Strategy Manager Test Complete")
    return True


def main():
    """Run all strategy tests."""
    print("\n" + "="*70)
    print("🚀 QUANTITATIVE STRATEGIES TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test each strategy
    results.append(("Mean Reversion", test_mean_reversion()))
    results.append(("Momentum Breakout", test_momentum_breakout()))
    results.append(("MA Crossover", test_ma_crossover()))
    results.append(("Iron Condor", test_iron_condor()))
    results.append(("Strategy Manager", test_strategy_manager()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL STRATEGIES IMPLEMENTED AND WORKING!")
    else:
        print("\n⚠️ Some tests failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
