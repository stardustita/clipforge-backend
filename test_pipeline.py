from services.whisper_service import WhisperService
from services.gemini_service import GeminiService

print("🚀 TEST PIPELINE COMPLETA\n")

# 1. Trascrivi audio
print("📝 STEP 1: Trascrizione...")
whisper = WhisperService()
testo = whisper.trascrivi("uploads/Kevin de Vries - Dance With Me.mp3")
print(f"✅ Trascritto: {len(testo)} caratteri\n")

# 2. Analizza con Gemini
print("🧠 STEP 2: Analisi momenti virali...")
gemini = GeminiService()
momenti = gemini.analizza_trascrizione(testo)

print("\n🎯 RISULTATO:")
print(momenti)
