# -*- coding: utf-8 -*-
"""
Cliente Ollama para IA de trading.
Conecta a Ollama local (Gemma 4) en vez de OpenRouter.
"""

import ollama
from typing import Optional, Dict, Any


# Modelos disponibles (fallback chain) - qwen2 para mejor rendimiento
MODELS = ["qwen2:0.5b", "gemma4:e2b"]


class OllamaClient:
    """Cliente para conectar a Ollama local."""
    
    def __init__(self, model: str = None, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        
        # Si no se especifica modelo, usar el primero disponible
        if model:
            self.models = [model]
        else:
            self.models = MODELS
        
        self.current_model = None
        self.client = None
        self._connected = False
        self.initial_context = ""
    
    def initialize_context(self, memory_context: str = "", learnings_context: str = ""):
        """Carga el contexto inicial (no necesario para Ollama, pero requerido por el bot)."""
        context = """Eres un scalper profesional de XAU/USD en timeframe M1.
Buscas operaciones rápidas con SL ajustados.
Si hay duda, responder NADA.
Si hay noticia ±30 min → NO OPERAR.
Responde SOLO con una palabra: BUY, SELL o NADA"""
        
        if memory_context:
            context += f"\n\n{memory_context}"
        
        if learnings_context:
            context += f"\n\n{learnings_context}"
        
        self.initial_context = context
        print(f"📌 Contexto IA cargado ({len(self.initial_context)} chars)")
    
    def connect(self) -> bool:
        """Inicializa la conexión con Ollama."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                # Encontrar primer modelo disponible
                available = response.json().get("models", [])
                model_names = [m["name"].split(":")[0] for m in available]
                
                for m in self.models:
                    base = m.split(":")[0]
                    if any(base in n for n in model_names):
                        self.current_model = m
                        break
                
                if not self.current_model:
                    self.current_model = self.models[0]
                
                self._connected = True
                print(f"✅ Conectado a Ollama: {self.current_model}")
                return True
        except Exception as e:
            print(f"❌ Error conectando a Ollama: {e}")
            print(f"   Asegúrate de que Ollama esté corriendo: ollama serve")
            return False
    
    def analyze(self, market_data: Dict[str, Any], strategy_rules: str) -> str:
        """
        Analiza datos de mercado y decide señal.
        
        Args:
            market_data: Diccionario con precio, RSI, EMA, ATR, etc.
            strategy_rules: Reglas de la estrategia activa
            
        Returns:
            "BUY" | "SELL" | "NADA"
        """
        if not self._connected:
            return "NADA"
        
        # Construir prompt
        prompt = self._build_prompt(market_data, strategy_rules)
        
        # Probar cada modelo hasta que uno funcione
        for model in self.models:
            try:
                response = ollama.chat(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": """Eres un ANALISTA de trading para XAUUSD M1.
 Tu único trabajo es CONFIRMAR o RECHAZAR señales de trading.
 
 REGLAS:
 1. Si la estrategia dice SELL y el precio está BAJO el EMA50 → CONFIRMA SELL
 2. Si la estrategia dice BUY y el precio está SOBRE el EMA50 → CONFIRMA BUY  
 3. Si el RSI está en sobrecompra (>70) o sobreventa (<30) → RECHAZAR
 4. Si hay noticia de alto impacto pronto → RECHAZAR
 
 IMPORTANTE: Responde SOLO con la palabra exacta que corresponda:
 - Si confirmas SELL -> escribe "SELL"
 - Si confirmas BUY -> escribe "BUY"  
 - Si rechazas -> escribe "NADA"
 
 NADA de explicaciones, NADA de texto adicional."""
                        },
                        {
                            "role": "user",
                            "content": f"""La estrategia detecta: {strategy_rules.get('direction', 'N/A')}

Datos del mercado:
- Precio actual: ${market_data.get('price', 'N/A')}
- EMA50: ${market_data.get('ema50', 'N/A')}
- EMA200: ${market_data.get('ema200', 'N/A')}
- RSI: {market_data.get('rsi', 'N/A')}
- Tendencia: {market_data.get('trend', 'N/A')}

Responde SOLO: SELL, BUY o NADA"""
                        }
                    ],
                    options={
                        "temperature": 0.0,
                        "num_predict": 3,
                        "repeat_penalty": 1.5
                    }
                )
                
                content = response.get("message", {}).get("content", "").strip().upper()
                
                print(f"   [IA] Response: {content[:80]}...")
                
                # Buscar palabras clave
                buy_words = ["BUY", "LONG", "CALL", "COMPRAR"]
                sell_words = ["SELL", "SHORT", "PUT", "VENDER"]
                
                for word in buy_words:
                    if word in content:
                        print(f"   [OK] BUY detected ({word})")
                        return "BUY"
                
                for word in sell_words:
                    if word in content:
                        print(f"   [OK] SELL detected ({word})")
                        return "SELL"
                
                return "NADA"
                    
            except Exception as e:
                print(f"⚠️ Modelo {model} falló: {e}")
                continue
        
        return "NADA"
    
    def _build_prompt(self, market_data: Dict, strategy_rules: str) -> str:
        """Construye el prompt para la IA."""
        return f"""
## Datos Actuales del Mercado:
- Precio: ${market_data.get('price', 'N/A')}
- EMA50: ${market_data.get('ema50', 'N/A')}
- EMA200: ${market_data.get('ema200', 'N/A')}
- RSI14: {market_data.get('rsi', 'N/A')}
- ATR14: ${market_data.get('atr', 'N/A')}
- Tendencia: {market_data.get('trend', 'N/A')}

## Estrategia Activa:
{strategy_rules}

## Estado de Noticias:
{market_data.get('news_status', 'Sin noticias')}

Responde SOLO con una palabra: BUY, SELL o NADA
"""