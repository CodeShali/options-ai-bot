#!/usr/bin/env python3
"""
Quick test for the YouTube Trade Monitor.
Tests Claude trade detection and Discord connection without needing a real stream.

Run:
    python test_youtube_monitor.py
"""
import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault("ALPACA_API_KEY", "not-used")
os.environ.setdefault("ALPACA_SECRET_KEY", "not-used")
os.environ.setdefault("OPENAI_API_KEY", "not-used")

from loguru import logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}", colorize=True)


# ─── Test 1: Env vars ────────────────────────────────────────────────────────

def test_env():
    logger.info("TEST 1: Checking environment variables...")
    missing = []
    for key in ["ANTHROPIC_API_KEY", "DISCORD_WEBHOOK_URL"]:
        val = os.getenv(key, "")
        if not val or val == "your_key_here":
            missing.append(key)
        else:
            logger.info(f"  ✅ {key} = {val[:8]}...")
    if missing:
        logger.error(f"  ❌ Missing in .env: {', '.join(missing)}")
        return False
    logger.info("  ✅ All env vars present")
    return True


# ─── Test 2: ffmpeg ──────────────────────────────────────────────────────────

def test_ffmpeg():
    logger.info("TEST 2: Checking ffmpeg...")
    import subprocess
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode == 0:
        version = result.stdout.split("\n")[0]
        logger.info(f"  ✅ {version}")
        return True
    else:
        logger.error("  ❌ ffmpeg not found — run: brew install ffmpeg")
        return False


# ─── Test 3: yt-dlp ──────────────────────────────────────────────────────────

def test_ytdlp():
    logger.info("TEST 3: Checking yt-dlp...")
    try:
        import yt_dlp
        logger.info(f"  ✅ yt-dlp {yt_dlp.version.__version__}")
        return True
    except ImportError:
        logger.error("  ❌ yt-dlp not installed — run: pip install yt-dlp")
        return False


# ─── Test 4: faster-whisper ──────────────────────────────────────────────────

def test_whisper():
    logger.info("TEST 4: Checking faster-whisper...")
    try:
        from faster_whisper import WhisperModel
        logger.info("  ✅ faster-whisper installed (model loads on first real run)")
        return True
    except ImportError:
        logger.error("  ❌ faster-whisper not installed — run: pip install faster-whisper")
        return False


# ─── Test 5: Claude trade detection ─────────────────────────────────────────

async def test_claude_detection():
    logger.info("TEST 5: Testing Claude trade detection...")
    try:
        from services.youtube_trade_monitor import YouTubeTradeMonitor
        from unittest.mock import AsyncMock

        monitor = YouTubeTradeMonitor(discord_channel=AsyncMock())
        monitor.youtube_url = "https://youtube.com/test"

        test_transcripts = [
            ("I'm buying 100 shares of Apple right here at 185 dollars",
             "Should detect BUY AAPL"),
            ("Just sold my Tesla position, got out at 250",
             "Should detect SELL TSLA"),
            ("I think SPY could go higher, watching 450 as resistance",
             "Should detect NO trade (analysis only)"),
            ("Alright entering 5 contracts on the QQQ 380 calls expiring Friday",
             "Should detect BUY QQQ CALL"),
        ]

        all_passed = True
        for transcript, description in test_transcripts:
            trades = await monitor._detect_trades_audio(transcript)
            if "Should detect NO trade" in description:
                status = "✅" if len(trades) == 0 else "⚠️ "
                logger.info(f"  {status} '{transcript[:50]}...' → {len(trades)} trades (expected 0)")
                if len(trades) > 0:
                    logger.info(f"     Got: {trades}")
            else:
                status = "✅" if len(trades) > 0 else "❌"
                logger.info(f"  {status} '{transcript[:50]}...' → {trades[0]['symbol']} {trades[0]['action']} (conf={trades[0].get('confidence',0):.0%})" if trades else f"  {status} '{transcript[:50]}...' → No trade detected")
                if len(trades) == 0:
                    all_passed = False

        return all_passed
    except Exception as e:
        logger.error(f"  ❌ Claude detection failed: {e}")
        return False


# ─── Test 6: Discord webhook ─────────────────────────────────────────────────

async def test_discord():
    logger.info("TEST 6: Testing Discord webhook...")
    try:
        import aiohttp
        import discord

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        if not webhook_url:
            logger.error("  ❌ DISCORD_WEBHOOK_URL not set in .env")
            return False

        import ssl
        import certifi
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(connector=connector) as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send("✅ YouTube Trade Monitor test — connection working!")

        logger.info("  ✅ Webhook works! Check Discord for a test message.")
        return True
    except Exception as e:
        logger.error(f"  ❌ Webhook failed: {e}")
        logger.error("     Check DISCORD_WEBHOOK_URL in your .env")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    logger.info("━" * 60)
    logger.info("YouTube Trade Monitor — Test Suite")
    logger.info("━" * 60)

    results = {}
    results["env"]      = test_env()
    results["ffmpeg"]   = test_ffmpeg()
    results["yt-dlp"]   = test_ytdlp()
    results["whisper"]  = test_whisper()

    if results["env"]:
        results["claude"]  = await test_claude_detection()
        results["discord"] = await test_discord()
    else:
        logger.warning("Skipping Claude + Discord tests until env vars are set")
        results["claude"] = False
        results["discord"] = False

    logger.info("━" * 60)
    logger.info("Results:")
    all_pass = True
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        logger.info(f"  {icon}  {name}")
        if not passed:
            all_pass = False

    logger.info("━" * 60)
    if all_pass:
        logger.info("🎉 All tests passed! Ready to run:")
        logger.info('   python start_youtube_monitor.py "https://youtube.com/live/..."')
    else:
        logger.info("Fix the ❌ items above, then run this test again.")
    logger.info("━" * 60)


if __name__ == "__main__":
    asyncio.run(main())
