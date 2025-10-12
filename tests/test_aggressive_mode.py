"""
Test suite for aggressive trading mode implementation.
Tests trade type detection, AI prompts, and Discord integration.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from config import settings, enable_aggressive_mode, disable_aggressive_mode
from agents.strategy_agent import StrategyAgent
from services import get_alpaca_service, get_llm_service


class AggressiveModeTests:
    """Test suite for aggressive mode features."""
    
    def __init__(self):
        """Initialize test suite."""
        self.results = []
        self.strategy = StrategyAgent()
        
    def _add_result(self, test_name: str, status: str, details: str = ""):
        """Add test result."""
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        logger.info(f"{emoji} {test_name}: {status} - {details}")
    
    async def test_config_aggressive_mode(self):
        """Test aggressive mode configuration."""
        test_name = "Aggressive Mode Config"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test enable
            enable_aggressive_mode()
            
            assert settings.aggressive_mode == True, "Aggressive mode not enabled"
            assert settings.scan_interval == 60, f"Scan interval should be 60, got {settings.scan_interval}"
            assert settings.max_daily_loss == 500, f"Circuit breaker should be 500, got {settings.max_daily_loss}"
            assert settings.options_min_dte == 0, f"Min DTE should be 0, got {settings.options_min_dte}"
            
            # Test disable
            disable_aggressive_mode()
            
            assert settings.aggressive_mode == False, "Aggressive mode not disabled"
            assert settings.scan_interval == 300, f"Scan interval should be 300, got {settings.scan_interval}"
            assert settings.max_daily_loss == 1000, f"Circuit breaker should be 1000, got {settings.max_daily_loss}"
            
            self._add_result(test_name, "PASS", "Config toggles correctly")
            
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
    
    async def test_trade_type_detection(self):
        """Test trade type detection logic."""
        test_name = "Trade Type Detection"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Enable aggressive mode for testing
            enable_aggressive_mode()
            
            # Test scalping criteria (high score, high volatility)
            opportunity_scalp = {
                'score': 85,
                'volume_ratio': 2.5,
                'symbol': 'TEST'
            }
            
            technical_scalp = {
                'Volatility': 3.0,
                'Momentum_5': 3.0
            }
            
            sentiment_scalp = {
                'overall_score': 0.7
            }
            
            trade_type = self.strategy._determine_trade_type(
                opportunity_scalp,
                technical_scalp,
                sentiment_scalp
            )
            
            assert trade_type == 'scalp', f"Expected 'scalp', got '{trade_type}'"
            
            # Test day trading criteria
            opportunity_day = {
                'score': 75,
                'volume_ratio': 1.8,
                'symbol': 'TEST'
            }
            
            technical_day = {
                'Volatility': 1.5,
                'Momentum_5': 1.5
            }
            
            sentiment_day = {
                'overall_score': 0.5
            }
            
            trade_type = self.strategy._determine_trade_type(
                opportunity_day,
                technical_day,
                sentiment_day
            )
            
            assert trade_type == 'day_trade', f"Expected 'day_trade', got '{trade_type}'"
            
            # Test swing trading (low scores)
            opportunity_swing = {
                'score': 60,
                'volume_ratio': 1.2,
                'symbol': 'TEST'
            }
            
            technical_swing = {
                'Volatility': 0.5,
                'Momentum_5': 0.5
            }
            
            sentiment_swing = {
                'overall_score': 0.2
            }
            
            trade_type = self.strategy._determine_trade_type(
                opportunity_swing,
                technical_swing,
                sentiment_swing
            )
            
            assert trade_type == 'swing', f"Expected 'swing', got '{trade_type}'"
            
            self._add_result(test_name, "PASS", "All trade types detected correctly")
            
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
    
    async def test_targets_by_trade_type(self):
        """Test profit targets and stops by trade type."""
        test_name = "Targets by Trade Type"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            entry_price = 100.0
            
            # Test scalp targets
            targets_scalp = self.strategy._get_targets_for_trade_type('scalp', entry_price)
            assert targets_scalp['target_pct'] == 0.015, "Scalp target should be 1.5%"
            assert targets_scalp['stop_pct'] == 0.01, "Scalp stop should be 1%"
            assert targets_scalp['max_hold_minutes'] == 30, "Scalp hold time should be 30 min"
            assert abs(targets_scalp['target_price'] - 101.5) < 0.01, "Scalp target price incorrect"
            
            # Test day trade targets
            targets_day = self.strategy._get_targets_for_trade_type('day_trade', entry_price)
            assert targets_day['target_pct'] == 0.03, "Day trade target should be 3%"
            assert targets_day['stop_pct'] == 0.015, "Day trade stop should be 1.5%"
            assert targets_day['max_hold_minutes'] == 120, "Day trade hold time should be 120 min"
            assert abs(targets_day['target_price'] - 103.0) < 0.01, "Day trade target price incorrect"
            
            # Test swing targets
            targets_swing = self.strategy._get_targets_for_trade_type('swing', entry_price)
            assert targets_swing['target_pct'] == 0.50, "Swing target should be 50%"
            assert targets_swing['stop_pct'] == 0.30, "Swing stop should be 30%"
            assert targets_swing['max_hold_minutes'] is None, "Swing should have no time limit"
            assert abs(targets_swing['target_price'] - 150.0) < 0.01, "Swing target price incorrect"
            
            self._add_result(test_name, "PASS", "All targets calculated correctly")
            
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
    
    async def test_ai_prompt_generation(self):
        """Test AI prompt generation for different trade types."""
        test_name = "AI Prompt Generation"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            market_data = {
                'current_price': 180.50,
                'price_change_pct': 2.5,
                'volume_ratio': 1.8,
                'sma_20': 178.00,
                'high': 182.0,
                'low': 179.0
            }
            
            technical_indicators = {
                'RSI': 65,
                'SMA_20': 178.0,
                'SMA_50': 175.0,
                'Momentum_5': 2.5,
                'Volatility': 1.5
            }
            
            sentiment_data = {
                'overall_sentiment': 'POSITIVE',
                'overall_score': 0.6,
                'news_sentiment': {
                    'sentiment': 'POSITIVE',
                    'impact': 'HIGH'
                },
                'market_sentiment': {
                    'sentiment': 'POSITIVE'
                }
            }
            
            targets = {'target_pct': 0.015, 'stop_pct': 0.01}
            
            # Test scalp prompt
            prompt_scalp = self.strategy._build_scalp_prompt(
                'AAPL', market_data, technical_indicators, sentiment_data, targets
            )
            assert 'SCALP' in prompt_scalp, "Scalp prompt missing trade type"
            assert '5-30 minutes' in prompt_scalp, "Scalp prompt missing hold time"
            assert 'AAPL' in prompt_scalp, "Scalp prompt missing symbol"
            
            # Test day trade prompt
            prompt_day = self.strategy._build_day_trade_prompt(
                'AAPL', market_data, technical_indicators, sentiment_data, targets
            )
            assert 'DAY TRADE' in prompt_day, "Day trade prompt missing trade type"
            assert '30-120 minutes' in prompt_day, "Day trade prompt missing hold time"
            
            # Test swing prompt
            prompt_swing = self.strategy._build_swing_prompt(
                'AAPL', market_data, technical_indicators, sentiment_data, targets
            )
            assert 'SWING' in prompt_swing, "Swing prompt missing trade type"
            assert 'hours to days' in prompt_swing, "Swing prompt missing hold time"
            
            self._add_result(test_name, "PASS", "All prompts generated correctly")
            
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
    
    async def test_response_parsing(self):
        """Test AI response parsing."""
        test_name = "AI Response Parsing"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test valid response
            response = """
