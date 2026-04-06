#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de conexión IA - OpenRouter
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL_NAME", "openrouter/free")

print("🔌 Conectando a OpenRouter...")
print(f"   Modelo: {MODEL}")
print(f"   API Key: {API_KEY[:15]}...")

try:
    from openrouter import OpenRouter
    
    with OpenRouter(api_key=API_KEY) as client:
        print("✅ Cliente creado")
        
        print("📤 Enviando mensaje...")
        
        response = client.chat.send(
            messages=[
                {"role": "user", "content": "Responde solo: HOLA"}
            ],
            model=MODEL,
            max_tokens=5
        )
        
        # Obtener respuesta completa
        result = response.get()
        
        print(f"✅ Respuesta: {result}")
        print(f"📥 Contenido: {result.choices[0].message.content}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Test completado!")