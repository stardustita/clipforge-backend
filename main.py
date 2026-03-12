# main.py — ClipForge AI Backend (Lazy Init + Logging Definitivo)
import logging
import traceback
import os
import uuid
import glob
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# LOGGING DEFINITIVO — visibile nei log Render
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("clipforge")

# ============================================================
# APP FASTAPI
# ============================================================
app = FastAPI(title="ClipForge AI Backend", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path("temp").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)
Path("clips").mkdir(exist_ok=True)

# ============================================================
# LAZY INIT GLOBALS
# ============================================================
_whisper = None
_gemini = None
_video = None

# ============================================================
# MOCK FALLBACK (solo se servizio reale fallisce)
# ============================================================
class MockWhisper:
    def transcribe_video(self, path: str) -> str:
        logger.warning("⚠️ WhisperService NON disponibile — uso MOCK")
        return "00:00 Mock trascrizione — Whisper non caricato correttamente."

class MockGemini:
    def find_viral_moments(self, transcript: str, max_clips: int = 3):
        logger.warning("⚠️ GeminiService NON disponibile — uso MOCK")
        return [
            {"start_time": "00:00", "end_time": "00:30", "viral_score": 0,
             "reason": "MOCK — Gemini non caricato", "transcript_snippet": transcript[:100]}
        ]

class MockVideo:
    def generate_clip(self, video_path: str, output_path: str, start: str, end: str):
        logger.warning("⚠️ VideoService NON disponibile — creo clip mock vuota")
        Path(output_path).touch()

# ============================================================
# LAZY GETTERS CON LOGGING DETTAGLIATO
# ============================================================
async def get_whisper():
    global _whisper
    if _whisper is None:
        try:
            logger.info("⏳ Caricamento WhisperService...")
            from services.whisper_service import WhisperService
            _whisper = WhisperService()
            logger.info("✅ WhisperService caricato correttamente")
        except Exception as e:
            logger.error(f"❌ WhisperService FALLITO: {e}")
            logger.error(traceback.format_exc())
            _whisper = MockWhisper()
    return _whisper

async def get_gemini():
    global _gemini
    if _gemini is None:
        try:
            logger.info("⏳ Caricamento GeminiService...")
            from services.gemini_service import GeminiService
            _gemini = GeminiService()
            logger.info("✅ GeminiService caricato correttamente")
        except Exception as e:
            logger.error(f"❌ GeminiService FALLITO: {e}")
            logger.error(traceback.format_exc())
            _gemini = MockGemini()
    return _gemini

async def get_video():
    global _video
    if _video is None:
        try:
            logger.info("⏳ Caricamento VideoService...")
            from services.video_service import VideoService
            _video = VideoService()
            logger.info("✅ VideoService caricato correttamente")
        except Exception as e:
            logger.error(f"❌ VideoService FALLITO: {e}")
            logger.error(traceback.format_exc())
            _video = MockVideo()
    return _video

# ============================================================
# ROUTES
# ============================================================

@app.get("/")
def home():
    return {"status": "online", "message": "ClipForge AI Backend 🔥", "version": "3.0"}

@app.get("/health")
async def health():
    return {
        "status": "OK",
        "whisper_loaded": _whisper is not None and not isinstance(_whisper, MockWhisper),
        "gemini_loaded": _gemini is not None and not isinstance(_gemini, MockGemini),
        "video_loaded": _video is not None and not isinstance(_video, MockVideo),
    }

@app.post("/api/youtube")
async def youtube_endpoint(url: str = Form(...)):
    logger.info(f"🔄 /api/youtube ricevuto: {url}")
    try:
        import yt_dlp
        file_id = str(uuid.uuid4())
        temp_dir = Path("temp")
        outtmpl = str(temp_dir / f"{file_id}.%(ext)s")

        ydl_opts = {
            "format": "best[height<=480]/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
        }

        logger.info(f"⬇️ Download YouTube: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        video_files = list(temp_dir.glob(f"{file_id}.*"))
        if not video_files:
            logger.error("❌ Download fallito — nessun file trovato in temp/")
            raise HTTPException(400, "Download YouTube fallito")

        video_path = str(video_files[0])
        size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        logger.info(f"✅ Video scaricato: {Path(video_path).name} ({size_mb:.1f} MB)")

        whisper = await get_whisper()
        logger.info("🎤 Avvio trascrizione Whisper...")
        transcript = whisper.transcribe_video(video_path)
        logger.info(f"✅ Trascrizione completata: {len(transcript)} caratteri")

        gemini = await get_gemini()
        logger.info("🧠 Analisi Gemini per momenti virali...")
        viral_clips = gemini.find_viral_moments(transcript, max_clips=3)
        logger.info(f"✅ Gemini trovati {len(viral_clips)} clip virali")

        video_svc = await get_video()
        generated_clips = []
        for i, clip in enumerate(viral_clips):
            clip_filename = f"clips/{file_id}_clip{i}.mp4"
            logger.info(f"✂️ Genero clip {i}: {clip.get('start_time')} → {clip.get('end_time')}")
            try:
                video_svc.generate_clip(video_path, clip_filename, clip["start_time"], clip["end_time"])
                clip_size = Path(clip_filename).stat().st_size / (1024 * 1024) if Path(clip_filename).exists() else 0
                logger.info(f"✅ Clip {i} generata: {clip_filename} ({clip_size:.2f} MB)")
                generated_clips.append(f"/clips/{file_id}_clip{i}.mp4")
            except Exception as clip_err:
                logger.error(f"❌ Errore generazione clip {i}: {clip_err}")
                logger.error(traceback.format_exc())

        # Pulizia file temporanei
        try:
            Path(video_path).unlink()
            logger.info("🧹 File temp rimosso")
        except Exception:
            pass

        return {
            "status": "success",
            "youtube_url": url,
            "transcript_preview": transcript[:500] + "..." if len(transcript) > 500 else transcript,
            "clips": viral_clips,
            "clip_urls": generated_clips,
            "total_clips": len(generated_clips),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERRORE CRITICO /api/youtube: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clips/{filename}")
async def download_clip(filename: str):
    file_path = f"clips/{filename}"
    if not os.path.exists(file_path):
        logger.error(f"❌ Clip non trovata: {file_path}")
        raise HTTPException(404, "Clip non trovata")
    return FileResponse(path=file_path, media_type="video/mp4", filename=filename)

@app.delete("/api/cleanup/{file_id}")
async def cleanup(file_id: str):
    paths = glob.glob(f"uploads/{file_id}.*") + glob.glob(f"clips/{file_id}_*")
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass
    logger.info(f"🧹 Cleanup {file_id}: {len(paths)} file rimossi")
    return {"deleted": len(paths)}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Avvio ClipForge Backend v3.0 (Lazy Init + Logging Definitivo)")
    uvicorn.run(app, host="0.0.0.0", port=10000)
