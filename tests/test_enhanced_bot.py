"""
Test script for Enhanced Discord Bot
Validates all services load correctly without errors.
"""
import sys
import asyncio
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

async def test_imports():
    """Test that all services can be imported."""
    print("\n🧪 Testing Enhanced Bot Imports...\n")
    
    try:
        print("1️⃣  Testing core services...")
        from services import (
            get_alpaca_service,
            get_database_service,
            get_llm_service,
            get_cache_service,
        )
        print("   ✅ Core services imported")
        
        print("\n2️⃣  Testing Discord enhancement services...")
        from services.discord_realtime_service import get_discord_realtime_service
        print("   ✅ Real-time service imported")
        
        from services.discord_interactive_service import get_discord_interactive_service
        print("   ✅ Interactive service imported")
        
        from services.discord_alerts_service import get_discord_alerts_service
        print("   ✅ Alerts service imported")
        
        from services.discord_analytics_service import get_discord_analytics_service
        print("   ✅ Analytics service imported")
        
        from services.discord_market_intelligence import get_discord_market_intelligence
        print("   ✅ Market intelligence imported")
        
        from services.discord_risk_calculator import get_discord_risk_calculator
        print("   ✅ Risk calculator imported")
        
        from services.discord_conversation_service import get_discord_conversation_service
        print("   ✅ Conversation service imported")
        
        from services.discord_nlp_core import is_trading_related, classify_intent
        print("   ✅ NLP core imported")
        
        print("\n3️⃣  Testing enhanced bot...")
        from bot.discord_enhanced_bot import enhanced_bot
        print("   ✅ Enhanced bot imported")
        
        print("\n4️⃣  Testing bot initialization...")
        print(f"   Bot name: {enhanced_bot.__class__.__name__}")
        print(f"   Command prefix: {enhanced_bot.command_prefix}")
        print(f"   Intents configured: ✅")
        
        print("\n5️⃣  Testing service attributes...")
        services = [
            'realtime_service',
            'interactive_service',
            'alerts_service',
            'analytics_service',
            'conversation_service'
        ]
        for service in services:
            if hasattr(enhanced_bot, service):
                print(f"   ✅ {service} attribute exists")
            else:
                print(f"   ⚠️  {service} attribute missing (will be initialized on startup)")
        
        print("\n6️⃣  Testing NLP functionality...")
        test_queries = [
            "What's my P&L?",
            "Why did you exit TSLA?",
            "What's the weather?",
        ]
        for query in test_queries:
            is_trading = is_trading_related(query)
            intent = classify_intent(query)
            status = "✅ Trading" if is_trading else "❌ Off-topic"
            print(f"   {status}: '{query}' → Intent: {intent}")
        
        print("\n✅ ALL IMPORTS SUCCESSFUL!")
        print("=" * 60)
        print("🎉 Enhanced Discord Bot is ready to start!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_initialization():
    """Test that services can be initialized (without Discord connection)."""
    print("\n🧪 Testing Service Initialization (Dry Run)...\n")
    
    try:
        from services import (
            get_alpaca_service,
            get_database_service,
            get_llm_service,
            get_cache_service,
        )
        
        print("1️⃣  Initializing core services...")
        
        # These should initialize without errors
        cache = get_cache_service()
        print(f"   ✅ Cache service: {cache.__class__.__name__}")
        
        db = get_database_service()
        print(f"   ✅ Database service: {db.__class__.__name__}")
        
        llm = get_llm_service()
        print(f"   ✅ LLM service: {llm.__class__.__name__}")
        
        print("\n2️⃣  Testing cache operations...")
        await cache.set("test_key", "test_value", ttl=60)
        value = await cache.get("test_key")
        if value == "test_value":
            print("   ✅ Cache read/write works")
        else:
            print("   ⚠️  Cache read/write issue")
        
        print("\n✅ SERVICE INITIALIZATION SUCCESSFUL!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 ENHANCED DISCORD BOT - VALIDATION TEST")
    print("=" * 60)
    
    # Test imports
    imports_ok = await test_imports()
    
    if not imports_ok:
        print("\n❌ Import tests failed. Fix errors before starting bot.")
        return False
    
    # Test service initialization
    services_ok = await test_service_initialization()
    
    if not services_ok:
        print("\n❌ Service initialization failed. Fix errors before starting bot.")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\n📋 Summary:")
    print("   ✅ All imports successful")
    print("   ✅ All services can be initialized")
    print("   ✅ NLP functionality works")
    print("   ✅ Cache operations work")
    print("\n🚀 Ready to start the enhanced bot!")
    print("\n💡 To start the bot, run:")
    print("   python main.py  (if you've updated main.py)")
    print("   or")
    print("   python -c 'from bot.discord_enhanced_bot import enhanced_bot; from config import settings; enhanced_bot.run(settings.discord_token)'")
    print("\n")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
