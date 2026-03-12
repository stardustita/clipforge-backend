# main.py — ClipForge AI Backend V2.2 (Fix KeyError + Gemini 404 + Lazy Init + Logging)
import logging
import traceback
import os
import uuid
import glob
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("clipforge")

# ============================================================
# APP
# ============================================================
app = FastAPI(title="ClipForge AI Backend", version="2.2")

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
_gemini  = None
_video   = None

# ============================================================
# MOCK FALLBACK
# ============================================================
class MockWhisper:
    def transcribe_video(self, path: str) -> str:
        logger.warning("⚠️ WhisperService MOCK attivo")
        return "0000 Mock trascrizione Whisper non disponibile."

class MockGemini:
    def find_viral_moments(self, transcript: str, max_clips: int = 3):
        logger.warning("⚠️ GeminiService MOCK attivo")
        return [
            {
                "starttime": "00:00",
                "endtime": "00:30",
                "viral_score": 0,
                "reason": "MOCK — Gemini non disponibile",
                "transcript_snippet": transcript[:100]
            }
        ]

class MockVideo:
    def generate_clip(self, video_path: str, output_path: str, start: str, end: str):
        logger.warning("⚠️ VideoService MOCK attivo — clip vuota creata")
        Path(output_path).touch()

# ============================================================
# LAZY GETTERS
# ============================================================
async def get_whisper():
    global _whisper
    if _whisper is None:
        try:
            logger.info("⏳ Caricamento WhisperService...")
            from services.whisper_service import WhisperService
            _whisper = WhisperService()
            logger.info("✅ WhisperService OK")
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
            logger.info("✅ GeminiService OK")
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
            logger.info("✅ VideoService OK")
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
    return {"status": "online", "message": "ClipForge AI Backend 🔥", "version": "2.2"}

@app.get("/health")
async def health():
    return {
        "status": "OK",
        "whisper_loaded": _whisper is not None and not isinstance(_whisper, MockWhisper),
        "gemini_loaded":  _gemini  is not None and not isinstance(_gemini,  MockGemini),
        "video_loaded":   _video   is not None and not isinstance(_video,   MockVideo),
    }

# ---- UPLOAD ----
@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        import shutil
        file_id   = str(uuid.uuid4())
        extension = file.filename.split(".")[-1].lower()
        file_path = f"uploads/{file_id}.{extension}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "success":  True,
            "file_id":  file_id,
            "filename": file.filename,
            "size_mb":  os.path.getsize(file_path) / (1024 * 1024)
        }
    except Exception as e:
        raise HTTPException(500, f"Upload fallito: {str(e)}")

