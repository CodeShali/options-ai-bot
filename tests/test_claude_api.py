"""
Test Claude API to verify credits are working
"""
import asyncio
from services.claude_service import ClaudeService

async def test_claude():
    print("=" * 60)
    print("TESTING CLAUDE API")
    print("=" * 60)
    
    try:
        # Initialize Claude service
        claude = ClaudeService()
        print(f"\n✅ Claude service initialized")
        print(f"   Client: {'Active' if claude.client else 'Not initialized'}")
        print(f"   Model: claude-sonnet-4-20250514")
        
        # Test simple analysis
        print("\n🧪 Testing Claude API call...")
        response = await claude.analyze_stock(
            messages=[
                {
                    "role": "user",
                    "content": "Analyze AAPL stock in one sentence. Is it bullish or bearish?"
                }
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        if response:
            print(f"\n✅ Claude API is WORKING!")
            print(f"\n📊 Response:")
            print(f"   {response[:200]}...")
            print(f"\n💰 Credits: ACTIVE")
            return True
        else:
            print(f"\n❌ Claude API returned empty response")
            return False
            
    except Exception as e:
        print(f"\n❌ Claude API Error: {e}")
        if "credit balance" in str(e).lower():
            print(f"\n💳 Issue: No credits available")
            print(f"   Solution: Add payment method at https://console.anthropic.com/settings/billing")
        return False
    
    finally:
        print("\n" + "=" * 60)

if __name__ == "__main__":
    result = asyncio.run(test_claude())
    exit(0 if result else 1)
