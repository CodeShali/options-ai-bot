"""
YouTube Trade Monitor Service

Monitors any YouTube video or live stream for trade executions, using:
  - faster-whisper (local, free) for audio transcription
  - Claude Haiku (text) for detecting spoken trades
  - Claude Haiku Vision for detecting trades shown on broker screens
  - Discord embeds for real-time alerts
"""
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiohttp
import anthropic
import discord
from loguru import logger

from config import settings


AUDIO_SYSTEM_PROMPT = """You are an expert trade execution detector for live trading streams.

Your ONLY job is to identify moments when the trader PHYSICALLY EXECUTES a trade RIGHT NOW.

CONFIRM a trade ONLY when you hear EXPLICIT execution language such as:
- "I'm buying / I'm selling [X] right here / right now"
- "Going long / short [X]"
- "I just got filled / filled at [price]"
- "I'm in [X]" (entering a position)
- "I'm out / taking profits / closed my [X]"
- "Bought [X] / Sold [X]"

DO NOT flag:
- "I'm watching X" / "I'm waiting for X"
- "I would buy here" / "if price does X I'll buy"
- "We're looking at X" / "X is setting up"
- Explaining past trades or hypothetical setups
- Any sentence with "if", "when", "could", "should", "might", "would", "watching", "waiting"

Be VERY conservative. If you are not 90%+ certain it is a live execution, return confidence < 0.75 or omit it.

Return ONLY valid JSON:
{"trades":[{"symbol":"NQ","action":"BUY","quantity":1,"price":21450.0,
"type":"FUTURES","strike":null,"expiry":null,"confidence":0.92,
"quote":"exact verbatim words proving the execution"}]}

type options: STOCK, FUTURES, CALL, PUT
Return {"trades":[]} if no confirmed live execution found."""

VIDEO_SYSTEM_PROMPT = """You analyze trading platform screenshots to detect live trade executions.

CONFIRM a trade ONLY when you see:
- An order ticket with BUY/SELL just submitted or filled
- A green/red "Order Filled" or "Position Opened" confirmation popup
- A new position appearing in the positions panel that wasn't there before
- A trade blotter showing a brand-new execution

DO NOT flag:
- Charts, price levels, indicators
- Watchlists or scanners
- Open positions that were already there
- Educational annotations on charts

Be very conservative. Only flag what you are 90%+ certain is a new execution.

Return ONLY valid JSON:
{"trades":[{"symbol":"NQ","action":"BUY","quantity":1,"price":21450.0,
"type":"FUTURES","strike":null,"expiry":null,"confidence":0.92,
"source_frame":0,"quote":"describe exactly what confirms the trade on screen"}]}

Return {"trades":[]} if no confirmed new execution is visible."""

SONNET_MODEL = "claude-sonnet-4-6"


class MonitorStats:
    def __init__(self):
        self.chunks_processed = 0
        self.api_calls_audio = 0
        self.api_calls_video = 0
        self.trades_detected = 0
        self.trades_sent = 0
        self.trades_deduplicated = 0
        self.started_at: Optional[datetime] = None
        self.last_chunk_at: Optional[datetime] = None
        self.estimated_cost_usd = 0.0

    def to_dict(self) -> dict:
        elapsed = None
        if self.started_at:
            elapsed = str(datetime.now() - self.started_at).split(".")[0]
        return {
            "chunks_processed": self.chunks_processed,
            "api_calls_audio": self.api_calls_audio,
            "api_calls_video": self.api_calls_video,
            "trades_detected": self.trades_detected,
            "trades_sent": self.trades_sent,
            "trades_deduplicated": self.trades_deduplicated,
            "elapsed": elapsed,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }


