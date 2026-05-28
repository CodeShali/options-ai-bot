#!/usr/bin/env python3
"""
YouTube Live Trade Monitor — Standalone CLI

Usage:
    python start_youtube_monitor.py <youtube_url> [--channel CHANNEL_ID] [--model tiny.en]

Monitors a YouTube video or live stream for trade executions.
Sends Discord alerts to the configured channel when trades are detected.

Requirements:
    - ANTHROPIC_API_KEY in .env (for Claude Haiku trade detection)
    - DISCORD_BOT_TOKEN in .env
    - DISCORD_CHANNEL_ID or YOUTUBE_MONITOR_CHANNEL_ID in .env
    - System: ffmpeg (apt install ffmpeg / brew install ffmpeg)
    - Python: yt-dlp, faster-whisper (pip install yt-dlp faster-whisper)
"""
import argparse
import asyncio
import signal
import sys

import discord
from loguru import logger

from config import settings
from services.youtube_trade_monitor import YouTubeTradeMonitor, set_monitor


async def print_stats_loop(monitor: YouTubeTradeMonitor, stop_event: asyncio.Event):
    """Print live stats every 60 seconds."""
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


async def run_monitor(youtube_url: str, channel_id: int):
    """Start Discord client and YouTube trade monitor."""
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    stop_event = asyncio.Event()
    monitor: YouTubeTradeMonitor = None

    @client.event
    async def on_ready():
        nonlocal monitor
        logger.info(f"Discord connected as {client.user}")

        # Fetch the target channel
        channel = client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(channel_id)
            except Exception as e:
                logger.error(f"Cannot access Discord channel {channel_id}: {e}")
                stop_event.set()
                await client.close()
                return

        logger.info(f"Discord channel: #{getattr(channel, 'name', channel_id)}")

        # Create and start monitor
        monitor = YouTubeTradeMonitor(discord_channel=channel)
        set_monitor(monitor)

        result = await monitor.start(youtube_url)
        if not result["success"]:
            logger.error(f"Monitor failed to start: {result['message']}")
            stop_event.set()
            await client.close()
            return

        kind = "LIVE" if result.get("is_live") else "VIDEO"
        logger.info(f"✅ [{kind}] {result['message']}")
        logger.info(f"📺 {youtube_url}")
        logger.info("━" * 60)
        logger.info("Monitoring for trades... Press Ctrl+C to stop.")
        logger.info("━" * 60)

        # Send start notification to Discord
        await channel.send(
            f"📡 **YouTube Trade Monitor started**\n"
            f"Type: `{kind}` | Model: `{settings.youtube_whisper_model}`\n"
            f"Stream: {youtube_url}"
        )

        # Background stats printer
        asyncio.create_task(print_stats_loop(monitor, stop_event))

    async def shutdown():
        """Graceful shutdown: stop monitor, notify Discord, close client."""
        if monitor:
            logger.info("Stopping monitor…")
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
            logger.info(f"  Deduplicated:    {s.get('trades_deduplicated', 0)}")
            logger.info(f"  Est. cost:       ${s.get('estimated_cost_usd', 0):.4f}")
            logger.info("━" * 60)

        set_monitor(None)
        if not client.is_closed():
            await client.close()

    # Register signal handlers for Ctrl+C / SIGTERM
    loop = asyncio.get_event_loop()

    def handle_signal():
        if not stop_event.is_set():
            stop_event.set()
            asyncio.create_task(shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler for all signals

    try:
        await client.start(settings.discord_bot_token)
    except discord.LoginFailure:
        logger.error("Invalid DISCORD_BOT_TOKEN — check your .env file")
        sys.exit(1)
    except Exception as e:
        if not stop_event.is_set():
            logger.error(f"Discord client error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Trade Monitor → Discord Alerts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_youtube_monitor.py "https://youtube.com/live/JMyf02fkh6w"
  python start_youtube_monitor.py "https://www.youtube.com/watch?v=XXXXX"
  python start_youtube_monitor.py "https://youtube.com/live/..." --channel 123456789
  python start_youtube_monitor.py "https://youtube.com/live/..." --model tiny.en
        """,
    )
    parser.add_argument("url", help="YouTube URL (live stream or regular video)")
    parser.add_argument(
        "--channel",
        type=int,
        default=None,
        help="Discord channel ID (overrides YOUTUBE_MONITOR_CHANNEL_ID / DISCORD_CHANNEL_ID from .env)",
    )
    parser.add_argument(
        "--model",
        choices=["tiny.en", "base.en", "small.en"],
        default=None,
        help="Whisper model size (default: base.en). tiny.en is faster; small.en is most accurate.",
    )
    args = parser.parse_args()

    # Validate URL
    if "youtube.com" not in args.url and "youtu.be" not in args.url:
        print("Error: URL must be a YouTube link (youtube.com or youtu.be)", file=sys.stderr)
        sys.exit(1)

    # Override model if specified
    if args.model:
        settings.youtube_whisper_model = args.model

    # Resolve channel ID
    channel_id = args.channel
    if not channel_id:
        raw = settings.youtube_monitor_channel_id or settings.discord_channel_id
        try:
            channel_id = int(raw)
        except (TypeError, ValueError):
            print(
                "Error: No valid channel ID. Set YOUTUBE_MONITOR_CHANNEL_ID or "
                "DISCORD_CHANNEL_ID in your .env file, or pass --channel.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    # Banner
    logger.info("━" * 60)
    logger.info("🎬  YouTube Trade Monitor  →  Discord Alerts")
    logger.info("━" * 60)
    logger.info(f"URL:     {args.url}")
    logger.info(f"Channel: {channel_id}")
    logger.info(f"Whisper: {settings.youtube_whisper_model} (local, free)")
    logger.info(f"AI:      Claude Haiku (text + vision)")
    logger.info(f"Est cost: ~$0.10/hr")
    logger.info("━" * 60)
    logger.info("Whisper model will be downloaded on first run (~145MB for base.en)")
    logger.info("━" * 60)

    asyncio.run(run_monitor(args.url, channel_id))


if __name__ == "__main__":
    main()
