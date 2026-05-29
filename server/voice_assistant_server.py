#!/usr/bin/env python3
"""
ESP32-S3 Voice Assistant Server  v19
======================================
Audio format: RAW PCM s16le mono 16kHz — zero-copy, no decode step,
              works across all pipelines, minimum latency.

Streaming architecture (LOCAL pipeline):
  ESP32 mic → server WS (raw PCM) → Whisper STT
                                      ↓ text (200ms)
                              Ollama gemma2:2b (streaming tokens)
                                      ↓ sentence queue
                              edge-tts (PCM output, per sentence)
                                      ↓ 512B packets
                              ESP32 speaker ring buffer → I2S DAC

Streaming architecture (SARVAM pipeline):
  ESP32 mic → server WS (raw PCM) → Sarvam STT WS (saaras:v3, pcm_s16le)
                                      ↓ transcript
                              Sarvam chat (sarvam-m)
                                      ↓ text (streaming via our sentence splitter)
                              Sarvam TTS WS (bulbul:v3, output_audio_codec=pcm)
                                      ↓ raw PCM chunks (no decode needed!)
                              ESP32 speaker ring buffer → I2S DAC

Parallel processing:
  • LLM tokens → sentence_q → TTS tasks (asyncio.gather, true overlap)
  • Multiple TTS sentences in flight simultaneously via asyncio.Queue
  • First audio plays within ~300ms of speech end on local, ~500ms on Sarvam

API keys: Stored in api_keys.json (created on first run), editable via dashboard.
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
import wave
import io
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Set, Optional

import numpy as np
import websockets
import websockets.exceptions
from aiohttp import web, ClientSession

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log     = logging.getLogger("va")
mic_log = logging.getLogger("va.mic")
spk_log = logging.getLogger("va.spk")

# ── PATHS ─────────────────────────────────────────────────────────────────────
_HERE      = Path(__file__).parent
_KEYS_FILE = _HERE / "api_keys.json"

# ── API KEYS (persisted to disk) ──────────────────────────────────────────────
def _load_keys() -> Dict[str, str]:
    if _KEYS_FILE.exists():
        try:
            return json.loads(_KEYS_FILE.read_text())
        except Exception:
            pass
    return {"sarvam": "", "gemini": ""}

def _save_keys(keys: Dict[str, str]):
    _KEYS_FILE.write_text(json.dumps(keys, indent=2))

_KEYS = _load_keys()

# ── PERSONAS ──────────────────────────────────────────────────────────────────
PERSONAS = {
    "vikram": {
        "name":    "Vikram",
        "gender":  "male",
        "voice":   "en-IN-PrabhatNeural",   # edge-tts Indian male
        "sarvam_speaker": "shubh",          # Sarvam Indian male
        "system":  (
            "You are Vikram, a sharp and friendly Indian AI assistant. "
            "Speak like a natural Indian — warm, direct, occasionally use yaar/bilkul/haan. "
            "RULE: reply in EXACTLY 1 short sentence (max 20 words). No lists. No markdown."
        ),
    },
    "diya": {
        "name":    "Diya",
        "gender":  "female",
        "voice":   "en-IN-NeerjaNeural",    # edge-tts Indian female
        "sarvam_speaker": "anushka",        # Sarvam Indian female
        "system":  (
            "You are Diya, a witty and cheerful Indian AI assistant. "
            "Speak naturally — confident, warm, occasional Hindi (haan/arre/bilkul). "
            "RULE: reply in EXACTLY 1 short sentence (max 20 words). No lists. No markdown."
        ),
    },
}

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG: Dict[str, Any] = {
    # Core
    "pipeline":           "local",     # local | sarvam | gemini
    "persona":            "vikram",

    # Audio hardware
    "chunk_size":         640,         # bytes per WS mic packet (20ms @ 16kHz)
    "volume":             100,         # 0-200; 100=unity
    "sample_rate":        16000,
    "dma_len":            256,
    "dma_bufs":           8,
    "gain_shift":         11,
    "hpf_alpha":          31785,
    "clip_limit":         30000,

    # Network
    "ws_host":            "10.133.85.73",
    "ws_port":            8765,
    "http_port":          8081,

    # Local pipeline
    "whisper_model":      "tiny",      # tiny≈200ms | base≈700ms on CPU
    "ollama_model":       "gemma2:2b",
    "ollama_host":        "http://localhost:11434",

    # TTS
    "tts_engine":         "edge-tts",  # edge-tts | espeak | piper
    "tts_rate":           "+10%",       # voice pace (-20%…+30%)
    "tts_pitch":          "+0Hz",
    "piper_model":        "en_US-amy-medium",

    # Sarvam
    "sarvam_language":    "en-IN",
    "sarvam_stt_model":   "saaras:v3",
    "sarvam_chat_model":  "sarvam-m",
    "sarvam_tts_model":   "bulbul:v3",

    # Gemini
    "gemini_model":       "gemini-2.0-flash-live-001",

    # Streaming
    "ws_packet_bytes":    512,         # safe under ESP32 WS lib 1436B limit
    "tts_sample_rate":    16000,

    # VAD
    "vad_speech_rms":     800,   # raised: room noise was 400-900 rms
    "vad_silence_frames": 10,          # 10×20ms = 200ms silence window
    "vad_min_speech":     6,           # 6×20ms = 120ms minimum utterance
}

CONNECTED_DEVICES: Set = set()
DEVICE_INFO:  Dict = {}
CONV_HISTORY: Dict = {}
_start_time = time.time()


def persona() -> Dict:
    return PERSONAS.get(CONFIG["persona"], PERSONAS["vikram"])

def sarvam_key() -> str:
    return _KEYS.get("sarvam", "") or os.getenv("SARVAM_API_KEY", "")

def gemini_key() -> str:
    return _KEYS.get("gemini", "") or os.getenv("GEMINI_API_KEY", "")

def public_config() -> Dict:
    return {k: v for k, v in CONFIG.items()}


# ══════════════════════════════════════════════════════════════════════════════
# PCM UTILITIES
# ══════════════════════════════════════════════════════════════════════════════
def _mp3_to_pcm(mp3_bytes: bytes, target_sr: int = 16000) -> bytes:
    """MP3 → raw int16 LE mono PCM. Uses miniaudio (pip install miniaudio)."""
    if not mp3_bytes:
        return b""
    try:
        import miniaudio
        d = miniaudio.mp3_read_s16(mp3_bytes)
        s = np.array(d.samples, dtype=np.int16)
        if d.nchannels == 2:
            s = s.reshape(-1, 2).mean(axis=1).astype(np.int16)
        if d.sample_rate != target_sr:
            n = int(len(s) * target_sr / d.sample_rate)
            s = np.interp(np.linspace(0, len(s), n),
                          np.arange(len(s)), s.astype(np.float32)).astype(np.int16)
        return s.tobytes()
    except ImportError:
        pass
    except Exception as e:
        log.warning("miniaudio: %s", e)
    try:
        from pydub import AudioSegment
        seg = (AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
               .set_frame_rate(target_sr).set_channels(1).set_sample_width(2))
        return seg.raw_data
    except Exception as e:
        log.warning("pydub: %s", e)
    log.error("No MP3 decoder — pip install miniaudio")
    return b""


def _pcm_to_wav(pcm: bytes, sr: int = 16000) -> bytes:
    """Wrap raw PCM in a minimal WAV header (for Sarvam STT which wants WAV)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm)
    return buf.getvalue()


