# main.py - FIX ULTIMO ERRORE (os.makedirs)
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import os, uuid, glob
import yt_dlp
from pydantic import BaseModel
from typing import List

app = FastAPI(title="ClipForge")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Clip(BaseModel):
    start_time: str
    end_time: str
    viral_score: int
    reason: str

_whisper = None
_gemini = None
_video = None

class MockWhisper:
    async def transcribe_video(self, path):
        return "Trascrizione test video"

class MockGemini:
    async def find_viral_moments(self, transcript, max_clips=3):
        return [
            Clip(start_time="00:30", end_time="01:00", viral_score=90, reason="Momento virale"),
            Clip(start_time="01:45", end_time="02:15", viral_score=85, reason="Hook forte")
        ]

class MockVideo:
    async def generate_clip(self, input_path, output_path, start, end):
        open(output_path, 'w').close()  # File vuoto mock

async def get_whisper():
    global _whisper
    if _whisper is None:
        try:
            from whisper_service import WhisperService
            _whisper = WhisperService()
            print("Whisper OK")
        except:
            print("Whisper mock")
            _whisper = MockWhisper()
    return _whisper

async def get_gemini():
    global _gemini
    if _gemini is None:
        try:
            from gemini_service import GeminiService
            _gemini = GeminiService()
            print("Gemini OK")
        except:
            print("Gemini mock")
            _gemini = MockGemini()
    return _gemini

async def get_video():
    global _video
    if _video is None:
        try:
            from video_service import VideoService
            _video = VideoService()
            print("Video OK")
        except:
            print("Video mock")
            _video = MockVideo()
    return _video

@app.post("/api/youtube")
async def youtube_pipeline(url: str = Form(...)):
    fileid = str(uuid.uuid4())
    videopath = f"temp/{fileid}.%(ext)s"
    
    ydl_opts = {
        "format": "best[height<=720]", 
        "outtmpl": videopath,
        "quiet": True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    videofiles = glob.glob(f"temp/{fileid}.*")
    if not videofiles:
        raise HTTPException(400, "Download fallito")
    
    videopath = videofiles[0]
    
    whisper = await get_whisper()
    transcript = await whisper.transcribe_video(videopath)
    
    gemini = await get_gemini()
    clips = await gemini.find_viral_moments(transcript)
    
    clips_generated = []
    videosvc = await get_video()
    os.makedirs("clips", exist_ok=True)
    
    for i, clip in enumerate(clips[:3]):
        output = f"clips/{fileid}_clip{i}.mp4"
        await videosvc.generate_clip(videopath, output, clip.start_time, clip.end_time)
        clips_generated.append(f"/clips/{os.path.basename(output)}")
    
    os.remove(videopath)
    
    return {
        "status": "success",
        "clips": clips_generated
    }

@app.get("/clips/{filename}")
async def get_clip(filename: str):
    filepath = f"clips/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(404, "Clip non trovata")
    return FileResponse(filepath, media_type="video/mp4")

@app.get("/health")
async def health():
    return {"status": "OK"}

if __name__ == "__main__":
    os.makedirs("temp", exist_ok=True)
    os.makedirs("clips", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=10000)
