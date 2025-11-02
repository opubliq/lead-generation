#!/usr/bin/env python3
"""
Test rapide de l'API Gemini
"""

import os
import google.generativeai as genai

# Charger la clé API
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ Erreur: Variable GEMINI_API_KEY non définie")
    print("   Créez un fichier .env avec:")
    print("   GEMINI_API_KEY=votre_clé")
    exit(1)

print(f"✅ Clé API trouvée: {api_key[:10]}...")

# Configurer Gemini
try:
    genai.configure(api_key=api_key)

    # Lister les modèles disponibles
    print("\n📋 Modèles disponibles:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"   • {m.name}")

    # Utiliser gemini-2.5-flash (rapide et stable)
    model = genai.GenerativeModel("gemini-2.5-flash")
    print("\n✅ Modèle gemini-2.5-flash initialisé")
except Exception as e:
    print(f"❌ Erreur d'initialisation: {e}")
    exit(1)

# Test simple
try:
    print("\n🧪 Test d'appel API...")
    response = model.generate_content("Réponds avec juste le chiffre 5")
    result = response.text.strip()
    print(f"✅ Réponse reçue: '{result}'")

    if "5" in result:
        print("\n🎉 API Gemini fonctionne correctement!")
    else:
        print(f"\n⚠️  Réponse inattendue (attendu: 5, reçu: {result})")

except Exception as e:
    print(f"❌ Erreur lors de l'appel API: {e}")
    exit(1)