async def _send_pcm(ws, pcm: bytes, addr: str, acc=None) -> bool:
    """
    Stream PCM to ESP32 in 512-byte packets.
    If acc provided and not already muted, mutes for 500ms echo tail.
    Returns False on disconnect.
    """
    pkt   = CONFIG["ws_packet_bytes"]
    ok    = True
    # Pace the send to match playback rate: 512B = 16ms audio @ 16kHz
    # Send every 14ms so ring buffer stays ~2 packets ahead (small lead buffer)
    delay = 0.014
    for i in range(0, len(pcm), pkt):
        try:
            await ws.send(pcm[i:i + pkt])
            await asyncio.sleep(delay)  # pace to playback rate — prevents ring overflow
        except Exception as e:
            spk_log.warning("[%s] send failed at byte %d: %s", addr, i, e)
            ok = False; break
    # Only set mute if caller didn't already set a longer duration
    if acc is not None and not acc.muted:
        acc.mute(0.5)
    return ok


# ══════════════════════════════════════════════════════════════════════════════
# SENTENCE FLUSHER
# ══════════════════════════════════════════════════════════════════════════════
_HARD_END = frozenset('.!?।')
_SOFT_END = frozenset(',;:—')
_HARD_MIN = 8
_SOFT_MIN = 45

def _try_flush(pending: str):
    """Return (chunk, remainder) or (None, pending) if no flush point yet."""
    for i, ch in enumerate(pending):
        if ch == '\n':
            chunk = pending[:i].strip()
            return (chunk, pending[i+1:].lstrip()) if chunk else (None, pending[i+1:].lstrip())
        if ch in _HARD_END and i >= _HARD_MIN - 1:
            nxt = pending[i+1] if i+1 < len(pending) else ' '
            if nxt in ' \n\t' or i+1 == len(pending):
                return pending[:i+1].strip(), pending[i+2:].lstrip() if i+1 < len(pending) else ''
        if ch in _SOFT_END and i >= _SOFT_MIN - 1:
            return pending[:i+1].strip(), pending[i+2:].lstrip() if i+1 < len(pending) else ''
    return None, pending


def _clean_for_tts(text: str) -> str:
    """Strip markdown/emoji that confuse TTS engines."""
    text = re.sub(r'[*_`#>\[\]\\]', '', text)
    text = re.sub(r'[\U0001F000-\U0001FFFF]', '', text)  # remove emoji
    return re.sub(r'\s+', ' ', text).strip()


# ══════════════════════════════════════════════════════════════════════════════
# TTS ENGINE  (edge-tts → raw PCM)
# ══════════════════════════════════════════════════════════════════════════════
async def _tts_sentence(text: str) -> bytes:
    """Convert text to raw PCM int16 LE mono 16kHz."""
    engine = CONFIG["tts_engine"]
    loop   = asyncio.get_running_loop()
    if engine == "pyttsx3":
        return await loop.run_in_executor(None, _pyttsx3_sync, text)
    elif engine == "edge-tts":
        return await loop.run_in_executor(None, _edge_tts_sync_net, text)
    elif engine == "piper":
        return await loop.run_in_executor(None, _piper_sync, text)
    else:
        return await loop.run_in_executor(None, _espeak_sync, text)


def _edge_tts_rate() -> str:
    """Ensure rate has a sign: '0%' → '+0%'."""
    r = str(CONFIG.get("tts_rate", "+0%")).strip().replace(" ", "")
    if r and r[0] not in ("+", "-"):
        r = "+" + r
    import re as _re
    return r if _re.match(r"^[+-]\d+%$", r) else "+0%"


def _pyttsx3_sync(text: str) -> bytes:
    """
    pyttsx3 → raw PCM via Windows SAPI5 (built-in, zero install, <50ms).
    Falls back to edge-tts if pyttsx3 unavailable.
    """
    try:
        import pyttsx3, tempfile
        engine = pyttsx3.init()
        # Map tts_rate (-20%..+30%) to SAPI5 words-per-minute (default ~200)
        rate_str = _edge_tts_rate()  # e.g. "+0%", "-10%"
        rate_pct = int(rate_str.replace("%","").replace("+","") or "0")
        engine.setProperty("rate", max(80, min(400, 200 + int(200 * rate_pct / 100))))
        engine.setProperty("volume", 1.0)
        # Set Indian English voice if available
        voices = engine.getProperty("voices")
        for v in voices:
            if "india" in v.name.lower() or "ravi" in v.name.lower() or "heera" in v.name.lower():
                engine.setProperty("voice", v.id); break
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            out = f.name
        try:
            engine.save_to_file(text, out)
            engine.runAndWait()
            engine.stop()
            with wave.open(out, "rb") as wf:
                raw = wf.readframes(wf.getnframes())
                src_sr = wf.getframerate()
            # Resample to target if needed
            tgt = CONFIG["tts_sample_rate"]
            if src_sr != tgt:
                s = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                n = int(len(s) * tgt / src_sr)
                s = np.interp(np.linspace(0,len(s),n), np.arange(len(s)), s).astype(np.int16)
                raw = s.tobytes()
            return raw
        finally:
            Path(out).unlink(missing_ok=True)
    except Exception as e:
        log.warning("pyttsx3 failed (%s), trying edge-tts", e)
        return _edge_tts_sync_net(text)


