import os
from dotenv import load_dotenv
from google import genai

# Carica variabili da .env
load_dotenv()

# Prendi API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERRORE: API key non trovata nel file .env")
    exit()

print(f"✅ API Key caricata: {api_key[:20]}...")

# Configura client Gemini
client = genai.Client(api_key=api_key)

# Test semplice
print("\n🧪 Sto testando Gemini...")

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',  # ✅ Modello aggiornato
        contents='Rispondi con una emoji se funziona'
    )
    
    print(f"\n🎉 SUCCESSO! Gemini ha risposto:")
    print(f"📝 {response.text}")

except Exception as e:
    print(f"\n❌ ERRORE: {e}")
