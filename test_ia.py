#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de conexión IA - OpenRouter
Simple: envía un mensaje y recibe respuesta
"""

import os
import sys

# Cargar variable de entorno
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "")

if not API_KEY:
    print("❌ Error: Falta OPENROUTER_API_KEY en .env")
    sys.exit(1)

print("🔌 Conectando a OpenRouter...")

try:
    from openrouter import OpenRouter
    
    client = OpenRouter(api_key=API_KEY)
    
    print("✅ Cliente creado")
    
    # Enviar mensaje simple
    print("📤 Enviando mensaje de prueba...")
    
    response = client.chat.send(
        messages=[
            {"role": "user", "content": "Responde solo con 'BUY' o 'SELL'"}
        ],
        model="meta-llama/llama-3.2-3b-instruct:free",
        temperature=0.1,
        max_tokens=20
    )
    
    print("✅ Respuesta recibida!")
    print(f"📥 Respuesta: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n✅ Test completado - IA funcionando!")