def _edge_tts_sync_net(text: str) -> bytes:
    """edge-tts fallback (needs network, ~500ms-3s)."""
    async def _run():
        import edge_tts
        comm = edge_tts.Communicate(text, persona()["voice"],
                                    rate=_edge_tts_rate(), pitch=CONFIG.get("tts_pitch","+0Hz"))
        chunks = []
        async for chunk in comm.stream():
            if chunk["type"] == "audio": chunks.append(chunk["data"])
        return b"".join(chunks)
    loop = asyncio.new_event_loop()
    try:
        mp3 = loop.run_until_complete(_run())
    finally:
        loop.close()
    return _mp3_to_pcm(mp3, CONFIG["tts_sample_rate"]) if mp3 else b""


def _edge_tts_sync(text: str) -> bytes:
    """Primary TTS: pyttsx3 (offline SAPI5), falls back to edge-tts."""
    return _pyttsx3_sync(text)


def _espeak_sync(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    try:
        subprocess.run(["espeak-ng", "-w", out, "-s", "150", "--", text],
                       check=True, capture_output=True, timeout=15)
        with wave.open(out, "rb") as wf:
            return wf.readframes(wf.getnframes())
    except Exception as e:
        log.error("espeak: %s", e); return b""
    finally:
        Path(out).unlink(missing_ok=True)


def _piper_sync(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    try:
        subprocess.run(["piper", "--model", CONFIG["piper_model"], "--output_file", out],
                       input=text.encode(), check=True, capture_output=True, timeout=30)
        with wave.open(out, "rb") as wf:
            return wf.readframes(wf.getnframes())
    except Exception as e:
        log.error("piper: %s", e); return b""
    finally:
        Path(out).unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL PIPELINE  (Whisper STT + Ollama LLM + edge-tts)
# ══════════════════════════════════════════════════════════════════════════════
class _Whisper:
    def __init__(self):
        self._model = None
        self._lock  = None

    def _lk(self):
        if not self._lock:
            self._lock = asyncio.Lock()
        return self._lock

    async def ensure_loaded(self):
        async with self._lk():
            if not self._model:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._load)

    def _load(self):
        cache = Path.home() / ".cache" / "whisper"
        if cache.exists():
            try:
                import torch
                for f in cache.glob("*.pt"):
                    try: torch.load(str(f), map_location="cpu", weights_only=True)
                    except Exception:
                        log.warning("Deleted bad Whisper cache: %s", f)
                        f.unlink(missing_ok=True)
            except ImportError:
                pass  # torch not separately installed; whisper bundles it
        import whisper
        log.info("Loading Whisper '%s'…", CONFIG["whisper_model"])
        self._model = whisper.load_model(CONFIG["whisper_model"])
        log.info("Whisper ready ✓")

    async def transcribe(self, pcm: bytes, sr: int) -> str:
        await self.ensure_loaded()
        return await asyncio.get_running_loop().run_in_executor(None, self._run, pcm, sr)

    def _run(self, pcm: bytes, sr: int) -> str:
        s = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        if sr != 16000:
            n = int(len(s) * 16000 / sr)
            s = np.interp(np.linspace(0, len(s), n), np.arange(len(s)), s).astype(np.float32)
        return self._model.transcribe(s, fp16=False, language="en").get("text", "").strip()

_whisper = _Whisper()


async def _local_stream(text: str, ws, addr: str, history: list, t0: float):
    """
    Latency-optimised pipeline:
      1. Collect full LLM reply (streaming tokens, fast)
      2. ONE edge-tts call → single MS network round trip (was N calls)
      3. Stream PCM in 512B packets → device plays immediately

    Per-sentence TTS was slower because each sentence = 1 HTTPS round trip
    to Microsoft (~500-2000ms each). With gemma2:2b + 1-sentence system prompt,
    batching gives: LLM(~1s) + TTS(~500ms) = ~1.5s total.
    """
    msgs = [{"role": "system", "content": persona()["system"]}]
    msgs += history[-16:]
    msgs.append({"role": "user", "content": text})

    # ── 1. Collect full LLM reply ────────────────────────────────────────────
    full_reply = ""
    try:
        async with ClientSession() as s:
            async with s.post(
                f"{CONFIG['ollama_host']}/api/chat",
                json={"model": CONFIG["ollama_model"], "messages": msgs, "stream": True},
                timeout=60,
            ) as r:
                async for raw in r.content:
                    raw = raw.strip()
                    if not raw: continue
                    try: obj = json.loads(raw)
                    except: continue
                    if "error" in obj:
                        full_reply = f"Model error: {obj['error']}"
                        break
                    full_reply += obj.get("message", {}).get("content", "")
                    if obj.get("done"): break
    except Exception as e:
        log.error("Ollama: %s", e)
        full_reply = "Ollama is not running, yaar."

    reply = full_reply.strip()
    t_llm = (time.monotonic()-t0)*1000
    spk_log.info('[%s] 💬 "%s"  (LLM %.0fms)', addr, reply[:80], t_llm)

    if not reply:
        return

    # Save to history
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant",  "content": reply})
    if len(history) > 20: history[:] = history[-20:]

    # ── 2. ONE TTS call for the complete reply ───────────────────────────────
    clean = _clean_for_tts(reply)
    if not clean:
        return

    t1 = time.monotonic()
    pcm = await _tts_sentence(clean)
    t_tts = (time.monotonic()-t1)*1000
    t_tot = (time.monotonic()-t0)*1000

    if not pcm:
        spk_log.warning("[%s] TTS empty for: %r", addr, clean[:40])
        try: await ws.send("END")
        except: pass
        return

    spk_log.info('[%s] 🔊 "%s"  LLM=%.0fms  TTS=%.0fms  TOTAL=%.0fms',
                 addr, clean[:40], t_llm, t_tts, t_tot)

    # ── 3. Stream PCM → device, mute mic for playback duration + tail ────────
    acc  = _get_acc(ws)
    # Estimate playback duration: PCM bytes / (sr * 2 bytes/sample)
    play_secs = len(pcm) / (CONFIG["tts_sample_rate"] * 2)
    if acc:
        acc.mute(play_secs + 1.5)   # cover full playback + 1.5s echo tail

    await _send_pcm(ws, pcm, addr)   # acc mute already set above, skip double-mute
    try: await ws.send("END")
    except: pass

    spk_log.info('[%s] ✔ done  %.0fms  (%.1fs audio)',
                 addr, (time.monotonic()-t0)*1000, play_secs)


# ══════════════════════════════════════════════════════════════════════════════
# SARVAM PIPELINE
# Full streaming: STT WS (pcm_s16le) → sarvam-m chat → TTS WS (output pcm)
# ══════════════════════════════════════════════════════════════════════════════
async def _sarvam_stt(pcm: bytes, sr: int) -> str:
    """Sarvam streaming STT — sends raw PCM, returns transcript."""
    key = sarvam_key()
    if not key:
        return "[no sarvam key]"
    try:
        from sarvamai import AsyncSarvamAI
        client = AsyncSarvamAI(api_subscription_key=key)
        wav_b64 = base64.b64encode(_pcm_to_wav(pcm, sr)).decode()
        async with client.speech_to_text_streaming.connect(
            model=CONFIG["sarvam_stt_model"],
            mode="transcribe",
            language_code=CONFIG["sarvam_language"],
            high_vad_sensitivity=True,
        ) as ws:
            await ws.transcribe(audio=wav_b64, encoding="audio/wav", sample_rate=sr)
            await ws.flush()
            async for msg in ws:
                if isinstance(msg, dict):
                    t = msg.get("transcript") or msg.get("text", "")
                    if t: return t.strip()
                elif hasattr(msg, "transcript"):
                    return msg.transcript.strip()
    except ImportError:
        # Fallback: REST API
        return await _sarvam_stt_rest(pcm, sr)
    except Exception as e:
        log.error("Sarvam STT: %s", e)
        return ""
    return ""


async def _sarvam_stt_rest(pcm: bytes, sr: int) -> str:
    """Sarvam REST STT fallback."""
    key = sarvam_key()
    if not key: return ""
    import aiohttp
    wav_bytes = _pcm_to_wav(pcm, sr)
    form = aiohttp.FormData()
    form.add_field("file", wav_bytes, filename="audio.wav", content_type="audio/wav")
    form.add_field("model", "saaras:v3")
    form.add_field("language_code", CONFIG["sarvam_language"])
    try:
        async with ClientSession() as s:
            async with s.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": key},
                data=form, timeout=20,
            ) as r:
                d = await r.json()
                return d.get("transcript", "").strip()
    except Exception as e:
        log.error("Sarvam STT REST: %s", e)
        return ""


