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

print("🔌 Conectando a OpenRouter...")

try:
    from openrouter import OpenRouter
    
    with OpenRouter(api_key=API_KEY) as client:
        print("✅ Cliente creado")
        
        print("📤 Enviando mensaje de prueba...")
        
        response = client.chat.send(
            messages=[
                {"role": "user", "content": "Responde solo con 'BUY' o 'SELL'"}
            ],
            model="meta-llama/llama-3.2-3b-instruct:free",
            max_tokens=20
        )
        
        # Leer respuesta
        text = ""
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices:
                if chunk.choices[0].delta.content:
                    text += chunk.choices[0].delta.content
        
        print("✅ Respuesta recibida!")
        print(f"📥 Respuesta: {text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Test completado - IA funcionando!")