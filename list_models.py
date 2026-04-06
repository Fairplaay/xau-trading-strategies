# -*- coding: utf-8 -*-
"""
Listador de modelos de OpenRouter.
Checkea modelos disponibles y filtra por free/paid.
"""

import argparse
import os
from openrouter import OpenRouter


def list_models(api_key: str, free_only: bool = False):
    """Lista modelos disponibles de OpenRouter."""
    
    if not api_key:
        print("❌ Necesitas OPENROUTER_API_KEY")
        print("   Crea un .env con tu API key o-passala como argumento")
        return
    
    client = OpenRouter(api_key=api_key)
    
    try:
        # Obtener lista de modelos
        response = client.models.list()
        models = response.data
        
        print("\n" + "=" * 60)
        print("🧠 MODELOS DISPONIBLES EN OPENROUTER")
        print("=" * 60 + "\n")
        
        if free_only:
            print("📌 Mostrando solo modelos FREE\n")
            free_models = [m for m in models if "free" in m.id.lower() or "free" in m.name.lower()]
            for m in free_models:
                print(f"  {m.id}")
        else:
            print(f"📊 Total: {len(models)} modelos\n")
            
            # Categorizar
            free_models = [m for m in models if "free" in m.id.lower()]
            paid_models = [m for m in models if "free" not in m.id.lower()]
            
            print("🆓 MODELOS FREE:")
            for m in free_models[:20]:  # Primeros 20
                print(f"  {m.id}")
            if len(free_models) > 20:
                print(f"  ... y {len(free_models) - 20} más")
            
            print(f"\n💰 MODELOS PAID (primeros 20):")
            for m in paid_models[:20]:
                print(f"  {m.id}")
            if len(paid_models) > 20:
                print(f"  ... y {len(paid_models) - 20} más")
        
        print("\n" + "=" * 60)
        print("💡 USO: Copia el ID del modelo y ponlo en .env como:")
        print("   MODEL_NAME=meta-llama/llama-3.2-3b-instruct:free")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Lista modelos de OpenRouter")
    parser.add_argument("--api-key", type=str, help="API Key de OpenRouter")
    parser.add_argument("--free", action="store_true", help="Mostrar solo modelos gratuitos")
    parser.add_argument("--env", type=str, default=".env", help="Archivo .env a usar")
    
    args = parser.parse_args()
    
    # Intentar cargar desde .env
    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY", "")
    
    if not api_key and os.path.exists(args.env):
        from dotenv import load_dotenv
        load_dotenv(args.env)
        api_key = os.getenv("OPENROUTER_API_KEY", "")
    
    list_models(api_key, free_only=args.free)


if __name__ == "__main__":
    main()