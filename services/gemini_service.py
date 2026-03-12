import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re

load_dotenv()

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ GEMINI_API_KEY mancante")
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.5-flash'
    
    def find_viral_moments(self, transcript: str, max_clips: int = 5):
        prompt = f"""
Analizza questa trascrizione e trova {max_clips} momenti VIRALI per clip brevi (15-60s).

TRASCRIZIONE:
{transcript}

CRITERI (score 0-100):
- Hook forte primi 3s
- Emozioni intense
- Reveal/secrets
- Plot twist
- Frasi quotabili

RISPONDI SOLO JSON:
{{
  "clips": [
    {{
      "start_time": "00:45",
      "end_time": "01:05", 
      "viral_score": 89,
      "reason": "Hook forte (max 20 parole)",
      "transcript_snippet": "testo momento..."
    }}
  ]
}}
"""
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            text = response.text.strip()
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
            result = json.loads(text)
            return result.get('clips', [])
        except:
            return [{"start_time": "00:30", "end_time": "00:45", "viral_score": 80, "reason": "Fallback", "transcript_snippet": "test"}]