async def _sarvam_chat(text: str, history: list) -> str:
    """Sarvam-m chat completion."""
    key = sarvam_key()
    if not key: return "No Sarvam API key set."
    msgs = [{"role": "system", "content": persona()["system"]}]
    msgs += history[-16:]
    msgs.append({"role": "user", "content": text})
    try:
        async with ClientSession() as s:
            async with s.post(
                "https://api.sarvam.ai/v1/chat/completions",
                headers={"api-subscription-key": key, "Content-Type": "application/json"},
                json={"model": CONFIG["sarvam_chat_model"], "messages": msgs},
                timeout=30,
            ) as r:
                d = await r.json()
                if "choices" in d:
                    reply = d["choices"][0]["message"]["content"].strip()
                    history.append({"role": "user", "content": text})
                    history.append({"role": "assistant", "content": reply})
                    if len(history) > 20: history[:] = history[-20:]
                    return reply
                log.error("Sarvam chat response: %s", d)
    except Exception as e:
        log.error("Sarvam chat: %s", e)
    return "Sarvam API is not responding."


async def _sarvam_tts_ws(text: str) -> bytes:
    """
    Sarvam TTS WS — output_audio_codec=pcm gives raw PCM directly.
    No decode step, minimum latency, clean audio.
    """
    key = sarvam_key()
    if not key: return b""
    try:
        from sarvamai import AsyncSarvamAI, AudioOutput
        client = AsyncSarvamAI(api_subscription_key=key)
        spk = persona()["sarvam_speaker"]
        lang = CONFIG["sarvam_language"]
        pcm_chunks = []
        async with client.text_to_speech_streaming.connect(
            model=CONFIG["sarvam_tts_model"],
            send_completion_event=True,
        ) as ws:
            await ws.configure(
                target_language_code=lang,
                speaker=spk,
                output_audio_codec="pcm",        # raw PCM — no decode needed!
                min_buffer_size=20,
                max_chunk_length=200,
                pace=float(CONFIG.get("tts_rate", "0%").replace("%","").replace("+","") or "0") / 100 + 1.0,
            )
            await ws.convert(text)
            await ws.flush()
            async for msg in ws:
                if isinstance(msg, AudioOutput):
                    pcm_chunks.append(base64.b64decode(msg.data.audio))
                elif hasattr(msg, "data") and hasattr(msg.data, "event_type"):
                    if msg.data.event_type == "final":
                        break
        return b"".join(pcm_chunks)
    except ImportError:
        # Fallback: REST TTS then decode
        return await _sarvam_tts_rest(text)
    except Exception as e:
        log.error("Sarvam TTS WS: %s", e)
        return await _sarvam_tts_rest(text)


async def _sarvam_tts_rest(text: str) -> bytes:
    """Sarvam TTS REST fallback — returns WAV PCM."""
    key = sarvam_key()
    if not key: return b""
    try:
        async with ClientSession() as s:
            async with s.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": key, "Content-Type": "application/json"},
                json={
                    "inputs": [text],
                    "target_language_code": CONFIG["sarvam_language"],
                    "model": CONFIG["sarvam_tts_model"],
                    "speaker": persona()["sarvam_speaker"],
                    "enable_preprocessing": True,
                },
                timeout=20,
            ) as r:
                d = await r.json()
                wav = base64.b64decode(d["audios"][0])
                with wave.open(io.BytesIO(wav), "rb") as wf:
                    return wf.readframes(wf.getnframes())
    except Exception as e:
        log.error("Sarvam TTS REST: %s", e)
        return b""


