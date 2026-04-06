# -*- coding: utf-8 -*-
"""
Cliente OpenRouter para IA de trading.
Maneja la conexión y prompts hacia modelos gratuitos.
"""

import os
from typing import Optional, Dict, Any
from openrouter import OpenRouter


# PROMPT INICIAL - Rol Scalper
SYSTEM_PROMPT = """Eres un scalper profesional de XAU/USD en timeframe M1.
Buscas operaciones rápidas con SL ajustados.
Tu objetivo: muchas operaciones pequeñas, profits constantes.
Agresivo pero con gestión de riesgo estricta.

Tu metodología:
- Solo confirmar operaciones cuando el setup sea CLARO
- Priorizar calidad sobre cantidad
- Si hay duda, responder NADA
- Verificar siempre noticias de alto impacto antes de confirmar
- Si hay noticia ±30 min → NO OPERAR"""


class AITradingClient:
    """Cliente para interactuar con modelos de OpenRouter."""
    
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.2-3b-instruct:free", 
                 temperature: float = 0.1, max_tokens: int = 20):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = None
        self._connected = False
        self.initial_context = ""
    
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
    
    def initialize_context(self, memory_context: str = "", learnings_context: str = ""):
        """
        Carga el contexto inicial (solo una vez al iniciar el bot).
        Combina: System Prompt + Memory + Learnings
        """
        self.initial_context = SYSTEM_PROMPT
        
        if memory_context:
            self.initial_context += f"\n\n{memory_context}"
        
        if learnings_context:
            self.initial_context += f"\n\n{learnings_context}"
        
        print(f"📌 Contexto inicial cargado ({len(self.initial_context)} chars)")
    
    def analyze(self, market_data: Dict[str, Any], strategy_rules: str) -> str:
        """
        Analiza datos de mercado y decide señal.
        Usa el contexto inicial + datos actuales.
        
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
                    {"role": "system", "content": self.initial_context},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens
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
            # Retry una vez
            try:
                print("🔄 Reintentando...")
                response = self.client.chat.send(
                    messages=[
                        {"role": "system", "content": self.initial_context},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                decision = response.choices[0].message.content.strip().upper()
                if "BUY" in decision:
                    return "BUY"
                elif "SELL" in decision:
                    return "SELL"
            except Exception as e2:
                print(f"❌ Retry también falló: {e2}")
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
{market_data.get('news_status', 'Sin noticias de alto impacto')}

## Tu Tarea:
Analiza los datos y decide:
- BUY: Si hay señal clara de compra
- SELL: Si hay señal clara de venta  
- NADA: Si no hay setup claro

Responde SOLO con una palabra: BUY, SELL o NADA
"""