# -*- coding: utf-8 -*-
"""
Cliente Ollama para IA de trading.
Conecta a Ollama local (Gemma 4) en vez de OpenRouter.
"""

import ollama
from typing import Optional, Dict, Any


class OllamaClient:
    """Cliente para conectar a Ollama local."""
    
    def __init__(self, model: str = "gemma4:e2b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.client = None
        self._connected = False
    
    def connect(self) -> bool:
        """Inicializa la conexión con Ollama."""
        try:
            # Verificar que Ollama está corriendo
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self._connected = True
                print(f"✅ Conectado a Ollama: {self.model}")
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
        
        # Reintentar hasta 2 veces
        for attempt in range(2):
            try:
                response = ollama.chat(
                    model=self.model,
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
                        "temperature": 0.1,
                        "num_predict": 10
                    }
                )
                
                content = response.get("message", {}).get("content", "").strip().upper()
                
                if "BUY" in content:
                    return "BUY"
                elif "SELL" in content:
                    return "SELL"
                else:
                    return "NADA"
                    
            except Exception as e:
                print(f"⚠️ Intento {attempt+1} falló: {e}")
                if attempt == 0:
                    import time
                    time.sleep(1)
                    continue
                return "NADA"
        
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