async def _sarvam_stream(text: str, ws, addr: str, history: list, t0: float):
    """Sarvam full pipeline with sentence-level streaming TTS."""
    msgs = [{"role": "system", "content": persona()["system"]}]
    msgs += history[-16:]
    msgs.append({"role": "user", "content": text})

    # Get full reply (Sarvam chat is not streaming token-by-token)
    reply = await _sarvam_chat(text, history)
    spk_log.info('[%s] Sarvam 💬 "%s"  (%.0fms)', addr, reply[:80], (time.monotonic()-t0)*1000)

    # Stream sentences through Sarvam TTS WS in parallel
    sentences = []
    pending = reply
    while pending:
        chunk, pending = _try_flush(pending)
        if chunk: sentences.append(chunk)
        else:
            if pending: sentences.append(pending)
            break

    # Run TTS for each sentence concurrently, stream in order
    async def tts_and_send(sentence: str, order_event: asyncio.Event, prev_event: asyncio.Event):
        clean = _clean_for_tts(sentence)
        if not clean: order_event.set(); return
        t1 = time.monotonic()
        pcm = await _sarvam_tts_ws(clean)
        ms = (time.monotonic()-t1)*1000
        # Wait for previous sentence to finish sending before we send ours
        await prev_event.wait()
        if pcm:
            spk_log.info('[%s] 🔊 Sarvam %.0fms', addr, ms)
            await _send_pcm(ws, pcm, addr)
        order_event.set()

    prev = asyncio.Event(); prev.set()  # first sentence has no predecessor
    events = []
    tasks = []
    for s in sentences:
        ev = asyncio.Event()
        events.append(ev)
        tasks.append(asyncio.ensure_future(tts_and_send(s, ev, prev)))
        prev = ev

    if tasks:
        await asyncio.gather(*tasks)
    try: await ws.send("END")
    except Exception: pass
    spk_log.info('[%s] Sarvam ✔ %.0fms', addr, (time.monotonic()-t0)*1000)


# ══════════════════════════════════════════════════════════════════════════════
# GEMINI PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
async def _gemini_stream(text: str, ws, addr: str, history: list, t0: float):
    key = gemini_key()
    if not key:
        await _fallback_stream("No Gemini API key set.", ws, addr, t0)
        return
    msgs = [{"role": "system", "content": persona()["system"]}]
    msgs += history[-16:]
    msgs.append({"role": "user", "content": text})
    try:
        model = CONFIG["gemini_model"].replace("-live-", "-").replace("live-", "")
        url   = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                 f"{model}:generateContent?key={key}")
        async with ClientSession() as s:
            async with s.post(url, json={
                "contents":     [{"parts": [{"text": text}]}],
                "systemInstruction": {"parts": [{"text": persona()["system"]}]},
                "generationConfig": {"maxOutputTokens": 60},
            }, timeout=30) as r:
                d = await r.json()
                reply = d["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        log.error("Gemini: %s", e)
        reply = "Gemini is not responding."
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20: history[:] = history[-20:]
    await _fallback_stream(reply, ws, addr, t0)


async def _fallback_stream(reply: str, ws, addr: str, t0: float):
    """edge-tts sentence streaming for pipelines that don't have native TTS streaming."""
    pending = reply
    first = True
    while pending:
        chunk, pending = _try_flush(pending)
        if not chunk:
            if pending: chunk, pending = pending, ""
            else: break
        clean = _clean_for_tts(chunk)
        if not clean: continue
        t1 = time.monotonic()
        pcm = await _tts_sentence(clean)
        if pcm:
            ms = (time.monotonic()-t1)*1000
            tot = (time.monotonic()-t0)*1000
            if first:
                spk_log.info('[%s] 🔊 FIRST  TTS=%.0fms  TOTAL=%.0fms', addr, ms, tot)
                first = False
            await _send_pcm(ws, pcm, addr)
    try: await ws.send("END")
    except Exception: pass
    # Mute is already set by _send_pcm calls above


# ══════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL PIPELINE DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════
async def run_pipeline(pcm: bytes, ws, sr: int, addr: str):
    if not pcm: return
    t0      = time.monotonic()
    history = CONV_HISTORY.setdefault(id(ws), [])
    pipe    = CONFIG["pipeline"]

    try:
        # ── STT ───────────────────────────────────────────────────────────────
        if pipe == "sarvam":
            mic_log.info("[%s] ⟳ Sarvam STT %.2fs", addr, len(pcm)/(sr*2))
            text = await _sarvam_stt(pcm, sr)
        else:
            mic_log.info("[%s] ⟳ Whisper STT %.2fs", addr, len(pcm)/(sr*2))
            text = await _whisper.transcribe(pcm, sr)

        t_stt = (time.monotonic()-t0)*1000
        if not text:
            mic_log.info("[%s] ↷ empty transcript  %.0fms", addr, t_stt)
            return
        mic_log.info('[%s] ✔ "%s"  STT=%.0fms', addr, text, t_stt)

        # ── LLM + TTS ─────────────────────────────────────────────────────────
        if pipe == "sarvam":
            await _sarvam_stream(text, ws, addr, history, t0)
        elif pipe == "gemini":
            await _gemini_stream(text, ws, addr, history, t0)
        else:
            await _local_stream(text, ws, addr, history, t0)

    except websockets.exceptions.ConnectionClosed:
        log.info("[%s] disconnected mid-pipeline", addr)
    except Exception as e:
        log.error("[%s] pipeline error: %s", addr, e, exc_info=True)
        try: await ws.send("END")
        except: pass


# ══════════════════════════════════════════════════════════════════════════════
# VAD ACCUMULATOR
# ══════════════════════════════════════════════════════════════════════════════
_BAR = 26
def _rms(data: bytes) -> float:
    if len(data) < 2: return 0.0
    return float(np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float32)**2)))

def _bar(rms: float, thr: float) -> str:
    n = min(_BAR, int(rms/1000*_BAR))
    return f"|{'█'*n}{'░'*(_BAR-n)}| {rms:5.0f}{'  ◀' if rms>=thr else ''}"


