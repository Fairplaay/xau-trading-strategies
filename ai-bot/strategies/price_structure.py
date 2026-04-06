# -*- coding: utf-8 -*-
"""
Estrategia B: Estructura de Precio
Price action + estructura + Stoch + CCI
"""

from typing import Dict, Any, Optional
from .base import BaseStrategy, Signal, register_strategy


@register_strategy
class STRUCTURE(BaseStrategy):
    """Estrategia basada en estructura de precio."""
    
    @property
    def name(self) -> str:
        return "Price Structure"
    
    @property
    def description(self) -> str:
        return "Estrategia basada en estructura de precio, Stoch, CCI y RSI"
    
    @property
    def rules(self) -> str:
        return """
## Reglas de la Estrategia Price Structure:

### CONDICIONES PARA BUY:
1. Precio en zona de soporte (swing low reciente)
2. Stoch %K cruzando hacia arriba desde zona de sobreventa (<20)
3. CCI > -100 (sale de sobreventa)
4. RSI > 40 (momentum no bajista)
5. ATR > 8 pips (suficiente volatilidad)

### CONDICIONES PARA SELL:
1. Precio en zona de resistencia (swing high reciente)
2. Stoch %K cruzando hacia abajo desde zona de sobrecompra (>80)
3. CCI < 100 (sale de sobrecompra)
4. RSI < 60 (momentum no alcista)
5. ATR > 8 pips (suficiente volatilidad)

### GATES RÍGIDOS (todos deben cumplirse):
- ATR > 8 pips (si no, skip)
- NO operar durante noticias de alto impacto
- NO operar 21:00-22:00 UTC (fin de sesión NY)

### NO OPERAR SI:
- Mercado en rango estrecho
- Alta volatilidad por noticias
- Fuera de horas operativas
"""
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Analiza el mercado y retorna señal.
        
        Args:
            market_data debe contener:
                - price: precio actual
                - stoch_k: Stochastic %K
                - stoch_d: Stochastic %D
                - cci: Commodity Channel Index
                - rsi: RSI 14
                - atr: ATR 14 (en pips)
                - swing_high: precio del swing high reciente
                - swing_low: precio del swing low reciente
        """
        price = market_data.get("price", 0)
        stoch_k = market_data.get("stoch_k", 50)
        stoch_d = market_data.get("stoch_d", 50)
        cci = market_data.get("cci", 0)
        rsi = market_data.get("rsi", 50)
        atr = market_data.get("atr", 0)
        swing_high = market_data.get("swing_high", 0)
        swing_low = market_data.get("swing_low", 0)
        
        # Gate: ATR mínimo
        if atr < 8:
            return None
        
        # Validar datos
        if not all([price, stoch_k, stoch_d, cci, rsi]):
            return None
        
        # Calcular SL/TP
        sl_tp = self.calculate_sl_tp("BUY", price, atr)
        
        # BUY: Stoch cruza arriba desde sobreventa + CCI sale de sobreventa
        if (stoch_k < 20 or (stoch_k < stoch_d and stoch_k < 30)) and \
           cci > -100 and rsi > 40:
            return Signal(
                direction="BUY",
                price=price,
                sl=sl_tp["sl"],
                tp1=sl_tp["tp1"],
                tp2=sl_tp["tp2"],
                reason=f"Stoch={stoch_k:.0f}, CCI={cci:.0f}, RSI={rsi}",
                confidence=0.6
            )
        
        # SELL: Stoch cruza abajo desde sobrecompra + CCI sale de sobrecompra
        if (stoch_k > 80 or (stoch_k > stoch_d and stoch_k > 70)) and \
           cci < 100 and rsi < 60:
            return Signal(
                direction="SELL",
                price=price,
                sl=sl_tp["sl"],
                tp1=sl_tp["tp1"],
                tp2=sl_tp["tp2"],
                reason=f"Stoch={stoch_k:.0f}, CCI={cci:.0f}, RSI={rsi}",
                confidence=0.6
            )
        
        return None