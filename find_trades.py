#!/usr/bin/env python3
"""
Find ACTUAL trade entry/exit timestamps in a YouTube trading video.
Run locally to find the right --start time for the monitor.

Usage:
    python find_trades.py "https://www.youtube.com/live/JMyf02fkh6w"

Install requirement:
    pip install youtube-transcript-api
"""
import sys
import re


# Very specific execution phrases — must sound like placing/closing an order RIGHT NOW
ENTRY_PHRASES = [
    "i'm buying", "i am buying", "buying here", "buying this",
    "i'm selling", "i am selling", "selling here",
    "going long", "going short",
    "i'm long", "i'm short", "i am long", "i am short",
    "getting long", "getting short",
    "i'm in", "i am in", "getting in", "got in", "i'm entering",
    "taking a long", "taking a short", "taking the long", "taking the short",
    "i just bought", "i just sold", "just filled", "just got filled",
    "filled at", "entry at", "entered at", "entered here",
    "loading up", "i'm loaded", "i loaded",
    "i bought", "i sold", "i entered",
    "long here", "short here",
    "i'm taking", "taking profit", "taking profits",
    "i'm out", "i am out", "getting out", "got out",
    "closed my", "closing my", "exiting here", "i exited",
    "stop hit", "stop was hit", "got stopped",
]

# Phrases to EXCLUDE — commentary, not execution
EXCLUDE_PHRASES = [
    "make sure", "god bless", "next stream", "subscribe", "like and",
    "comment below", "in the next", "see you", "thank you",
    "if you", "you guys", "let me know", "don't forget",
    "by the way", "as i said", "talked about", "looking for",
    "waiting for", "i think", "i believe", "could be",
    "should be", "might be", "would be", "going to be",
    "watch for", "watching", "levels", "structure",
]


def find_trade_timestamps(url: str):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        print("Install first: pip install youtube-transcript-api")
        sys.exit(1)

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
    except Exception:
        try:
            raw = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = [type('S', (), {'text': s['text'], 'start': s['start']})() for s in raw]
        except Exception as e:
            print(f"Could not fetch transcript: {e}")
            sys.exit(1)

    print("=" * 65)
    print("ACTUAL TRADE EXECUTIONS FOUND:")
    print("=" * 65)

    found = []
    seen_times = set()

    for i, seg in enumerate(transcript):
        text_lower = seg.text.lower()

        # Must match an entry phrase
        matched = any(phrase in text_lower for phrase in ENTRY_PHRASES)
        if not matched:
            continue

        # Must NOT be commentary
        excluded = any(phrase in text_lower for phrase in EXCLUDE_PHRASES)
        if excluded:
            continue

        t = int(seg.start)

        # Skip if we already showed a trade within 30 seconds of this
        if any(abs(t - seen) < 30 for seen in seen_times):
            continue
        seen_times.add(t)

        h, m, s = t // 3600, (t % 3600) // 60, t % 60
        context = " ".join(x.text for x in transcript[max(0, i-1):i+4])
        found.append((f"{h:02d}:{m:02d}:{s:02d}", context))

    if found:
        for timestamp, context in found:
            print(f"⏱  {timestamp}  →  {context}")
            print()
    else:
        print("No clear trade executions found in transcript.")
        print("Try running the monitor at 30:00 or 1:00:00 and watch the output.")

    print("=" * 65)
    print(f"Found {len(found)} likely trade executions")
    if found:
        print()
        print("Suggested test command (first trade found):")
        print(f'  python start_youtube_monitor.py "{url}" --start {found[0][0]} --model tiny.en')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_trades.py <youtube_url>")
        sys.exit(1)
    find_trade_timestamps(sys.argv[1])
