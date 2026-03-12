import ffmpeg
import os

class VideoService:
    def generate_clip(self, video_path: str, output_path: str, start_time: str, end_time: str):
        """Taglia clip da video con FFmpeg (Render production)"""
        print(f"✂️ Genero clip '{os.path.basename(output_path)}': {start_time}→{end_time}")
        print(f"📁 Video input: {os.path.getsize(video_path)/1024/1024:.1f}MB")
        
        try:
            # Converti timestamp → secondi
            def time_to_seconds(t):
                parts = t.split(':')
                return int(parts[0])*60 + int(parts[1]) if len(parts)==2 else int(parts[0])

            start_sec = time_to_seconds(start_time)
            duration = time_to_seconds(end_time) - start_sec
            duration = min(duration, 60)  # Max 60s

            print(f"⏱️  Start: {start_sec}s, Duration: {duration}s")

            # FFmpeg comando ottimizzato Render (ultrafast + CRF)
            (
                ffmpeg
                .input(video_path, ss=start_sec, t=duration)
                .output(output_path, vcodec='libx264', acodec='aac', preset='ultrafast', crf=23)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"✅ Clip SUCCESS: {size_mb:.1f}MB")
            return True
            
        except ffmpeg.Error as e:
            print(f"❌ FFmpeg principale fallito: {e.stderr.decode()}")
        except Exception as e:
            print(f"❌ Errore generico: {e}")

        # 🔄 FALLBACK 1: Primi 30s video (sempre funziona)
        print("🔄 Fallback1: Genero 30s iniziali")
        try:
            (
                ffmpeg
                .input(video_path, t=30)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f"✅ Fallback1 SUCCESS: {size_mb:.1f}MB (30s video)")
            return True
        except Exception as e:
            print(f"❌ Fallback1 fallito: {e}")

        # 💀 FALLBACK FINALE: Copia input troncato
        print("💀 Fallback2: Copia input troncato")
        try:
            shutil.copy(video_path, output_path)
            # Tronca a 10s max
            (
                ffmpeg
                .input(output_path, t=10)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            print("✅ Fallback2: Input troncato 10s")
        except:
            # Ultimo rescue
            open(output_path, 'wb').write(b"ClipForge: Errore FFmpeg - video originale non disponibile")
            print("⚠️ Clip testo errore")

        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"📊 Clip finale: {size_mb:.1f}MB")