class YouTubeTradeMonitor:
    """
    Monitors a YouTube video or live stream for spoken and displayed trade executions.

    Architecture:
      1. yt-dlp resolves audio + video stream URLs from the YouTube URL.
      2. ffmpeg captures overlapping 60s audio chunks and video frames every 15s.
      3. faster-whisper transcribes audio locally (free, CPU).
      4. Claude Haiku analyzes transcript text for spoken trade mentions.
      5. Claude Haiku Vision analyzes frame batches for broker screen trade executions.
      6. Detections are merged, deduplicated, and sent as Discord embeds.
    """

    def __init__(self, discord_channel: discord.abc.Messageable = None, webhook_url: str = None):
        self.discord_channel = discord_channel
        self.webhook_url = webhook_url
        self.youtube_url: Optional[str] = None
        self.state = "idle"
        self._stop_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None

        # Deduplication: {key -> datetime_sent}
        self._sent_trades: OrderedDict[str, datetime] = OrderedDict()
        self._dedup_window = timedelta(minutes=settings.youtube_dedup_minutes)

        # Stream info populated by start()
        self._audio_url: Optional[str] = None
        self._video_url: Optional[str] = None
        self._is_live = False
        self._duration: Optional[int] = None
        self._stream_title = ""

        # faster-whisper model (lazy-loaded on first transcription)
        self._whisper_model = None

        # Anthropic client
        if settings.anthropic_api_key:
            self._claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            self._claude = None
            logger.warning("No ANTHROPIC_API_KEY — trade detection disabled (set key in .env)")

        self.stats = MonitorStats()

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def start(self, youtube_url: str, start_offset: int = 0) -> dict:
        """Begin monitoring the given YouTube URL.

        Args:
            youtube_url: YouTube video or live stream URL
            start_offset: Start processing from this many seconds into the video (0 = beginning)
        """
        if self.state not in ("idle", "error"):
            return {"success": False, "message": f"Monitor is already {self.state}"}

        self.youtube_url = youtube_url
        self.state = "starting"
        self._stop_event.clear()
        self._start_offset = start_offset

        try:
            info = await self._get_stream_info(youtube_url)
        except Exception as e:
            self.state = "error"
            return {"success": False, "message": f"Could not resolve stream: {e}"}

        self._is_live = info["is_live"]
        self._duration = info.get("duration")
        self._audio_url = info["audio_url"]
        self._video_url = info["video_url"]
        self._stream_title = info.get("title", "")

        self.stats = MonitorStats()
        self.stats.started_at = datetime.now()
        self.state = "running"
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

        kind = "live stream" if self._is_live else "video"
        offset_str = f" from {start_offset//3600:02d}:{(start_offset%3600)//60:02d}:{start_offset%60:02d}" if start_offset else ""
        return {
            "success": True,
            "message": f"Monitoring started ({kind}){offset_str}: {self._stream_title}",
            "is_live": self._is_live,
            "title": self._stream_title,
        }

    async def stop(self) -> dict:
        """Stop monitoring gracefully."""
        if self.state == "idle":
            return {"success": True, "message": "Not running", "stats": self.stats.to_dict()}

        self._stop_event.set()
        self.state = "stopping"

        if self._monitor_task and not self._monitor_task.done():
            try:
                await asyncio.wait_for(self._monitor_task, timeout=15.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._monitor_task.cancel()

        self.state = "idle"
        return {"success": True, "message": "Monitoring stopped", "stats": self.stats.to_dict()}

    def get_status(self) -> dict:
        return {
            "state": self.state,
            "youtube_url": self.youtube_url,
            "title": self._stream_title,
            "is_live": self._is_live,
            "stats": self.stats.to_dict(),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Stream info
    # ──────────────────────────────────────────────────────────────────────────

    def _ytdlp_base(self) -> list:
        """Base yt-dlp args including cookie auth if configured."""
        args = ["yt-dlp", "--no-playlist", "--no-warnings"]
        browser = getattr(settings, "youtube_cookies_browser", "") or os.getenv("YOUTUBE_COOKIES_BROWSER", "")
        if browser:
            args += ["--cookies-from-browser", browser]
        return args

    async def _get_stream_info(self, url: str) -> dict:
        """Use yt-dlp to retrieve stream metadata and stream URL."""
        # Step 1: Get metadata (no format filter — just info)
        meta_cmd = self._ytdlp_base() + ["--dump-json", url]
        proc = await asyncio.create_subprocess_exec(
            *meta_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode()[:500])

        info = json.loads(stdout.decode())
        is_live = bool(info.get("is_live"))

        # Step 2: Get a single best stream URL using --get-url (no format restriction)
        url_cmd = self._ytdlp_base() + ["--get-url", url]
        proc2 = await asyncio.create_subprocess_exec(
            *url_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout2, stderr2 = await asyncio.wait_for(proc2.communicate(), timeout=60)
        if proc2.returncode != 0:
            raise RuntimeError(stderr2.decode()[:500])

        # --get-url may return multiple lines (video + audio); take the first
        stream_url = stdout2.decode().strip().splitlines()[0]
        logger.debug(f"Stream URL resolved for: {info.get('title', url)}")

        return {
            "is_live": is_live,
            "duration": info.get("duration"),
            "audio_url": stream_url,
            "video_url": stream_url,   # same URL works for both ffmpeg audio and frame extraction
            "title": info.get("title", ""),
        }

    async def _refresh_audio_url(self) -> str:
        """Re-resolve audio URL (live stream URLs rotate ~every 6 hours)."""
        cmd = self._ytdlp_base() + ["--get-url", "-f", "bestaudio/best", self.youtube_url]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            raise RuntimeError("Failed to refresh stream URL")
        return stdout.decode().strip()

    # ──────────────────────────────────────────────────────────────────────────
    # Audio pipeline
    # ──────────────────────────────────────────────────────────────────────────

    async def _capture_audio_chunk(self, offset: int, duration: int) -> Path:
        """
        Capture `duration` seconds of audio via ffmpeg.
        For live streams offset is ignored (ffmpeg reads from current live position).
        Returns path to a temporary .wav file (caller must delete it).
        """
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="yt_audio_")
        tmp.close()
        out_path = Path(tmp.name)

        cmd = [
            "ffmpeg", "-y",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
        ]
        if not self._is_live and offset > 0:
            cmd += ["-ss", str(offset)]
        cmd += [
            "-i", self._audio_url,
            "-t", str(duration),
            "-vn",          # no video
            "-ac", "1",     # mono
            "-ar", "16000", # 16 kHz for Whisper
            "-f", "wav",
            str(out_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=duration + 30)

        if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 1000:
            out_path.unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg audio capture failed (code {proc.returncode})")

        return out_path

    def _transcribe_sync(self, audio_path: Path) -> str:
        """Synchronous transcription — run via run_in_executor to keep event loop free."""
        if self._whisper_model is None:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model '{settings.youtube_whisper_model}' ...")
            self._whisper_model = WhisperModel(
                settings.youtube_whisper_model, device="cpu", compute_type="int8"
            )
            logger.info("Whisper model ready")
        segments, _ = self._whisper_model.transcribe(
            str(audio_path), beam_size=5, language="en"
        )
        return " ".join(seg.text.strip() for seg in segments)

    async def _transcribe_local(self, audio_path: Path) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_path)

    async def _detect_trades_audio(self, transcript: str) -> list[dict]:
        """Claude Haiku: extract trades from transcript text."""
        if not self._claude or not transcript.strip():
            return []
        try:
            response = self._claude.messages.create(
                model=SONNET_MODEL,
                max_tokens=512,
                system=[
                    {
                        "type": "text",
                        "text": AUDIO_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": f"Transcript: {transcript}"}],
            )
            self.stats.api_calls_audio += 1
            self.stats.estimated_cost_usd += 0.0004
            trades = self._parse_trades_json(response.content[0].text)
            for t in trades:
                t.setdefault("detected_by", "audio")
            return trades
        except Exception as e:
            logger.warning(f"Audio trade detection error: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # Video pipeline
    # ──────────────────────────────────────────────────────────────────────────

    async def _capture_video_frames(self, offset: int, window: int) -> list[Path]:
        """
        Capture one frame every `youtube_frame_interval` seconds within `window` seconds
        starting at `offset`. Returns list of individual temp .jpg files (caller must delete).
        """
        frame_interval = settings.youtube_frame_interval
        tmpdir = tempfile.mkdtemp(prefix="yt_frames_")
        pattern = os.path.join(tmpdir, "frame_%03d.jpg")

        cmd = [
            "ffmpeg", "-y",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
        ]
        if not self._is_live and offset > 0:
            cmd += ["-ss", str(offset)]
        cmd += [
            "-i", self._video_url,
            "-t", str(window),
            "-vf", f"fps=1/{frame_interval},scale=1280:-1",
            "-q:v", "5",
            pattern,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=window + 30)

            # Copy frames to individual temp files so tmpdir can be removed
            result = []
            for src in sorted(Path(tmpdir).glob("frame_*.jpg")):
                if src.stat().st_size > 500:
                    dst_fd, dst_path = tempfile.mkstemp(suffix=".jpg", prefix="yt_frame_")
                    os.close(dst_fd)
                    shutil.copy2(src, dst_path)
                    result.append(Path(dst_path))
            return result
        except Exception as e:
            logger.warning(f"Video frame capture error: {e}")
            return []
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    async def _detect_trades_video(self, frame_paths: list[Path]) -> list[dict]:
        """Claude Haiku Vision: extract trades from a batch of video frames."""
        if not self._claude or not frame_paths:
            return []
        try:
            content: list = [
                {
                    "type": "text",
                    "text": VIDEO_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            for i, fp in enumerate(frame_paths[:4]):  # max 4 frames per call
                with open(fp, "rb") as f:
                    img_b64 = base64.standard_b64encode(f.read()).decode()
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_b64,
                    },
                })
            content.append({
                "type": "text",
                "text": f"Analyze these {len(frame_paths)} frames for trade executions.",
            })

            response = self._claude.messages.create(
                model=SONNET_MODEL,
                max_tokens=512,
                messages=[{"role": "user", "content": content}],
            )
            self.stats.api_calls_video += 1
            self.stats.estimated_cost_usd += 0.002  # vision calls cost more
            trades = self._parse_trades_json(response.content[0].text)
            for t in trades:
                t.setdefault("detected_by", "video")
            return trades
        except Exception as e:
            logger.warning(f"Video trade detection error: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # Trade parsing & deduplication
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_trades_json(self, text: str) -> list[dict]:
        """Parse Claude's JSON response into a list of valid trade dicts."""
        try:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if not m:
                return []
            data = json.loads(m.group())
            raw = data.get("trades", [])
            valid = []
            for t in raw:
                if (
                    isinstance(t, dict)
                    and t.get("symbol")
                    and t.get("action") in ("BUY", "SELL")
                    and float(t.get("confidence") or 0) >= settings.youtube_min_confidence
                ):
                    t["symbol"] = str(t["symbol"]).upper()
                    t["action"] = str(t["action"]).upper()
                    t["type"] = str(t.get("type") or "STOCK").upper()
                    valid.append(t)
            return valid
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f"Trade JSON parse issue: {e} | raw: {text[:200]}")
            return []

    def _merge_detections(
        self, audio_trades: list[dict], video_trades: list[dict]
    ) -> list[dict]:
        """Merge audio and video detections; combine same trade into one alert."""
        merged: dict[str, dict] = {}
        for trade in audio_trades + video_trades:
            key = f"{trade.get('symbol','').upper()}_{trade.get('action','').upper()}"
            if key in merged:
                existing = merged[key]
                srcs = set()
                if existing.get("detected_by"):
                    srcs.add(existing["detected_by"])
                if trade.get("detected_by"):
                    srcs.add(trade["detected_by"])
                existing["detected_by"] = " + ".join(sorted(srcs))
                existing["confidence"] = max(
                    float(existing.get("confidence") or 0),
                    float(trade.get("confidence") or 0),
                )
            else:
                merged[key] = dict(trade)
        return list(merged.values())

    def _dedup_key(self, trade: dict) -> str:
        symbol = (trade.get("symbol") or "").upper()
        action = (trade.get("action") or "").upper()
        ttype = (trade.get("type") or "STOCK").upper()
        price = round(float(trade.get("price") or 0), 1)
        raw = f"{symbol}_{action}_{ttype}_{price}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def _is_duplicate(self, trade: dict) -> bool:
        now = datetime.now()
        cutoff = now - self._dedup_window
        stale = [k for k, v in self._sent_trades.items() if v < cutoff]
        for k in stale:
            del self._sent_trades[k]
        return self._dedup_key(trade) in self._sent_trades

    def _record_sent(self, trade: dict):
        self._sent_trades[self._dedup_key(trade)] = datetime.now()

    # ──────────────────────────────────────────────────────────────────────────
    # Discord alert
    # ──────────────────────────────────────────────────────────────────────────

    def _confidence_bar(self, confidence: float) -> str:
        filled = int(confidence * 10)
        return "█" * filled + "░" * (10 - filled) + f"  {confidence * 100:.0f}%"

    def _build_embed(self, trade: dict) -> discord.Embed:
        symbol = (trade.get("symbol") or "?").upper()
        action = (trade.get("action") or "?").upper()
        ttype = (trade.get("type") or "STOCK").upper()
        quantity = trade.get("quantity")
        price = trade.get("price")
        strike = trade.get("strike")
        expiry = trade.get("expiry")
        confidence = float(trade.get("confidence") or 0)
        quote = (trade.get("quote") or "").strip()
        detected_by = trade.get("detected_by", "audio")

        if action in ("BUY", "OPEN"):
            color = discord.Color.green()
            emoji = "🟢"
        elif action in ("SELL", "CLOSE"):
            color = discord.Color.red()
            emoji = "🔴"
        else:
            color = discord.Color.orange()
            emoji = "⚠️"

        src_parts = []
        if "audio" in detected_by.lower():
            src_parts.append("🎤 Audio")
        if "video" in detected_by.lower():
            src_parts.append("📹 Video")
        source_str = " + ".join(src_parts) if src_parts else detected_by

        embed = discord.Embed(
            title=f"{emoji} TRADE DETECTED: {symbol}",
            color=color,
            timestamp=datetime.now(),
        )
        embed.add_field(name="Action", value=action, inline=True)
        instrument_label = {"STOCK": "Stock", "CALL": "Call Option", "PUT": "Put Option"}.get(ttype, ttype)
        embed.add_field(name="Type", value=instrument_label, inline=True)
        embed.add_field(name="Source", value=source_str, inline=True)

        unit = "contracts" if ttype in ("CALL", "PUT") else "shares"
        qty_str = f"{quantity:,} {unit}" if quantity else "Not stated"
        embed.add_field(name="Quantity", value=qty_str, inline=True)
        price_str = f"${float(price):,.2f}" if price else "Not stated"
        embed.add_field(name="Price", value=price_str, inline=True)
        embed.add_field(name="Confidence", value=self._confidence_bar(confidence), inline=True)

        if ttype in ("CALL", "PUT") and (strike or expiry):
            opts = []
            if strike:
                opts.append(f"Strike: ${float(strike):,.2f}")
            if expiry:
                opts.append(f"Expiry: {expiry}")
            embed.add_field(name="Options Detail", value=" | ".join(opts), inline=False)

        if quote:
            display = quote[:300] + "..." if len(quote) > 300 else quote
            embed.add_field(name="Quote", value=f'*"{display}"*', inline=False)

        url_display = (self.youtube_url or "")[:70]
        embed.set_footer(text=f"📺 {url_display}")
        return embed

    async def _send_alert(self, trade: dict):
        try:
            embed = self._build_embed(trade)

            if self.webhook_url:
                import ssl
                import certifi
                ssl_ctx = ssl.create_default_context(cafile=certifi.where())
                connector = aiohttp.TCPConnector(ssl=ssl_ctx)
                async with aiohttp.ClientSession(connector=connector) as session:
                    webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                    await webhook.send(embed=embed)
            elif self.discord_channel:
                await self.discord_channel.send(embed=embed)
            else:
                logger.error("No Discord webhook or channel configured")
                return

            self.stats.trades_sent += 1
            logger.info(f"Alert sent: {trade.get('action')} {trade.get('symbol')} "
                        f"(confidence={trade.get('confidence', 0):.0%})")
        except Exception as e:
            logger.error(f"Discord send failed: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Main monitoring loop
    # ──────────────────────────────────────────────────────────────────────────

    async def _monitoring_loop(self):
        chunk_sec = settings.youtube_chunk_seconds
        step_sec = settings.youtube_step_seconds
        offset = getattr(self, "_start_offset", 0)
        if offset:
            logger.info(f"Starting from offset {offset//3600:02d}:{(offset%3600)//60:02d}:{offset%60:02d}")
        consecutive_failures = 0
        max_failures = 5

        logger.info(
            f"Monitoring loop started | chunk={chunk_sec}s step={step_sec}s "
            f"frame_interval={settings.youtube_frame_interval}s"
        )

        while not self._stop_event.is_set():
            # Stop at video end for non-live
            if not self._is_live and self._duration and offset >= self._duration:
                logger.info("Video fully processed, stopping")
                break

            t_start = asyncio.get_event_loop().time()
            audio_path: Optional[Path] = None
            frame_paths: list[Path] = []

            try:
                # Capture audio and frames concurrently
                audio_task = asyncio.create_task(
                    self._capture_audio_chunk(offset, chunk_sec)
                )
                frame_task = asyncio.create_task(
                    self._capture_video_frames(offset, step_sec)
                )
                results = await asyncio.gather(audio_task, frame_task, return_exceptions=True)
                audio_result, frame_result = results

                if isinstance(audio_result, Exception):
                    logger.warning(f"Audio capture failed: {audio_result}")
                    consecutive_failures += 1
                    audio_path = None
                else:
                    consecutive_failures = 0
                    audio_path = audio_result

                frame_paths = [] if isinstance(frame_result, Exception) else frame_result
                if isinstance(frame_result, Exception):
                    logger.debug(f"Frame capture failed: {frame_result}")

                # Transcribe audio
                transcript = ""
                if audio_path:
                    try:
                        transcript = await self._transcribe_local(audio_path)
                        logger.debug(f"Transcript ({len(transcript)}c): {transcript[:80]}…")
                    except Exception as e:
                        logger.warning(f"Transcription error: {e}")

                # Detect trades in parallel from both channels
                audio_detect = asyncio.create_task(self._detect_trades_audio(transcript))
                video_detect = asyncio.create_task(self._detect_trades_video(frame_paths))
                audio_trades, video_trades = await asyncio.gather(audio_detect, video_detect)

                all_trades = self._merge_detections(audio_trades, video_trades)

                # Source-based confidence filtering:
                # Single source (audio only OR video only) needs 0.75+
                # Both sources agree needs only 0.55+ (two signals = stronger)
                combined_key = "audio + video"
                filtered_trades = []
                for trade in all_trades:
                    conf = float(trade.get("confidence") or 0)
                    src = (trade.get("detected_by") or "").lower()
                    is_combined = "audio" in src and "video" in src
                    threshold = settings.youtube_min_confidence_combined if is_combined else settings.youtube_min_confidence_single
                    if conf >= threshold:
                        filtered_trades.append(trade)
                    else:
                        logger.debug(f"Filtered low-confidence trade: {trade.get('symbol')} {trade.get('action')} conf={conf:.0%} src={src} (need {threshold:.0%})")
                all_trades = filtered_trades

                self.stats.chunks_processed += 1
                self.stats.trades_detected += len(all_trades)
                self.stats.last_chunk_at = datetime.now()

                for trade in all_trades:
                    if self._is_duplicate(trade):
                        self.stats.trades_deduplicated += 1
                        logger.debug(f"Suppressed duplicate: {trade.get('symbol')} {trade.get('action')}")
                    else:
                        self._record_sent(trade)
                        await self._send_alert(trade)

                # Handle repeated failures
                if consecutive_failures >= max_failures:
                    msg = (
                        f"⚠️ YouTube monitor stopped after {max_failures} consecutive failures. "
                        "The stream may have ended or the URL expired."
                    )
                    logger.error(msg)
                    try:
                        if self.webhook_url:
                            async with aiohttp.ClientSession() as session:
                                webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                                await webhook.send(msg)
                        elif self.discord_channel:
                            await self.discord_channel.send(msg)
                    except Exception:
                        pass
                    break

                # Refresh stream URL after partial failures
                if 0 < consecutive_failures < max_failures:
                    try:
                        self._audio_url = await self._refresh_audio_url()
                        logger.info("Stream URL refreshed after failure")
                        consecutive_failures = 0
                    except Exception as e:
                        logger.warning(f"URL refresh failed: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Loop iteration error: {e}", exc_info=True)
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
            finally:
                if audio_path and isinstance(audio_path, Path):
                    audio_path.unlink(missing_ok=True)
                for fp in frame_paths:
                    if isinstance(fp, Path):
                        fp.unlink(missing_ok=True)

            offset += step_sec

            # For live streams: wait to maintain real-time cadence
            # For recorded videos: process immediately, no need to wait
            if self._is_live:
                elapsed = asyncio.get_event_loop().time() - t_start
                sleep_time = max(0.0, step_sec - elapsed)
                if sleep_time > 0:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(self._stop_event.wait()), timeout=sleep_time
                        )
                        break  # stop event was set
                    except asyncio.TimeoutError:
                        pass

        self.state = "idle"
        logger.info(f"Monitor stopped. {self.stats.to_dict()}")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton for bot integration
# ─────────────────────────────────────────────────────────────────────────────

_monitor: Optional[YouTubeTradeMonitor] = None


def get_monitor() -> Optional[YouTubeTradeMonitor]:
    return _monitor


def set_monitor(monitor: Optional[YouTubeTradeMonitor]):
    global _monitor
    _monitor = monitor