RECOMMENDATION: BUY
CONFIDENCE: 75
RISK_LEVEL: MEDIUM
ENTRY_PRICE: 180.50
REASONING: Strong momentum with high volume confirmation. RSI indicates room to run.
"""
            
            result = self.strategy._parse_analysis_response(response, 'scalp')
            
            assert result['recommendation'] == 'BUY', f"Expected BUY, got {result['recommendation']}"
            assert result['confidence'] == 75.0, f"Expected 75.0, got {result['confidence']}"
            assert result['risk_level'] == 'MEDIUM', f"Expected MEDIUM, got {result['risk_level']}"
            assert result['entry_price'] == 180.50, f"Expected 180.50, got {result['entry_price']}"
            assert 'momentum' in result['reasoning'].lower(), "Reasoning missing"
            assert result['trade_type'] == 'scalp', "Trade type not preserved"
            
            self._add_result(test_name, "PASS", "Response parsed correctly")
            
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
    
    async def test_discord_helpers(self):
        """Test Discord helper functions."""
        test_name = "Discord Helpers"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            from bot.discord_helpers import (
                create_status_embed,
                create_position_embed,
                create_sentiment_embed,
                create_error_embed,
                create_success_embed
            )
            
            # Test status embed
            status_data = {
                'running': True,
                'status': 'Running',
                'mode': 'paper',
                'paused': False,
                'account': {
                    'equity': 100000,
                    'cash': 50000,
                    'buying_power': 100000
                },
                'positions': {
                    'count': 3,
                    'total_pl': 500,
                    'today_pl': 200
                },
                'performance': {
                    'win_rate': 65,
                    'total_trades': 20,
                    'total_pl': 1000
                },
                'circuit_breaker': {
                    'active': False,
                    'daily_loss': 0,
                    'limit': 1000
                },
                'last_scan': 'Just now',
                'last_trade': '5 min ago',
                'uptime': '2 hours'
            }
            
            embed = create_status_embed(status_data)
            assert embed.title == "🤖 Trading System Status", "Status embed title incorrect"
            assert len(embed.fields) > 0, "Status embed has no fields"
            
            # Test error embed
            error_embed = create_error_embed("Test error message")
            assert error_embed.title == "❌ Error", "Error embed title incorrect"
            
            # Test success embed
            success_embed = create_success_embed("Test success message")
            assert success_embed.title == "✅ Success", "Success embed title incorrect"
            
            self._add_result(test_name, "PASS", "All Discord helpers working")
            
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all tests."""
        logger.info("=" * 80)
        logger.info("AGGRESSIVE MODE TEST SUITE")
        logger.info("=" * 80)
        
        # Run tests
        await self.test_config_aggressive_mode()
        await self.test_trade_type_detection()
        await self.test_targets_by_trade_type()
        await self.test_ai_prompt_generation()
        await self.test_response_parsing()
        await self.test_discord_helpers()
        
        # Generate report
        self._generate_report()
    
    def _generate_report(self):
        """Generate test report."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 80)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        total = len(self.results)
        
        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📊 Success Rate: {(passed/total)*100:.1f}%")
        
        logger.info("\n" + "=" * 80)
        logger.info("DETAILED RESULTS")
        logger.info("=" * 80)
        
        for result in self.results:
            emoji = "✅" if result['status'] == 'PASS' else "❌"
            logger.info(f"\n{emoji} {result['test']}")
            logger.info(f"   Status: {result['status']}")
            logger.info(f"   Details: {result['details']}")
        
        logger.info("\n" + "=" * 80)
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! System ready for deployment.")
        else:
            logger.info(f"⚠️ {failed} test(s) failed. Please review and fix.")
        
        logger.info("=" * 80)


async def main():
    """Main test runner."""
    tests = AggressiveModeTests()
    await tests.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
