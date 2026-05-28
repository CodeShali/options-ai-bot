#!/usr/bin/env python3
"""
YouTube Live Trade Monitor — Standalone CLI

Usage:
    python start_youtube_monitor.py <youtube_url> [--model tiny.en]

Monitors a YouTube video or live stream for trade executions.
Sends Discord alerts via webhook when trades are detected.

Required .env variables (only 2):
    ANTHROPIC_API_KEY=sk-ant-...
    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

System requirements:
    ffmpeg  (brew install ffmpeg  /  apt install ffmpeg)
    pip install yt-dlp faster-whisper
"""
import os
import sys

from dotenv import load_dotenv
load_dotenv()

# Dummy values for unused fields in the shared settings validator
os.environ.setdefault("ALPACA_API_KEY", "not-used")
os.environ.setdefault("ALPACA_SECRET_KEY", "not-used")
os.environ.setdefault("OPENAI_API_KEY", "not-used")
os.environ.setdefault("DISCORD_BOT_TOKEN", "not-used")
os.environ.setdefault("DISCORD_CHANNEL_ID", "0")

import argparse
import asyncio
import signal

from loguru import logger

from config import settings
from services.youtube_trade_monitor import YouTubeTradeMonitor, set_monitor


def parse_timestamp(ts: str) -> int:
    """Convert a timestamp string to seconds.
    Accepts: 5400, 1:30:00, 90:00, 1h30m, 30m
    """
    ts = ts.strip()
    # Plain seconds
    if ts.isdigit():
        return int(ts)
    # HH:MM:SS or MM:SS
    if ":" in ts:
        parts = ts.split(":")
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
    # 1h30m / 30m / 90s style
    import re
    total = 0
    for val, unit in re.findall(r"(\d+)([hms])", ts.lower()):
        if unit == "h":
            total += int(val) * 3600
        elif unit == "m":
            total += int(val) * 60
        elif unit == "s":
            total += int(val)
    if total:
        return total
    raise ValueError(f"Cannot parse timestamp: {ts}")


async def print_stats_loop(monitor: YouTubeTradeMonitor, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=60)
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        s = monitor.stats.to_dict()
        logger.info(
            f"[Stats] chunks={s['chunks_processed']} | "
            f"audio_calls={s['api_calls_audio']} | "
            f"video_calls={s['api_calls_video']} | "
            f"trades_found={s['trades_detected']} | "
            f"alerts_sent={s['trades_sent']} | "
            f"cost=${s['estimated_cost_usd']:.4f}"
        )


async def run_monitor(youtube_url: str, webhook_url: str, start_offset: int = 0):
    stop_event = asyncio.Event()
    monitor = YouTubeTradeMonitor(webhook_url=webhook_url)
    set_monitor(monitor)

    # Send start notification via webhook
    import ssl
    import certifi
    import aiohttp
    import discord

    def _make_session():
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx))

    try:
        async with _make_session() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send(
                f"📡 **YouTube Trade Monitor started**\n"
                f"Model: `{settings.youtube_whisper_model}` | AI: Claude Haiku\n"
                f"Stream: {youtube_url}"
            )
        logger.info("✅ Discord webhook connected")
    except Exception as e:
        logger.error(f"❌ Webhook failed: {e}")
        logger.error("Check your DISCORD_WEBHOOK_URL in .env")
        return

    result = await monitor.start(youtube_url, start_offset=start_offset)
    if not result["success"]:
        logger.error(f"Monitor failed to start: {result['message']}")
        return

    kind = "LIVE" if result.get("is_live") else "VIDEO"
    logger.info(f"✅ [{kind}] {result['message']}")
    logger.info(f"📺 {youtube_url}")
    logger.info("━" * 60)
    logger.info("Monitoring for trades... Press Ctrl+C to stop.")
    logger.info("━" * 60)

    asyncio.create_task(print_stats_loop(monitor, stop_event))

    async def shutdown():
        result = await monitor.stop()
        s = result.get("stats", {})
        logger.info("━" * 60)
        logger.info("Final session stats:")
        logger.info(f"  Duration:        {s.get('elapsed', 'N/A')}")
        logger.info(f"  Chunks:          {s.get('chunks_processed', 0)}")
        logger.info(f"  Audio API calls: {s.get('api_calls_audio', 0)}")
        logger.info(f"  Video API calls: {s.get('api_calls_video', 0)}")
        logger.info(f"  Trades found:    {s.get('trades_detected', 0)}")
        logger.info(f"  Alerts sent:     {s.get('trades_sent', 0)}")
        logger.info(f"  Est. cost:       ${s.get('estimated_cost_usd', 0):.4f}")
        logger.info("━" * 60)
        set_monitor(None)
        stop_event.set()

    loop = asyncio.get_event_loop()

    def handle_signal():
        asyncio.create_task(shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    await stop_event.wait()


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Trade Monitor → Discord Alerts (via Webhook)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_youtube_monitor.py "https://youtube.com/live/JMyf02fkh6w"
  python start_youtube_monitor.py "https://www.youtube.com/watch?v=XXXXX"
  python start_youtube_monitor.py "https://youtube.com/live/..." --model tiny.en
        """,
    )
    parser.add_argument("url", help="YouTube URL (live stream or regular video)")
    parser.add_argument(
        "--model",
        choices=["tiny.en", "base.en", "small.en"],
        default=None,
        help="Whisper model (default: base.en). tiny.en=fastest, small.en=most accurate",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Start from this timestamp, e.g. 1:30:00 or 90:00 or 5400 or 1h30m",
    )
    args = parser.parse_args()

    if "youtube.com" not in args.url and "youtu.be" not in args.url:
        print("Error: Must be a YouTube URL", file=sys.stderr)
        sys.exit(1)

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL not set in .env", file=sys.stderr)
        sys.exit(1)

    if args.model:
        settings.youtube_whisper_model = args.model

    start_offset = 0
    if args.start:
        try:
            start_offset = parse_timestamp(args.start)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    logger.info("━" * 60)
    logger.info("🎬  YouTube Trade Monitor  →  Discord Alerts")
    logger.info("━" * 60)
    logger.info(f"URL:      {args.url}")
    if start_offset:
        h, m, s = start_offset // 3600, (start_offset % 3600) // 60, start_offset % 60
        logger.info(f"Start:    {h:02d}:{m:02d}:{s:02d} ({start_offset}s into video)")
    logger.info(f"Whisper:  {settings.youtube_whisper_model} (local, free)")
    logger.info(f"AI:       Claude Haiku (audio + video)")
    logger.info(f"Discord:  Webhook")
    logger.info(f"Est cost: ~$0.10/hr")
    logger.info("━" * 60)

    asyncio.run(run_monitor(args.url, webhook_url, start_offset))


if __name__ == "__main__":
    main()
