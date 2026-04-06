#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de conexión IA - OpenRouter
Simple: envía un mensaje y recibe respuesta
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "")

if not API_KEY:
    print("❌ Error: Falta OPENROUTER_API_KEY en .env")
    sys.exit(1)

MODEL = os.getenv("MODEL_NAME", "meta-llama/llama-3.2-3b-instruct:free")

print("🔌 Conectando a OpenRouter...")
print(f"   Modelo: {MODEL}")
print(f"   API Key: {API_KEY[:15]}...")

MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    print(f"\n📤 Intento {attempt + 1}/{MAX_RETRIES}...")
    
    try:
        from openrouter import OpenRouter
        
        with OpenRouter(api_key=API_KEY) as client:
            print("✅ Cliente creado")
            
            response = client.chat.send(
                messages=[
                    {"role": "user", "content": "Responde solo con una palabra: BUY o SELL"}
                ],
                model=MODEL,
                max_tokens=10,
                temperature=0.1
            )
            
            # Leer respuesta
            text = ""
            for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    if chunk.choices[0].delta.content:
                        text += chunk.choices[0].delta.content
            
            if text.strip():
                print(f"✅ Respuesta: {text.strip()}")
                print("\n✅ IA funcionando!")
                sys.exit(0)
            else:
                print("⚠️ Respuesta vacía")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        err_str = str(e)
        if "TooManyRequests" in err_str or "rate_limit" in err_str:
            print("   Modelo saturado, esperando 2s...")
            import time
            time.sleep(2)
        else:
            print(f"   Error: {e}")
    
    import time
    time.sleep(1)

print("\n❌ Todos los intentos fallaron")
print("   Prueba cambiar el modelo en .env:")
print("   MODEL_NAME=google/gemma-2-9b-it:free")
sys.exit(1)