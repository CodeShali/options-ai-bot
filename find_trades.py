#!/usr/bin/env python3
"""
Find actual trade timestamps in a YouTube video using Claude AI.
Run locally before monitoring to find the best --start time.

Usage:
    python find_trades.py "https://www.youtube.com/live/JMyf02fkh6w"

Requirements:
    pip install youtube-transcript-api anthropic python-dotenv
"""
import os
import re
import sys

from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault("ALPACA_API_KEY", "not-used")
os.environ.setdefault("ALPACA_SECRET_KEY", "not-used")
os.environ.setdefault("OPENAI_API_KEY", "not-used")
os.environ.setdefault("DISCORD_BOT_TOKEN", "not-used")
os.environ.setdefault("DISCORD_CHANNEL_ID", "0")

import anthropic


SYSTEM_PROMPT = """You analyze transcripts from trading live streams.
Your job is to identify the EXACT moments when the trader actually executes a trade (entry or exit).

For each real trade execution found, return:
- timestamp (HH:MM:SS)
- action: BUY or SELL
- instrument: what they traded (NQ, ES, AAPL, etc.)
- what they said (verbatim quote)

Ignore: analysis, commentary, education, watching levels, hypotheticals.
Only include confirmed executions where the trader is clearly entering or exiting a real position RIGHT NOW.

Return as a clean numbered list."""


def get_transcript(video_id: str) -> list:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("Install: pip install youtube-transcript-api")
        sys.exit(1)

    try:
        api = YouTubeTranscriptApi()
        return list(api.fetch(video_id))
    except Exception:
        try:
            raw = YouTubeTranscriptApi.get_transcript(video_id)
            return [type('S', (), {'text': s['text'], 'start': s['start']})() for s in raw]
        except Exception as e:
            print(f"Could not fetch transcript: {e}")
            sys.exit(1)


def seconds_to_ts(s: int) -> str:
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def analyze_chunk_with_claude(client: anthropic.Anthropic, chunk_text: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Transcript segment:\n\n{chunk_text}"}]
    )
    return response.content[0].text


def find_trade_timestamps(url: str):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    match = re.search(r"(?:v=|live/|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if not match:
        print("Could not extract video ID from URL")
        sys.exit(1)

    video_id = match.group(1)
    print(f"Video ID: {video_id}")
    print("Fetching transcript...")

    transcript = get_transcript(video_id)
    duration = int(transcript[-1].start) if transcript else 0
    print(f"Transcript loaded: {len(transcript)} segments, duration {seconds_to_ts(duration)}\n")

    # Build text chunks of ~5 minutes each, with timestamps inline
    CHUNK_SECONDS = 300  # 5 minutes per Claude call
    client = anthropic.Anthropic(api_key=api_key)

    print("=" * 65)
    print("Scanning transcript with Claude AI...")
    print("=" * 65)

    all_results = []
    chunk_start = 0

    while chunk_start < duration:
        chunk_end = chunk_start + CHUNK_SECONDS
        segs = [s for s in transcript if chunk_start <= s.start < chunk_end]

        if not segs:
            chunk_start = chunk_end
            continue

        # Format chunk with timestamps so Claude can reference them
        lines = []
        for s in segs:
            t = seconds_to_ts(int(s.start))
            lines.append(f"[{t}] {s.text}")
        chunk_text = "\n".join(lines)

        ts_range = f"{seconds_to_ts(chunk_start)} – {seconds_to_ts(min(chunk_end, duration))}"
        print(f"Analyzing {ts_range}...", end=" ", flush=True)

        result = analyze_chunk_with_claude(client, chunk_text)

        # Check if Claude found anything real
        if any(word in result.lower() for word in ["buy", "sell", "long", "short", "no trade", "no execution", "none found", "nothing"]):
            if "no trade" not in result.lower() and "none" not in result.lower() and "no execution" not in result.lower() and len(result.strip()) > 20:
                print("✅ trades found!")
                all_results.append((ts_range, result))
            else:
                print("— no trades")
        else:
            print("— no trades")

        chunk_start = chunk_end

    print()
    print("=" * 65)
    print("RESULTS:")
    print("=" * 65)

    if all_results:
        for ts_range, result in all_results:
            print(f"\n📍 {ts_range}")
            print(result)
            print()

        # Extract first timestamp mentioned for suggested command
        first_ts = re.search(r'\d{2}:\d{2}:\d{2}', all_results[0][1])
        if first_ts:
            print("=" * 65)
            print("Suggested test command:")
            print(f'  python start_youtube_monitor.py "{url}" --start {first_ts.group()} --model tiny.en')
    else:
        print("No confirmed trade executions found in transcript.")
        print("The trader may not have executed any trades, or auto-captions were unavailable.")

    print("=" * 65)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_trades.py <youtube_url>")
        sys.exit(1)
    find_trade_timestamps(sys.argv[1])
