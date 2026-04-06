# -*- coding: utf-8 -*-
"""
Cliente Ollama para IA de trading.
Conecta a Ollama local (Gemma 4) en vez de OpenRouter.
"""

import ollama
from typing import Optional, Dict, Any


# Modelos disponibles (fallback chain) - qwen2 para mejor rendimiento
MODELS = ["qwen2:0.5b", "gemma4:e2b"]


# System prompt optimizado para trading profesional
SYSTEM_PROMPT = """Eres un ANALISTA PROFESIONAL de trading para XAUUSD (oro) en timeframe M1 (1 minuto).

## CONTEXTO
- Mercado: XAUUSD (XAU/USD)
- Broker: Vantage International
- Spread típico: 15-30 pips
- Horario: 24/5 (lunes-viernes)
- Tu rol: CONFIRMAR o RECHAZAR señales del sistema de trading

## REGLAS DE DECISIÓN

### CONFIRMAR SELL si:
- Precio ESTÁ POR DEBAJO de EMA50
- RSI < 70 (no sobrecompra)
- Tendencia = BAJISTA o NEUTRAL
- No hay noticias de alto impacto en ±30 min

### CONFIRMAR BUY si:
- Precio ESTÁ POR ENCIMA de EMA50
- RSI > 30 (no sobreventa)
- Tendencia = ALCISTA o NEUTRAL
- No hay noticias de alto impacto en ±30 min

### RECHAZAR (NADA) si:
- RSI en sobrecompra (>70) o sobreventa (<30)
- Precio muy cerca de EMA50 (dentro de 5 pips = indecisión)
- Noticia de alto impacto en menos de 30 minutos
- Spread > 40 pips (anormal)
- Vela reciente muy pequeña (< 5 pips de rango)

## FORMATO DE RESPUESTA
ESCRIBE SOLO UNA PALABRA:
- SELL → Ejecutar venta
- BUY → Ejecutar compra  
- NADA → No hacer nada, esperar siguiente vela

NO escribas nada más. Solo SELL, BUY o NADA."""


class OllamaClient:
    """Cliente para conectar a Ollama local."""
    
    def __init__(self, model: str = None, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        
        if model:
            self.models = [model]
        else:
            self.models = MODELS
        
        self.current_model = None
        self.client = None
        self._connected = False
        self.initial_context = SYSTEM_PROMPT
    
    def initialize_context(self, memory_context: str = "", learnings_context: str = ""):
        """Carga el contexto inicial."""
        context = SYSTEM_PROMPT
        
        if memory_context:
            context += f"\n\nContexto de memoria: {memory_context}"
        
        if learnings_context:
            context += f"\n\nAprendizajes: {learnings_context}"
        
        self.initial_context = context
        print(f"📌 Contexto IA cargado ({len(self.initial_context)} chars)")
    
    def connect(self) -> bool:
        """Inicializa la conexión con Ollama."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
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
            return False
    
    def analyze(self, market_data: Dict[str, Any], strategy_rules: str) -> str:
        """
        Analiza datos de mercado y decide señal.
        """
        if not self._connected:
            return "NADA"
        
        prompt = self._build_prompt(market_data, strategy_rules)
        
        for model in self.models:
            try:
                response = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.initial_context},
                        {"role": "user", "content": prompt}
                    ],
                    options={
                        "temperature": 0.0,
                        "num_predict": 3,
                        "repeat_penalty": 1.5
                    }
                )
                
                content = response.get("message", {}).get("content", "").strip().upper()
                
                print(f"   [IA] Response: {content[:50]}...")
                
                # Detectar palabras clave
                buy_words = ["BUY", "LONG", "CALL"]
                sell_words = ["SELL", "SHORT", "PUT"]
                
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
        return f"""## SEÑAL DEL SISTEMA
Dirección: {strategy_rules.get('direction', 'N/A')}

## DATOS DEL MERCADO
- Precio: ${market_data.get('price', 'N/A')}
- EMA50: ${market_data.get('ema50', 'N/A')}
- EMA200: ${market_data.get('ema200', 'N/A')}
- RSI: {market_data.get('rsi', 'N/A')}
- ATR: ${market_data.get('atr', 'N/A')}
- Tendencia: {market_data.get('trend', 'N/A')}
- Noticias: {market_data.get('news_status', 'Sin noticias')}

Responde SOLO: SELL, BUY o NADA"""