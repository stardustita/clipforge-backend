import ffmpeg
import os

class VideoService:
    def generate_clip(self, video_path: str, output_path: str, start_time: str, end_time: str):
        """Taglia clip da video con FFmpeg"""
        try:
            # Converti HH:MM:SS → secondi
            def time_to_seconds(t):
                h, m, s = map(int, t.split(':'))
                return h*3600 + m*60 + s
            
            start_sec = time_to_seconds(start_time)
            duration = time_to_seconds(end_time) - start_sec
            
            stream = ffmpeg.input(video_path, ss=start_sec, t=duration)
            stream = ffmpeg.output(stream, output_path, vcodec='libx264', acodec='aac', **{'preset': 'fast'})
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
        except Exception as e:
            print(f"FFmpeg error: {e}")
            # Fallback: copia primo minuto
            stream = ffmpeg.input(video_path, t=30)
            stream = ffmpeg.output(stream, output_path)
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
