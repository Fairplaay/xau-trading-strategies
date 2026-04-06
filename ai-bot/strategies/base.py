# -*- coding: utf-8 -*-
"""
Estrategias de trading - Clase base abstracta.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    """Señal de trading."""
    direction: str  # "BUY" o "SELL"
    price: float
    sl: float
    tp1: float
    tp2: float
    reason: str
    confidence: float  # 0.0 - 1.0


class BaseStrategy(ABC):
    """Clase base para estrategias de trading."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre de la estrategia."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción de la estrategia."""
        pass
    
    @property
    @abstractmethod
    def rules(self) -> str:
        """Reglas de la estrategia para el prompt de IA."""
        pass
    
    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """
        Analiza datos de mercado y retorna señal si existe.
        
        Args:
            market_data: Diccionario con datos del mercado
            
        Returns:
            Signal si hay setup, None si no hay
        """
        pass
    
    def get_indicators(self, market_data: Dict[str, Any]) -> Dict:
        """Extrae indicadores del market_data."""
        return {
            "price": market_data.get("price", 0),
            "ema50": market_data.get("ema50", 0),
            "ema200": market_data.get("ema200", 0),
            "rsi": market_data.get("rsi", 50),
            "atr": market_data.get("atr", 0),
            "trend": market_data.get("trend", "NEUTRAL")
        }
    
    def calculate_sl_tp(self, direction: str, price: float, atr: float) -> Dict[str, float]:
        """Calcula Stop Loss y Take Profit basados en ATR."""
        # ATR mínimo y máximo
        atr = max(atr, 0.25)
        atr = min(atr, 1.0)
        
        if direction == "BUY":
            sl = price - (atr * 1.5)
            tp1 = price + (atr * 1.0)
            tp2 = price + (atr * 2.0)
        else:  # SELL
            sl = price + (atr * 1.5)
            tp1 = price - (atr * 1.0)
            tp2 = price - (atr * 2.0)
        
        return {"sl": sl, "tp1": tp1, "tp2": tp2}


# Registry de estrategias disponibles
STRATEGY_REGISTRY: Dict[str, type] = {}


def register_strategy(cls: type):
    """Decorador para registrar estrategias."""
    STRATEGY_REGISTRY[cls.__name__] = cls
    return cls


def get_strategy(name: str) -> Optional[BaseStrategy]:
    """Obtiene una estrategia por nombre."""
    cls = STRATEGY_REGISTRY.get(name)
    if cls:
        return cls()
    return None


def list_strategies() -> Dict[str, str]:
    """Lista todas las estrategias disponibles."""
    return {name: cls().name for name, cls in STRATEGY_REGISTRY.items()}