# ---- ANALYZE ----
@app.post("/api/analyze")
async def analyze_video(file_id: str = Form(...)):
    try:
        video_files = glob.glob(f"uploads/{file_id}.*")
        if not video_files:
            raise HTTPException(404, "File non trovato")
        video_path = video_files[0]

        whisper = await get_whisper()
        transcript = whisper.transcribe_video(video_path)

        gemini = await get_gemini()
        viral_clips = gemini.find_viral_moments(transcript)

        return {
            "file_id":    file_id,
            "transcript": transcript[:2000] + "..." if len(transcript) > 2000 else transcript,
            "clips":      viral_clips,
            "total_clips": len(viral_clips),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Analisi fallita: {str(e)}")

# ---- GENERATE CLIPS ----
@app.post("/api/generate-clips")
async def generate_clips(file_id: str = Form(...), clip_index: int = Form(1)):
    try:
        video_files = glob.glob(f"uploads/{file_id}.*")
        if not video_files:
            raise HTTPException(404, "Video non trovato")
        video_path = video_files[0]

        whisper = await get_whisper()
        transcript = whisper.transcribe_video(video_path)

        gemini = await get_gemini()
        viral_clips = gemini.find_viral_moments(transcript)

        if clip_index < 1 or clip_index > len(viral_clips):
            raise HTTPException(400, f"clip_index non valido (max {len(viral_clips)})")

        clip_info = viral_clips[clip_index - 1]

        # ✅ FIX V2.2: chiavi Gemini sono "starttime"/"endtime" (no underscore)
        start_time = clip_info.get("starttime", clip_info.get("start_time", "00:00"))
        end_time   = clip_info.get("endtime",   clip_info.get("end_time",   "00:30"))

        clip_filename = f"clips/{file_id}_clip{clip_index}.mp4"

        video_svc = await get_video()
        video_svc.generate_clip(video_path, clip_filename, start_time, end_time)

        return {
            "success":      True,
            "download_url": f"/clips/{file_id}_clip{clip_index}.mp4",
            "clip_info":    clip_info,
            "size_mb":      Path(clip_filename).stat().st_size / (1024 * 1024) if Path(clip_filename).exists() else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Generazione clip fallita: {str(e)}")

# ---- YOUTUBE PIPELINE ----
@app.post("/api/youtube")
async def youtube_endpoint(url: str = Form(...)):
    logger.info(f"🔄 /api/youtube: {url}")
    try:
        import yt_dlp
        file_id  = str(uuid.uuid4())
        temp_dir = Path("temp")

        ydl_opts = {
            "format":         "best[height<=480]/best",
            "outtmpl":        str(temp_dir / f"{file_id}.%(ext)s"),
            "quiet":          True,
            "no_warnings":    True,
            "socket_timeout": 30,
        }

        logger.info(f"⬇️ Download YouTube: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        video_files = list(temp_dir.glob(f"{file_id}.*"))
        if not video_files:
            raise HTTPException(400, "Download YouTube fallito")

        video_path = str(video_files[0])
        size_mb    = Path(video_path).stat().st_size / (1024 * 1024)
        logger.info(f"✅ Video scaricato: {Path(video_path).name} ({size_mb:.1f} MB)")

        whisper    = await get_whisper()
        transcript = whisper.transcribe_video(video_path)
        logger.info(f"✅ Trascrizione: {len(transcript)} caratteri")

        gemini      = await get_gemini()
        viral_clips = gemini.find_viral_moments(transcript, max_clips=3)
        logger.info(f"✅ Gemini: {len(viral_clips)} clip virali trovate")

        video_svc        = await get_video()
        generated_clips  = []

        for i, clip in enumerate(viral_clips):
            # ✅ FIX V2.2: doppio .get() per compatibilità chiavi Gemini
            start_time = clip.get("starttime", clip.get("start_time", "00:00"))
            end_time   = clip.get("endtime",   clip.get("end_time",   "00:30"))

            clip_filename = f"clips/{file_id}_clip{i}.mp4"
            logger.info(f"✂️ Clip {i}: {start_time} → {end_time}")
            try:
                video_svc.generate_clip(video_path, clip_filename, start_time, end_time)
                clip_size = Path(clip_filename).stat().st_size / (1024 * 1024) if Path(clip_filename).exists() else 0
                logger.info(f"✅ Clip {i} generata ({clip_size:.2f} MB)")
                generated_clips.append(f"/clips/{file_id}_clip{i}.mp4")
            except Exception as clip_err:
                logger.error(f"❌ Errore clip {i}: {clip_err}")
                logger.error(traceback.format_exc())

        # Pulizia temp
        try:
            Path(video_path).unlink()
            logger.info("🧹 File temp rimosso")
        except Exception:
            pass

        return {
            "status":            "success",
            "youtube_url":       url,
            "transcript_preview": transcript[:500] + "..." if len(transcript) > 500 else transcript,
            "clips":             viral_clips,
            "clip_urls":         generated_clips,
            "total_clips":       len(generated_clips),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERRORE CRITICO /api/youtube: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, str(e))

# ---- DOWNLOAD CLIP ----
@app.get("/clips/{filename}")
async def download_clip(filename: str):
    file_path = f"clips/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(404, "Clip non trovata")
    return FileResponse(path=file_path, media_type="video/mp4", filename=filename)

# ---- CLEANUP ----
@app.delete("/api/cleanup/{file_id}")
async def cleanup(file_id: str):
    paths = glob.glob(f"uploads/{file_id}.*") + glob.glob(f"clips/{file_id}_*")
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass
    logger.info(f"🧹 Cleanup: {len(paths)} file rimossi")
    return {"deleted": len(paths)}

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 ClipForge Backend V2.2 — Lazy Init + Fix KeyError + Gemini 404")
    uvicorn.run(app, host="0.0.0.0", port=10000)
