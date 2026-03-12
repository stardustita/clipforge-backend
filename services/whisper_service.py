from faster_whisper import WhisperModel
import os
import ffmpeg

class WhisperService:
    def __init__(self):
        """Inizializza Whisper su CPU (compatibile GTX 550 Ti)"""
        print("⏳ Caricamento Whisper (CPU mode)...")
        # CPU + int8 = stabile e veloce su hardware vecchio
        self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
        )
        print("✅ Whisper pronto (CPU mode)!")

    def extract_audio(self, video_path: str, audio_path: str):
        """Estrae audio da video con FFmpeg"""
        try:
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, audio_path, acodec="pcm_s16le", ar=16000, ac=1)
            ffmpeg.run(stream, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)
        except Exception as e:
            print(f"⚠️ FFmpeg estratto audio fallito: {e}")

    def transcribe_video(self, video_path: str) -> str:
        """Trascrive video/audio con timestamp"""
        # Se è video, estrai audio
        if video_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            audio_path = video_path.rsplit('.', 1)[0] + '_audio.wav'
            self.extract_audio(video_path, audio_path)
            input_path = audio_path
        else:
            input_path = video_path
        
        print(f"🎤 Trascrivo: {os.path.basename(input_path)}")
        
        segments, info = self.model.transcribe(
            input_path, 
            word_timestamps=True,
            language="it"  # Italiano prioritario
        )
        
        transcript = []
        for segment in segments:
            if segment.text.strip():  # Ignora silenzi
                start_min = int(segment.start // 60)
                start_sec = int(segment.start % 60)
                timestamp = f"{start_min:02d}:{start_sec:02d}"
                transcript.append(f"[{timestamp}] {segment.text.strip()}")
        
        full_text = " ".join(transcript)
        
        # Pulisci file temp
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.remove(audio_path)
        
        print(f"✅ Trascritto {len(full_text)} caratteri")
        return full_text
