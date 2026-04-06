# -*- coding: utf-8 -*-
"""
Cliente Ollama para IA de trading.
Conecta a Ollama local (Gemma 4) en vez de OpenRouter.
"""

import ollama
from typing import Optional, Dict, Any


# Modelos disponibles (fallback chain) - tinyllama para CPU sin GPU
MODELS = ["tinyllama", "qwen2:0.5b", "gemma4:e2b"]


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
        """
        Carga el contexto inicial (no necesario para Ollama, pero requerido por el bot).
        """
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
                            "content": """Eres un scalper profesional de XAU/USD en timeframe M1.
Buscas operaciones rápidas con SL ajustados.
Si hay duda, responder NADA.
Si hay noticia ±30 min → NO OPERAR.
Responde SOLO con una palabra: BUY, SELL o NADA"""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    options={
                        "temperature": 0.3,
                        "num_predict": 50
                    }
                )
                
                content = response.get("message", {}).get("content", "").strip().upper()
                
                print(f"   📝 IA响应: {content[:80]}...")
                
                # Normalizar respuesta - buscar cualquier indicación
                buy_indicators = ["BUY", "COMPRAR", "LONG", "CALL", "APUYAR", "SUBE", "ALCISTA"]
                sell_indicators = ["SELL", "VENDER", "SHORT", "PUT", "BAJAR", "BAJISTA", "NEGATIVO"]
                
                for indicator in buy_indicators:
                    if indicator in content:
                        return "BUY"
                
                for indicator in sell_indicators:
                    if indicator in content:
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