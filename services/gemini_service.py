import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re

load_dotenv()

class GeminiService:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError('GEMINI_API_KEY mancante')
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini 1.5 Flash pronto!")

    def find_viral_moments(self, transcript: str, max_clips: int = 5) -> list:
        prompt = f"""Trova {max_clips} momenti VIRALI (15-60s) da questa trascrizione YouTube.
TRASCRIZIONE: {transcript[:4000]}
CRITERI score 0-100: hook primi 3s, emozioni, reveal, twist, frasi quotabili.
RISPONDI SOLO JSON array: [
  {{"starttime": "00:45", "endtime": "01:05", "viralscore": 89, "reason": "Hook forte (max 20 parole)", "transcript_snippet": "testo"}}
]"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            text = re.sub(r'```json|```', '', text)
            text = re.sub(r'\\', '', text)  # Escape fix
            result = json.loads(text)
            clips = result.get('clips', [])
            print(f"✅ Gemini trovato {len(clips)} clip virali")
            return clips
        except Exception as e:
            print(f"❌ Gemini errore: {e}")
            return [
                {"starttime": "00:30", "endtime": "00:45", "viralscore": 80, "reason": "Fallback", "transcript_snippet": "test"}
            ]
