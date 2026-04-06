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

try:
    from openrouter import OpenRouter
    
    with OpenRouter(api_key=API_KEY) as client:
        print("✅ Cliente creado")
        
        print("📤 Enviando mensaje de prueba...")
        
        response = client.chat.send(
            messages=[
                {"role": "user", "content": "Responde solo con 'BUY' o 'SELL'"}
            ],
            model=MODEL,
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
    print(f"\n❌ Error: {e}")
    
    # Mensajes específicos por tipo de error
    err_str = str(e)
    if "TooManyRequests" in err_str or "rate_limit" in err_str:
        print("\n⚠️ El modelo está saturado o alcanzaste el límite.")
        print("   Prueba en .env con otro modelo:")
        print("   MODEL_NAME=google/gemma-2-9b-it:free")
    elif "Provider returned error" in err_str:
        print("\n⚠️ El proveedor del modelo tiene problemas.")
        print("   Prueba con otro modelo gratuito.")
    elif "api_key" in err_str.lower():
        print("\n⚠️ Revisa tu API key en .env")
    else:
        print("\n   Revisa tu cuenta en https://openrouter.ai/credits")
    
    sys.exit(1)

print("\n✅ Test completado - IA funcionando!")