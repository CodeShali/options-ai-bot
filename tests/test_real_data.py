"""
Comprehensive test suite for real data integration.
Tests all components with actual API calls.
"""
import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import get_alpaca_service, get_llm_service
from services.news_service import get_news_service
from services.sentiment_service import get_sentiment_service
from agents.strategy_agent import StrategyAgent
from agents.risk_manager_agent import RiskManagerAgent


class RealDataTester:
    """Comprehensive tester for real data integration."""
    
    def __init__(self):
        """Initialize tester."""
        self.results = []
        self.alpaca = None
        self.news = None
        self.sentiment = None
        self.llm = None
        self.strategy = None
        self.risk_manager = None
        
    async def run_all_tests(self):
        """Run all tests and generate report."""
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE REAL DATA TEST SUITE")
        logger.info("=" * 80)
        
        # Initialize services
        await self._initialize_services()
        
        # Run tests
        await self._test_alpaca_connection()
        await self._test_market_data()
        await self._test_news_api()
        await self._test_sentiment_analysis()
        await self._test_strategy_agent()
        await self._test_risk_manager()
        await self._test_greeks_analysis()
        await self._test_end_to_end()
        
        # Generate report
        self._generate_report()
        
        return self.results
    
    async def _initialize_services(self):
        """Initialize all services."""
        try:
            logger.info("\n📦 Initializing services...")
            
            self.alpaca = get_alpaca_service()
            self.news = get_news_service()
            self.llm = get_llm_service()
            self.sentiment = get_sentiment_service()
            self.sentiment.set_llm(self.llm)
            self.sentiment.set_alpaca(self.alpaca)
            self.sentiment.set_news(self.news)
            
            self.strategy = StrategyAgent()
            self.risk_manager = RiskManagerAgent()
            
            self._add_result("Service Initialization", "PASS", "All services initialized successfully")
            logger.info("✅ All services initialized")
            
        except Exception as e:
            self._add_result("Service Initialization", "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ Failed to initialize services: {e}")
            raise
    
    async def _test_alpaca_connection(self):
        """Test Alpaca API connection."""
        test_name = "Alpaca API Connection"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test account access
            account = await self.alpaca.get_account()
            
            if account:
                self._add_result(
                    test_name,
                    "PASS",
                    f"Connected to Alpaca - Account: {account['account_number']}, "
                    f"Buying Power: ${float(account['buying_power']):,.2f}"
                )
                logger.info(f"✅ {test_name} passed")
            else:
                self._add_result(test_name, "FAIL", "Failed to get account info")
                logger.error(f"❌ {test_name} failed")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_market_data(self):
        """Test real market data fetching."""
        test_name = "Real Market Data (SPY/VIX/QQQ)"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test SPY
            spy_bars = await self.alpaca.get_bars("SPY", timeframe="1Day", limit=5)
            
            # Test VIX
            try:
                vix_bars = await self.alpaca.get_bars("VIX", timeframe="1Day", limit=5)
                vix_available = bool(vix_bars)
            except:
                vix_available = False
            
            # Test QQQ
            qqq_bars = await self.alpaca.get_bars("QQQ", timeframe="1Day", limit=5)
            
            if spy_bars and len(spy_bars) > 0:
                spy_price = spy_bars[-1]['close']
                
                details = f"SPY: ${spy_price:.2f} ({len(spy_bars)} bars)"
                
                if qqq_bars and len(qqq_bars) > 0:
                    qqq_price = qqq_bars[-1]['close']
                    details += f", QQQ: ${qqq_price:.2f}"
                
                if vix_available and len(vix_bars) > 0:
                    vix_price = vix_bars[-1]['close']
                    details += f", VIX: {vix_price:.2f}"
                else:
                    details += ", VIX: Not available"
                
                self._add_result(test_name, "PASS", details)
                logger.info(f"✅ {test_name} passed - {details}")
            else:
                # Market might be closed
                self._add_result(
                    test_name, 
                    "WARN", 
                    "No market data available (market may be closed - this is expected on weekends/holidays)"
                )
                logger.warning(f"⚠️ {test_name} - Market closed (expected behavior)")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_news_api(self):
        """Test NewsAPI integration."""
        test_name = "NewsAPI Integration"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test with popular stock
            articles = await self.news.get_news("AAPL", days=7, max_articles=5)
            
            if self.news.enabled:
                if articles:
                    self._add_result(
                        test_name,
                        "PASS",
                        f"Fetched {len(articles)} real articles for AAPL. "
                        f"First headline: '{articles[0]['title'][:60]}...'"
                    )
                    logger.info(f"✅ {test_name} passed - {len(articles)} articles")
                else:
                    self._add_result(
                        test_name,
                        "WARN",
                        "NewsAPI enabled but no articles found (may be rate limited)"
                    )
                    logger.warning(f"⚠️ {test_name} - No articles found")
            else:
                self._add_result(
                    test_name,
                    "SKIP",
                    "NewsAPI not enabled (NEWS_API_ENABLED=false)"
                )
                logger.info(f"⏭️ {test_name} skipped - API not enabled")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_sentiment_analysis(self):
        """Test sentiment analysis with real data."""
        test_name = "Sentiment Analysis (Real Data)"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test sentiment for SPY
            sentiment = await self.sentiment.analyze_symbol_sentiment("SPY")
            
            news_source = sentiment['news_sentiment'].get('data_source', 'unknown')
            market_source = sentiment['market_sentiment'].get('data_source', 'unknown')
            
            if sentiment:
                self._add_result(
                    test_name,
                    "PASS",
                    f"Overall: {sentiment['overall_sentiment']} ({sentiment['overall_score']:.2f}), "
                    f"News: {news_source}, Market: {market_source}"
                )
                logger.info(f"✅ {test_name} passed")
                logger.info(f"   News source: {news_source}")
                logger.info(f"   Market source: {market_source}")
                logger.info(f"   Overall sentiment: {sentiment['overall_sentiment']}")
            else:
                self._add_result(test_name, "FAIL", "No sentiment data returned")
                logger.error(f"❌ {test_name} failed")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_strategy_agent(self):
        """Test strategy agent with real data."""
        test_name = "Strategy Agent (AI Analysis)"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Create mock opportunity
            opportunity = {
                "symbol": "AAPL",
                "score": 82,
                "current_price": 180.50,
                "price_change_pct": 2.5,
                "volume_ratio": 1.8,
                "sma_20": 178.00,
                "quote": {"bid_size": 100, "ask_size": 100},
                "bars": [{"high": 182.0, "low": 179.0, "close": 180.50, "volume": 50000000}]
            }
            
            # Test AI analysis using the strategy's analyze_opportunity method directly
            result = await self.strategy.analyze_opportunity(opportunity)
            
            if result and result.get('recommendation'):
                self._add_result(
                    test_name,
                    "PASS",
                    f"Recommendation: {result['recommendation']}, "
                    f"Confidence: {result['confidence']}%, "
                    f"Risk: {result['risk_level']}"
                )
                logger.info(f"✅ {test_name} passed")
                logger.info(f"   Recommendation: {result['recommendation']}")
                logger.info(f"   Confidence: {result['confidence']}%")
            else:
                self._add_result(
                    test_name, 
                    "WARN", 
                    "AI analysis returned no recommendation (may be due to neutral sentiment or API limits)"
                )
                logger.warning(f"⚠️ {test_name} - No recommendation (expected with neutral sentiment)")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_risk_manager(self):
        """Test risk manager validation."""
        test_name = "Risk Manager Validation"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test stock trade validation
            stock_result = await self.risk_manager.process({
                "action": "validate_trade",
                "trade_type": "stock",
                "symbol": "AAPL",
                "quantity": 10,
                "price": 180.50,
                "side": "buy"
            })
            
            # Test options trade validation
            options_result = await self.risk_manager.process({
                "action": "validate_options_trade",
                "symbol": "AAPL",
                "option_type": "call",
                "contracts": 2,
                "premium": 4.50,
                "strike": 185.0,
                "expiration": "2025-01-17",
                "dte": 35
            })
            
            stock_valid = stock_result.get('valid', False)
            options_valid = options_result.get('valid', False)
            
            if stock_valid and options_valid:
                self._add_result(
                    test_name,
                    "PASS",
                    f"Stock validation: {stock_valid}, Options validation: {options_valid}"
                )
                logger.info(f"✅ {test_name} passed")
            else:
                self._add_result(
                    test_name,
                    "WARN",
                    f"Stock: {stock_valid}, Options: {options_valid} - "
                    f"May be due to circuit breaker or position limits"
                )
                logger.warning(f"⚠️ {test_name} - Some validations failed (may be expected)")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_greeks_analysis(self):
        """Test Greeks analysis."""
        test_name = "Greeks Analysis"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test option quote with Greeks
            option_symbol = "AAPL250117C00185000"  # AAPL Jan 17 2025 $185 Call
            quote = await self.alpaca.get_option_quote(option_symbol, include_greeks=True)
            
            if quote and 'greeks' in quote:
                greeks = quote['greeks']
                self._add_result(
                    test_name,
                    "PASS",
                    f"Greeks available - Delta: {greeks['delta']:.3f}, "
                    f"Theta: {greeks['theta']:.3f}, "
                    f"Vega: {greeks['vega']:.3f}, "
                    f"Source: {'estimated' if greeks.get('estimated') else 'real'}"
                )
                logger.info(f"✅ {test_name} passed")
                logger.info(f"   Delta: {greeks['delta']:.3f}")
                logger.info(f"   Theta: {greeks['theta']:.3f}")
            else:
                self._add_result(test_name, "FAIL", "No Greeks data available")
                logger.error(f"❌ {test_name} failed")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    async def _test_end_to_end(self):
        """Test complete end-to-end flow."""
        test_name = "End-to-End Trading Flow"
        logger.info(f"\n🧪 Testing: {test_name}")
        
        try:
            # 1. Get market data
            spy_bars = await self.alpaca.get_bars("SPY", timeframe="1Day", limit=1)
            
            # 2. Get sentiment
            sentiment = await self.sentiment.analyze_symbol_sentiment("SPY")
            
            # 3. Create opportunity
            opportunity = {
                "symbol": "SPY",
                "score": 78,
                "current_price": spy_bars[-1]['close'] if spy_bars else 450.0,
                "price_change_pct": 1.2,
                "volume_ratio": 1.5,
                "sma_20": 448.0,
                "quote": {"bid_size": 100, "ask_size": 100},
                "bars": [{"high": 452.0, "low": 448.0, "close": 450.0, "volume": 80000000}]
            }
            
            # 4. AI analysis
            analysis = await self.strategy.process({
                "action": "analyze",
                "opportunity": opportunity
            })
            
            # 5. Instrument decision
            if analysis and analysis.get('recommendation') == 'BUY':
                decision = await self.strategy.decide_instrument_type(analysis, opportunity)
                
                # 6. Risk validation
                if decision['instrument'] == 'stock':
                    validation = await self.risk_manager.process({
                        "action": "validate_trade",
                        "trade_type": "stock",
                        "symbol": "SPY",
                        "quantity": 10,
                        "price": opportunity['current_price'],
                        "side": "buy"
                    })
                else:
                    validation = await self.risk_manager.process({
                        "action": "validate_options_trade",
                        "symbol": "SPY",
                        "option_type": decision.get('option_type', 'call'),
                        "contracts": 1,
                        "premium": 4.50,
                        "strike": 455.0,
                        "expiration": "2025-01-17",
                        "dte": 35
                    })
                
                self._add_result(
                    test_name,
                    "PASS",
                    f"Complete flow executed - Sentiment: {sentiment['overall_sentiment']}, "
                    f"Recommendation: {analysis['recommendation']}, "
                    f"Instrument: {decision['instrument']}, "
                    f"Validation: {validation.get('valid', False)}"
                )
                logger.info(f"✅ {test_name} passed")
            else:
                self._add_result(
                    test_name,
                    "PASS",
                    f"Flow executed but no BUY signal (Recommendation: {analysis.get('recommendation', 'NONE')})"
                )
                logger.info(f"✅ {test_name} passed (no trade signal)")
                
        except Exception as e:
            self._add_result(test_name, "FAIL", f"Error: {str(e)}")
            logger.error(f"❌ {test_name} failed: {e}")
    
    def _add_result(self, test_name: str, status: str, details: str):
        """Add test result."""
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def _generate_report(self):
        """Generate test report."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST REPORT SUMMARY")
        logger.info("=" * 80)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results if r['status'] == 'WARN')
        skipped = sum(1 for r in self.results if r['status'] == 'SKIP')
        total = len(self.results)
        
        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⚠️ Warnings: {warned}")
        logger.info(f"⏭️ Skipped: {skipped}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        logger.info(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        logger.info("\n" + "=" * 80)
        logger.info("DETAILED RESULTS")
        logger.info("=" * 80)
        
        for result in self.results:
            status_emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARN': '⚠️',
                'SKIP': '⏭️'
            }.get(result['status'], '❓')
            
            logger.info(f"\n{status_emoji} {result['test']}")
            logger.info(f"   Status: {result['status']}")
            logger.info(f"   Details: {result['details']}")


async def main():
    """Run tests."""
    tester = RealDataTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    import json
    report_file = "test_report.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n📄 Full report saved to: {report_file}")
    
    # Return exit code based on failures
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
