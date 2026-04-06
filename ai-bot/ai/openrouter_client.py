# -*- coding: utf-8 -*-
"""
Cliente OpenRouter para IA de trading.
Maneja la conexión y prompts hacia modelos gratuitos.
"""

import os
from typing import Optional, Dict, Any
from openrouter import OpenRouter


class AITradingClient:
    """Cliente para interactuar con modelos de OpenRouter."""
    
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.2-3b-instruct:free"):
        self.api_key = api_key
        self.model = model
        self.client = None
        self._connected = False
    
    def connect(self) -> bool:
        """Inicializa la conexión con OpenRouter."""
        try:
            self.client = OpenRouter(api_key=self.api_key)
            self._connected = True
            print(f"✅ Conectado a OpenRouter: {self.model}")
            return True
        except Exception as e:
            print(f"❌ Error conectando a OpenRouter: {e}")
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
        if not self._connected or not self.client:
            return "NADA"
        
        # Construir prompt
        prompt = self._build_prompt(market_data, strategy_rules)
        
        try:
            response = self.client.chat.send(
                messages=[
                    {"role": "system", "content": "Eres un asistente de trading experto. Responde solo con BUY, SELL o NADA."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model
            )
            
            decision = response.choices[0].message.content.strip().upper()
            
            # Normalizar respuesta
            if "BUY" in decision:
                return "BUY"
            elif "SELL" in decision:
                return "SELL"
            else:
                return "NADA"
                
        except Exception as e:
            print(f"❌ Error en análisis IA: {e}")
            return "NADA"
    
    def _build_prompt(self, market_data: Dict, strategy_rules: str) -> str:
        """Construye el prompt para la IA."""
        return f"""
Eres un asistente de trading de XAU/USD.

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
{market_data.get('news_status', 'Sin noticias de alto impacto')}

## Tu Tarea:
Analiza los datos y decide:
- BUY: Si hay señal clara de compra
- SELL: Si hay señal clara de venta  
- NADA: Si no hay setup claro

Responde SOLO con una palabra: BUY, SELL o NADA
"""