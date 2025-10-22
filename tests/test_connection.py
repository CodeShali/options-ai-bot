#!/usr/bin/env python3
"""
Test script to verify all API connections.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services import get_alpaca_service, get_llm_service, get_database_service
from loguru import logger


async def test_alpaca():
    """Test Alpaca API connection."""
    print("\n🔍 Testing Alpaca API...")
    try:
        alpaca = get_alpaca_service()
        account = await alpaca.get_account()
        
        print("✅ Alpaca API connected successfully!")
        print(f"   Account: {account['equity']}")
        print(f"   Cash: ${account['cash']:,.2f}")
        print(f"   Buying Power: ${account['buying_power']:,.2f}")
        print(f"   Mode: {settings.trading_mode.upper()}")
        return True
    except Exception as e:
        print(f"❌ Alpaca API connection failed: {e}")
        return False


async def test_openai():
    """Test OpenAI API connection."""
    print("\n🔍 Testing OpenAI API...")
    try:
        llm = get_llm_service()
        
        # Simple test prompt
        result = await llm.client.chat.completions.create(
            model=llm.model,
            max_tokens=100,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'API test successful' if you can read this."}
            ]
        )
        
        response = result.choices[0].message.content
        
        print("✅ OpenAI API connected successfully!")
        print(f"   Model: {llm.model}")
        print(f"   Response: {response[:50]}...")
        return True
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        return False


async def test_database():
    """Test database connection."""
    print("\n🔍 Testing Database...")
    try:
        db = get_database_service()
        await db.initialize()
        
        # Test write
        await db.set_system_state("test_key", "test_value")
        
        # Test read
        value = await db.get_system_state("test_key")
        
        if value == "test_value":
            print("✅ Database connected successfully!")
            print(f"   Path: {db.db_path}")
            return True
        else:
            print("❌ Database read/write test failed")
            return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_discord():
    """Test Discord bot token (basic validation)."""
    print("\n🔍 Testing Discord Configuration...")
    try:
        if not settings.discord_bot_token:
            print("❌ Discord bot token not configured")
            return False
        
        if not settings.discord_channel_id:
            print("❌ Discord channel ID not configured")
            return False
        
        print("✅ Discord configuration looks good!")
        print(f"   Token: {settings.discord_bot_token[:20]}...")
        print(f"   Channel ID: {settings.discord_channel_id}")
        print("   Note: Bot connection will be tested when system starts")
        return True
    except Exception as e:
        print(f"❌ Discord configuration check failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("CONNECTION TEST SUITE")
    print("=" * 60)
    
    results = {
        "Alpaca API": await test_alpaca(),
        "OpenAI API": await test_openai(),
        "Database": await test_database(),
        "Discord Config": await test_discord(),
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{service:20} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! System is ready to run.")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Test Discord commands in your server")
        print("3. Monitor logs: tail -f logs/trading.log")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        print("1. Check your .env file has all required values")
        print("2. Verify API keys are correct")
        print("3. Ensure you have internet connection")
        print("4. Review the error messages above")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
