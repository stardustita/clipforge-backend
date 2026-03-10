from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import uuid
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import glob
import yt_dlp

# Importa servizi
from services.whisper_service import WhisperService
from services.gemini_service import GeminiService
from services.video_service import VideoService

load_dotenv()
app = FastAPI(title="ClipForge AI Backend", version="2.1")

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

whisper = WhisperService()
gemini = GeminiService()
video_service = VideoService()

@app.get("/")
def home():
    return {"status": "online", "message": "ClipForge AI Backend pronto! 🔥", "version": "2.1"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        extension = file.filename.split(".")[-1].lower()
        file_path = f"uploads/{file_id}.{extension}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "path": file_path,
            "size_mb": os.path.getsize(file_path) / (1024*1024)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload fallito: {str(e)}")

@app.post("/api/analyze")
async def analyze_video(file_id: str = Form(...)):
    try:
        video_files = glob.glob(f"uploads/{file_id}.*")
        if not video_files:
            raise HTTPException(404, "File non trovato")
        video_path = video_files[0]
        transcript = whisper.transcribe_video(video_path)
        viral_clips = gemini.find_viral_moments(transcript)
        return {
            "file_id": file_id,
            "transcript": transcript[:2000] + "..." if len(transcript) > 2000 else transcript,
            "clips": viral_clips,
            "total_clips": len(viral_clips),
            "top_score": viral_clips[0]["viral_score"] if viral_clips else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analisi fallita: {str(e)}")

@app.post("/api/generate-clips")
async def generate_clips(file_id: str = Form(...), clip_index: int = Form(1)):
    try:
        video_files = glob.glob(f"uploads/{file_id}.*")
        if not video_files:
            raise HTTPException(404, "Video non trovato")
        video_path = video_files[0]
        transcript = whisper.transcribe_video(video_path)
        viral_clips = gemini.find_viral_moments(transcript)
        if clip_index > len(viral_clips) or clip_index < 1:
            raise HTTPException(400, "Clip index non valido")
        clip_info = viral_clips[clip_index - 1]
        clip_filename = f"clips/{file_id}_clip{clip_index}.mp4"
        video_service.generate_clip(video_path, clip_filename, clip_info['start_time'], clip_info['end_time'])
        return {
            "success": True,
            "clip_filename": clip_filename,
            "download_url": f"/clips/{os.path.basename(clip_filename)}",
            "clip_info": clip_info,
            "size_mb": os.path.getsize(clip_filename) / (1024*1024)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generazione fallita: {str(e)}")

@app.get("/clips/{filename}")
async def download_clip(filename: str):
    file_path = f"clips/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(404, "Clip non trovata")
    return FileResponse(path=file_path, media_type='video/mp4', filename=filename)

@app.post("/api/youtube")
async def analyze_youtube(url: str = Form(...)):
    try:
        file_id = str(uuid.uuid4())
        video_path = f"temp/{file_id}.%(ext)s"
        ydl_opts = {'format': 'best[height<=720]/best', 'outtmpl': video_path, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        video_files = glob.glob(f"temp/{file_id}.*")
        if not video_files:
            raise HTTPException(400, "Download fallito")
        video_path = video_files[0]
        transcript = whisper.transcribe_video(video_path)
        viral_clips = gemini.find_viral_moments(transcript)
        os.remove(video_path)
        return {
            "success": True,
            "youtube_url": url,
            "transcript_preview": transcript[:500] + "...",
            "clips": viral_clips,
            "top_clip": viral_clips[0] if viral_clips else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore YouTube: {str(e)}")

@app.delete("/api/cleanup/{file_id}")
async def cleanup_files(file_id: str):
    paths = glob.glob(f"uploads/{file_id}.*") + glob.glob(f"clips/{file_id}_*")
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
    return {"deleted": len(paths)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
