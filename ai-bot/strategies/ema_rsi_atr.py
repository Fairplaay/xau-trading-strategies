# -*- coding: utf-8 -*-
"""
Estrategia A: EMA/RSI/ATR
Filtro de tendencia: precio > EMA200 = Alcista, precio < EMA200 = Bajista
"""

from typing import Dict, Any, Optional
from .base import BaseStrategy, Signal, register_strategy


@register_strategy
class EMARSIATRStrategy(BaseStrategy):
    """Estrategia EMA + RSI + ATR."""
    
    @property
    def name(self) -> str:
        return "EMA/RSI/ATR"
    
    @property
    def description(self) -> str:
        return "Estrategia basada en EMA50, EMA200, RSI14 y ATR14 para scalping XAU/USD"
    
    @property
    def rules(self) -> str:
        return """
## Reglas de la Estrategia EMA/RSI/ATR:

### CONDICIONES PARA BUY:
1. Precio POR ENCIMA de EMA200 (tendencia alcista)
2. Precio hace pullback y toca/acerca a EMA50 (máx $2-4 de distancia)
3. RSI > 45 con tendencia al alza en últimas 3 velas
4. Vela de confirmación: martillo, envolvente alcista, o pin bar alcista

### CONDICIONES PARA SELL:
1. Precio POR DEBAJO de EMA200 (tendencia bajista)
2. Precio hace pullback y sube hacia EMA50 (máx $2-4 de distancia)
3. RSI < 55 con tendencia a la baja en últimas 3 velas
4. Vela de confirmación: estrella fugaz, envolvente bajista, pin bar bajista

### NO OPERAR SI:
- Precio muy lejos de EMA50 (>$5)
- RSI extremo (>70 para BUY, <30 para SELL)
- Mercado plano (rango < $1 en últimas 10 velas)
- Durante ventana de noticias de alto impacto

### SL/TP (basados en ATR):
- SL: precio ± (ATR × 1.5), mínimo $0.25, máximo $1.00
- TP1: precio ± (ATR × 1.0) → cerrar 50%
- TP2: precio ± (ATR × 2.0) → cerrar resto
"""
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Analiza el mercado y retorna señal si hay setup.
        
        Args:
            market_data debe contener:
                - price: precio actual
                - ema50: EMA 50
                - ema200: EMA 200
                - rsi: RSI 14
                - atr: ATR 14
                - trend: "ALCISTA" | "BAJISTA" | "NEUTRAL"
        """
        price = market_data.get("price", 0)
        ema50 = market_data.get("ema50", 0)
        ema200 = market_data.get("ema200", 0)
        rsi = market_data.get("rsi", 50)
        atr = market_data.get("atr", 0.5)
        trend = market_data.get("trend", "NEUTRAL").upper()
        
        # Validar datos mínimos
        if not all([price, ema50, ema200, rsi]):
            return None
        
        # Verificar distancia a EMA50 (máx $4)
        distance_to_ema50 = abs(price - ema50)
        if distance_to_ema50 > 4:
            return None
        
        # Verificar RSI no extremo
        if rsi > 70 or rsi < 30:
            return None
        
        # Calcular SL/TP
        sl_tp = self.calculate_sl_tp("BUY" if trend == "ALCISTA" else "SELL", price, atr)
        
        # Lógica BUY
        if trend == "ALCISTA" and ema50 < price and 45 <= rsi <= 70:
            return Signal(
                direction="BUY",
                price=price,
                sl=sl_tp["sl"],
                tp1=sl_tp["tp1"],
                tp2=sl_tp["tp2"],
                reason=f"Precio toca EMA50 (${ema50:.2f}), RSI={rsi}, tendencia Alcista",
                confidence=0.7
            )
        
        # Lógica SELL
        if trend == "BAJISTA" and ema50 > price and 30 <= rsi <= 55:
            return Signal(
                direction="SELL",
                price=price,
                sl=sl_tp["sl"],
                tp1=sl_tp["tp1"],
                tp2=sl_tp["tp2"],
                reason=f"Precio toca EMA50 (${ema50:.2f}), RSI={rsi}, tendencia Bajista",
                confidence=0.7
            )
        
        return None