class Accumulator:
    def __init__(self, ws, sr: int, addr: str):
        self.ws  = ws; self.sr = sr; self.addr = addr
        self.buf = bytearray()
        self.sil = 0; self.spk = 0
        self.in_speech = False
        self._last_log = 0.0
        self.muted = False          # True while TTS is playing → suppress VAD
        self._mute_until = 0.0      # epoch time — mute for at least this long

    def mute(self, seconds: float = 0.5):
        """Suppress VAD for `seconds` after TTS ends (echo tail)."""
        self.muted = True
        self._mute_until = time.monotonic() + seconds

    def unmute(self):
        self.muted = False
        self.buf.clear(); self.sil = 0; self.spk = 0; self.in_speech = False

    async def feed(self, data: bytes):
        # Auto-unmute when mute period expires
        if self.muted and time.monotonic() > self._mute_until:
            self.unmute()

        rms = _rms(data)
        thr = CONFIG["vad_speech_rms"]
        now = time.monotonic()
        if now - self._last_log >= 0.5:
            self._last_log = now
            mute_tag = " [MUTED-echo]" if self.muted else ""
            mic_log.info("[%s] %s%s", self.addr, _bar(rms, thr), mute_tag)

        if self.muted:
            return  # discard mic data during TTS playback

        self.buf.extend(data)
        is_spk = rms >= thr

        if is_spk:
            self.spk += 1; self.sil = 0
            if not self.in_speech:
                self.in_speech = True
                mic_log.info("[%s] ▶ START rms=%.0f", self.addr, rms)
        else:
            if self.in_speech:
                self.sil += 1
                if self.sil >= CONFIG["vad_silence_frames"]:
                    self.in_speech = False
                    dur = len(self.buf)/(self.sr*2)
                    mic_log.info("[%s] ■ END spk=%d dur=%.1fs", self.addr, self.spk, dur)
                    if self.spk >= CONFIG["vad_min_speech"]:
                        utt = bytes(self.buf)
                        self.buf.clear(); self.sil = 0; self.spk = 0
                        # Fire pipeline as background task — NEVER block read loop
                        asyncio.ensure_future(run_pipeline(utt, self.ws, self.sr, self.addr))
                    else:
                        mic_log.info("[%s] ↷ too short", self.addr)
                        self.buf.clear(); self.sil = 0; self.spk = 0

        # 8s hard cap (only if speech detected)
        if len(self.buf) > self.sr*2*8:
            if self.spk >= CONFIG["vad_min_speech"]:
                mic_log.info("[%s] ⚠ 8s cap", self.addr)
                utt = bytes(self.buf)
                self.buf.clear(); self.sil = 0; self.spk = 0; self.in_speech = False
                asyncio.ensure_future(run_pipeline(utt, self.ws, self.sr, self.addr))
            else:
                self.buf.clear(); self.sil = 0; self.spk = 0; self.in_speech = False


# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET HANDLER
# ══════════════════════════════════════════════════════════════════════════════
async def ws_handler(ws):
    addr = str(ws.remote_address)
    log.info("Connected: %s  [%s / %s]", addr, CONFIG["pipeline"], persona()["name"])
    CONNECTED_DEVICES.add(ws)
    DEVICE_INFO[id(ws)] = {"addr": addr, "connected_at": time.time(),
                           "pipeline": CONFIG["pipeline"],
                           "persona": CONFIG["persona"], "_ws": ws}
    CONV_HISTORY[id(ws)] = []
    sr  = CONFIG["sample_rate"]
    acc = Accumulator(ws, sr, addr)
    DEVICE_INFO[id(ws)]["_acc"] = acc  # store for echo suppression in pipeline

    for cmd in [f"CMD:CHUNK_SIZE:{CONFIG['chunk_size']}",
                f"CMD:VOLUME:{CONFIG['volume']}",
                f"CMD:PIPELINE:{CONFIG['pipeline']}"]:
        try: await ws.send(cmd)
        except: pass

    # Semaphore: only one pipeline at a time per device
    _pipeline_sem = asyncio.Semaphore(1)

    async def _run_bg(pcm_bytes: bytes, sr_val: int):
        """Run full pipeline in background — never blocks the read loop."""
        async with _pipeline_sem:
            await run_pipeline(pcm_bytes, ws, sr_val, addr)

    try:
        async for msg in ws:
            if isinstance(msg, bytes):
                # acc.feed() is fast (just RMS + buffer append); safe to await
                await acc.feed(msg)
            elif isinstance(msg, str):
                if msg.startswith("HELLO:"):
                    parts = dict(p.split("=",1) for p in msg[6:].split(";") if "=" in p)
                    DEVICE_INFO[id(ws)].update(parts)
                    if "sr" in parts:
                        try: sr = int(parts["sr"]); acc.sr = sr
                        except: pass
                    log.info("Hello from %s: %s", addr, parts)
                elif msg.startswith("TEXT:"):
                    text = msg[5:].strip()
                    hist = CONV_HISTORY.setdefault(id(ws), [])
                    asyncio.ensure_future(_run_bg(text.encode(), sr))
                elif msg in ("RECORD_DONE","RECORD_FAIL"):
                    log.info("[%s] %s", addr, msg)
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.error("[%s] handler: %s", addr, e, exc_info=True)
    finally:
        CONNECTED_DEVICES.discard(ws)
        DEVICE_INFO.pop(id(ws), None)
        CONV_HISTORY.pop(id(ws), None)
        log.info("Disconnected: %s", addr)


# ══════════════════════════════════════════════════════════════════════════════
# REST API
# ══════════════════════════════════════════════════════════════════════════════
def _ok(d=None):  return web.Response(text=json.dumps(d or {"ok":True}), content_type="application/json")
def _err(m, s=400): return web.Response(text=json.dumps({"error":m}), content_type="application/json", status=s)

async def _push(cmd: str):
    dead = set()
    for ws in list(CONNECTED_DEVICES):
        try: await ws.send(cmd)
        except: dead.add(ws)
    CONNECTED_DEVICES.difference_update(dead)

def _get_acc(ws) -> "Accumulator | None":
    """Get the Accumulator for a WebSocket connection (for echo suppression)."""
    info = DEVICE_INFO.get(id(ws))
    return info.get("_acc") if info else None

