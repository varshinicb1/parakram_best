"""
Voice Routes — Sarvam AI STT/TTS integration for voice-driven firmware generation.
"""

import os
import aiohttp
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter()

SARVAM_API_KEY = os.environ.get(
    "SARVAM_API_KEY",
    "sk_9lft95ib_fsuLWDFQuq9CW7Qlr8UunLjx"
)
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text-translate"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio to text using Sarvam AI Speech-to-Text."""
    if not SARVAM_API_KEY:
        raise HTTPException(status_code=500, detail="Sarvam API key not configured")

    audio_data = await file.read()

    try:
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
        }

        form = aiohttp.FormData()
        form.add_field("file", audio_data, filename=file.filename or "audio.wav",
                       content_type=file.content_type or "audio/wav")
        form.add_field("model", "saaras:v2")
        form.add_field("language_code", "en-IN")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                SARVAM_STT_URL,
                data=form,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "transcript": data.get("transcript", ""),
                        "language": data.get("language_code", "en-IN"),
                    }
                else:
                    body = await resp.text()
                    print(f"[Sarvam STT] HTTP {resp.status}: {body[:300]}")
                    raise HTTPException(status_code=resp.status,
                                        detail=f"Sarvam STT error: {body[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Sarvam STT] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


class TTSRequest(BaseModel):
    text: str
    language: str = "en-IN"
    speaker: str = "meera"


@router.post("/synthesize")
async def synthesize_speech(req: TTSRequest):
    """Convert text to speech using Sarvam AI TTS."""
    if not SARVAM_API_KEY:
        raise HTTPException(status_code=500, detail="Sarvam API key not configured")

    try:
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": [req.text],
            "target_language_code": req.language,
            "speaker": req.speaker,
            "model": "bulbul:v1",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                SARVAM_TTS_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    audios = data.get("audios", [])
                    return {
                        "audio_base64": audios[0] if audios else "",
                        "format": "wav",
                    }
                else:
                    body = await resp.text()
                    raise HTTPException(status_code=resp.status,
                                        detail=f"Sarvam TTS error: {body[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")
