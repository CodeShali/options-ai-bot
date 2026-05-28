#!/usr/bin/env python3
"""
Find trade timestamps in any YouTube video.
Run this locally to find the right --start time for the monitor.

Usage:
    python find_trades.py "https://www.youtube.com/live/JMyf02fkh6w"

Install requirement:
    pip install youtube-transcript-api
"""
import sys

def find_trade_timestamps(url: str):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("Install first: pip install youtube-transcript-api")
        sys.exit(1)

    # Extract video ID
    import re
    match = re.search(r"(?:v=|live/|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    if not match:
        print("Could not extract video ID from URL")
        sys.exit(1)
    video_id = match.group(1)
    print(f"Video ID: {video_id}")
    print("Fetching transcript...\n")

    try:
        api = YouTubeTranscriptApi()
        transcript = list(api.fetch(video_id))
    except Exception as e:
        # Try older API
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = [type('S', (), {'text': s['text'], 'start': s['start']})() for s in transcript]
        except Exception as e2:
            print(f"Could not fetch transcript: {e2}")
            sys.exit(1)

    TRADE_KEYWORDS = [
        "buying", "selling", "bought", "sold",
        "long", "short", "entry", "exit",
        "filled", "fill", "i'm in", "getting in", "got in",
        "taking a", "entering", "out of",
        "trade", "position", "loaded", "scalp",
        "stop loss", "target", "taking profit",
        "going long", "going short"
    ]

    print("=" * 65)
    print("TRADE MOMENTS FOUND:")
    print("=" * 65)

    found = 0
    for i, seg in enumerate(transcript):
        text = seg.text.lower()
        if any(k in text for k in TRADE_KEYWORDS):
            t = int(seg.start)
            h, m, s = t // 3600, (t % 3600) // 60, t % 60
            # Get surrounding context (3 segments)
            context = " ".join(x.text for x in transcript[max(0, i-1):i+3])
            print(f"⏱  {h:02d}:{m:02d}:{s:02d}  →  {context}")
            print()
            found += 1

    print("=" * 65)
    print(f"Found {found} potential trade moments")
    print()
    print("Use the timestamp with:")
    print(f'  python start_youtube_monitor.py "{url}" --start HH:MM:SS --model tiny.en')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_trades.py <youtube_url>")
        sys.exit(1)
    find_trade_timestamps(sys.argv[1])