async def api_get_config(r):  return _ok(public_config())
async def api_post_config(r):
    try: body = await r.json()
    except: return _err("Invalid JSON")
    changed = []
    for k, v in body.items():
        if k in CONFIG:
            CONFIG[k] = v
            changed.append(k)
    tasks = []
    if "chunk_size"  in changed: tasks.append(_push(f"CMD:CHUNK_SIZE:{CONFIG['chunk_size']}"))
    if "volume"      in changed: tasks.append(_push(f"CMD:VOLUME:{CONFIG['volume']}"))
    if "pipeline"    in changed: tasks.append(_push(f"CMD:PIPELINE:{CONFIG['pipeline']}"))
    if "sample_rate" in changed: tasks.append(_push(f"CMD:SAMPLE_RATE:{CONFIG['sample_rate']}"))
    if "gain_shift"  in changed: tasks.append(_push(f"CMD:GAIN_SHIFT:{CONFIG['gain_shift']}"))
    if tasks: await asyncio.gather(*tasks)
    return _ok({"changed": changed})

async def api_status(r):
    devs = [{"addr":i.get("addr","?"),"pipeline":i.get("pipeline","?"),
              "persona":i.get("persona","?"),"connected_at":i.get("connected_at",0),
              "conv_turns":len(CONV_HISTORY.get(k,[]))//2}
             for k,i in DEVICE_INFO.items()]
    return _ok({"pipeline":CONFIG["pipeline"],"persona":CONFIG["persona"],
                "persona_name":persona()["name"],"devices_online":len(CONNECTED_DEVICES),
                "devices":devs,"uptime_s":int(time.time()-_start_time),
                "config_snapshot":public_config()})

async def api_pipeline(r):
    try: body = await r.json()
    except: return _err("Invalid JSON")
    p = body.get("pipeline","")
    if p not in ("local","sarvam","gemini"): return _err("local|sarvam|gemini")
    CONFIG["pipeline"] = p; await _push(f"CMD:PIPELINE:{p}")
    return _ok({"pipeline":p})

async def api_persona(r):
    try: body = await r.json()
    except: return _err("Invalid JSON")
    p = body.get("persona","")
    if p not in PERSONAS: return _err(f"persona: {list(PERSONAS)}")
    CONFIG["persona"] = p
    return _ok({"persona":p,"name":PERSONAS[p]["name"],"voice":PERSONAS[p]["voice"]})

async def api_get_personas(r):
    return _ok({k:{"name":v["name"],"voice":v["voice"],"gender":v["gender"]} for k,v in PERSONAS.items()})

async def api_tts_rate(r):
    try:
        body = await r.json()
        raw = str(body.get("rate", "+0%")).strip()
        if raw and raw[0] not in ("+", "-"): raw = "+" + raw
        CONFIG["tts_rate"] = raw
        return _ok({"tts_rate": CONFIG["tts_rate"]})
    except: return _err("Body: {rate: '+10%'}")

# ── API KEY MANAGEMENT ────────────────────────────────────────────────────────
async def api_get_keys(r):
    # Never expose actual keys — just show if set
    return _ok({
        "sarvam_set":  bool(sarvam_key()),
        "gemini_set":  bool(gemini_key()),
        "sarvam_hint": ("•"*8 + sarvam_key()[-4:]) if sarvam_key() else "",
        "gemini_hint": ("•"*8 + gemini_key()[-4:]) if gemini_key() else "",
    })

async def api_set_keys(r):
    try: body = await r.json()
    except: return _err("Invalid JSON")
    changed = []
    if "sarvam" in body and body["sarvam"]:
        _KEYS["sarvam"] = body["sarvam"].strip(); changed.append("sarvam")
    if "gemini" in body and body["gemini"]:
        _KEYS["gemini"] = body["gemini"].strip(); changed.append("gemini")
    if changed:
        _save_keys(_KEYS)
        log.info("API keys updated: %s", changed)
    return _ok({"saved": changed})

# ── OTHER ENDPOINTS ───────────────────────────────────────────────────────────
async def api_get_volume(r): return _ok({"volume":CONFIG["volume"]})
async def api_set_volume(r):
    try:
        v = int((await r.json())["volume"]); assert 0<=v<=200
        CONFIG["volume"] = v; await _push(f"CMD:VOLUME:{v}"); return _ok({"volume":v})
    except: return _err("Int 0-200")

async def api_get_chunk(r): return _ok({"chunk_size":CONFIG["chunk_size"]})
async def api_set_chunk(r):
    try:
        v = int((await r.json())["chunk_size"]); assert 64<=v<=3200 and v%2==0
        CONFIG["chunk_size"] = v; await _push(f"CMD:CHUNK_SIZE:{v}"); return _ok({"chunk_size":v})
    except: return _err("Even int 64-3200")

async def api_get_sr(r): return _ok({"sample_rate":CONFIG["sample_rate"]})
async def api_set_sr(r):
    try:
        v = int((await r.json())["sample_rate"]); assert v in (8000,16000,22050,44100)
        CONFIG["sample_rate"] = v; await _push(f"CMD:SAMPLE_RATE:{v}"); return _ok({"sample_rate":v})
    except: return _err("8000|16000|22050|44100")

async def api_tone(r):    await _push("CMD:TONE");   return _ok()
async def api_karaoke(r):
    b = {}
    try: b = await r.json()
    except: pass
    en = b.get("enable",True); await _push("CMD:KARAOKE" if en else "CMD:STOPK"); return _ok({"karaoke":en})

async def api_reboot(r):  await _push("CMD:REBOOT"); return _ok({"rebooting":True})
async def api_ota(r):
    try: url=(await r.json())["url"]; await _push(f"CMD:OTA_URL:{url}"); return _ok({"ota_triggered":url})
    except: return _err("Need 'url'")

async def api_sessions(r):
    return _ok({"sessions":[{"addr":i.get("addr","?"),"pipeline":i.get("pipeline","?"),
                "persona":i.get("persona","?"),"connected_at":i.get("connected_at",0),
                "conv_turns":len(CONV_HISTORY.get(k,[]))//2,"session_id":k}
               for k,i in DEVICE_INFO.items()], "count":len(DEVICE_INFO)})

async def api_cmd(r):
    try: body=await r.json()
    except: return _err("Invalid JSON")
    cmd=body.get("cmd","").strip()
    if not cmd: return _err("'cmd' required")
    if not cmd.startswith("CMD:") and cmd!="END": cmd=f"CMD:{cmd}"
    await _push(cmd); return _ok({"sent":cmd,"devices":len(CONNECTED_DEVICES)})

async def api_ollama_status(r):
    host=CONFIG.get("ollama_host","http://localhost:11434")
    try:
        async with ClientSession() as s:
            async with s.get(f"{host}/api/tags",timeout=3) as resp:
                if resp.status==200:
                    d=await resp.json(); models=[m["name"] for m in d.get("models",[])]
                    return _ok({"reachable":True,"host":host,"models":models,
                                "active_model":CONFIG.get("ollama_model"),
                                "model_loaded":CONFIG.get("ollama_model") in models})
                return _ok({"reachable":False,"host":host,"error":f"HTTP {resp.status}"})
    except Exception as e: return _ok({"reachable":False,"host":host,"error":str(e)})

async def api_get_vad(r):
    keys=("vad_speech_rms","vad_silence_frames","vad_min_speech")
    return _ok({k:CONFIG[k] for k in keys})
async def api_set_vad(r):
    try: body=await r.json()
    except: return _err("Invalid JSON")
    for k in ("vad_speech_rms","vad_silence_frames","vad_min_speech"):
        if k in body: CONFIG[k]=int(body[k])
    return _ok({k:CONFIG[k] for k in ("vad_speech_rms","vad_silence_frames","vad_min_speech")})

async def api_clear_history(r):
    for k in list(CONV_HISTORY): CONV_HISTORY[k]=[]
    return _ok({"cleared":True})

async def api_upload(r):
    data=await r.read()
    if len(data)<44: return _err("Too small",400)
    p=Path(f"/tmp/rec_{int(time.time())}.wav"); p.write_bytes(data)
    try:
        with wave.open(str(p),"rb") as wf: sr=wf.getframerate(); pcm=wf.readframes(wf.getnframes())
        asyncio.ensure_future(_whisper.transcribe(pcm,sr))
    except Exception as e: log.error("Upload: %s",e)
    return _ok({"saved":str(p)})


# ══════════════════════════════════════════════════════════════════════════════
# APP FACTORY
# ══════════════════════════════════════════════════════════════════════════════
def make_app():
    app = web.Application()

    @web.middleware
    async def cors(req, handler):
        if req.method=="OPTIONS":
            return web.Response(status=204, headers={
                "Access-Control-Allow-Origin":"*",
                "Access-Control-Allow-Methods":"GET,POST,OPTIONS",
                "Access-Control-Allow-Headers":"Content-Type"})
        resp = await handler(req)
        resp.headers["Access-Control-Allow-Origin"]  = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    app.middlewares.append(cors)
    dash = _HERE.parent / "dashboard" / "index.html"
    if dash.exists():
        app.router.add_get("/", lambda r: web.FileResponse(str(dash)))

    R = app.router
    R.add_get ("/api/config",           api_get_config)
    R.add_post("/api/config",           api_post_config)
    R.add_get ("/api/status",           api_status)
    R.add_post("/api/pipeline",         api_pipeline)
    R.add_get ("/api/personas",         api_get_personas)
    R.add_post("/api/persona",          api_persona)
    R.add_post("/api/tts/rate",         api_tts_rate)
    R.add_get ("/api/keys",             api_get_keys)
    R.add_post("/api/keys",             api_set_keys)
    R.add_post("/api/upload-recording", api_upload)
    R.add_get ("/api/audio/chunk_size", api_get_chunk)
    R.add_post("/api/audio/chunk_size", api_set_chunk)
    R.add_get ("/api/audio/volume",     api_get_volume)
    R.add_post("/api/audio/volume",     api_set_volume)
    R.add_get ("/api/audio/sample_rate",api_get_sr)
    R.add_post("/api/audio/sample_rate",api_set_sr)
    R.add_post("/api/audio/tone",       api_tone)
    R.add_post("/api/audio/karaoke",    api_karaoke)
    R.add_post("/api/device/reboot",    api_reboot)
    R.add_post("/api/device/ota",       api_ota)
    R.add_get ("/api/sessions",         api_sessions)
    R.add_post("/api/cmd",              api_cmd)
    R.add_get ("/api/ollama/status",    api_ollama_status)
    R.add_get ("/api/vad",              api_get_vad)
    R.add_post("/api/vad",              api_set_vad)
    R.add_post("/api/history/clear",    api_clear_history)
    R.add_route("OPTIONS","/{p:.*}", lambda r: web.Response(status=204))
    return app


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
async def main():
    p = persona()
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  Voice Assistant  v23  (pyttsx3+bg tasks)    ║")
    log.info("║  Persona  : %-30s║", f"{p['name']}  ({p['voice']})")
    log.info("║  Model    : %-30s║", CONFIG["ollama_model"])
    log.info("║  Pipeline : %-30s║", CONFIG["pipeline"])
    log.info("║  Audio    : PCM s16le mono 16kHz (zero-copy)  ║")
    log.info("╚══════════════════════════════════════════════╝")
    log.info("WS  ws://0.0.0.0:%d   HTTP  http://0.0.0.0:%d/", CONFIG["ws_port"], CONFIG["http_port"])
    if not sarvam_key(): log.warning("Sarvam API key not set — use dashboard /api/keys")
    if not gemini_key(): log.warning("Gemini API key not set — use dashboard /api/keys")

    log.info("Pre-loading Whisper '%s'…", CONFIG["whisper_model"])
    loop = asyncio.get_running_loop()
    asyncio.ensure_future(loop.run_in_executor(None, _whisper._load))

    ws_server = await websockets.serve(
        ws_handler, "0.0.0.0", CONFIG["ws_port"],
        ping_interval=25, ping_timeout=10, max_size=2*1024*1024)

    runner = web.AppRunner(make_app())
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", CONFIG["http_port"]).start()

    import webbrowser, threading
    url = f"http://localhost:{CONFIG['http_port']}/"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    log.info("Dashboard: %s", url)
    log.info("Ready — speak to %s!", p["name"])
    await asyncio.Event().wait()


def _handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    # Don't crash the server on pipeline errors — just log them
    if "ssl" in str(msg).lower() or "connection" in str(msg).lower():
        log.debug("Async exception (suppressed): %s", msg)
    else:
        log.error("Async exception: %s", msg)

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        loop.set_exception_handler(_handle_exception)
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        log.info("Stopped")
    finally:
        loop.close()
