# -*- coding: utf-8 -*-
"""
Features - Crear features para ML desde datos del mercado

Transforma datos crudos (precios, indicadores) en features listos para sklearn.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional


class Features:
    """Crea features para el modelo ML."""
    
    def __init__(self):
        self.feature_names = [
            'rsi',
            'ema50_position',      # precio vs EMA50
            'ema200_position',     # precio vs EMA200
            'ema50_ema200_diff',   # distancia entre EMAs
            'atr',
            'atr_position',        # ATR vs promedio
            'trend',               # 1=alcista, 0=bajista
            'rsi_change',         # cambio RSI en últimas 3 velas
            'price_change',       # cambio precio últimos 3 velas
            'volatility',         # rango últimas 10 velas
            'volume_avg',         # volumen promedio
        ]
    
    def calculate_from_rates(self, rates: List[List]) -> pd.DataFrame:
        """
        Calcular features desde rates (OHLCV).
        
        Args:
            rates: Lista de [time, open, high, low, close, tick_volume, spread, real_volume]
            
        Returns:
            DataFrame con features calculados
        """
        if not rates or len(rates) < 50:
            return pd.DataFrame()
        
        df = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'
        ])
        
        features_list = []
        total = len(df)
        
        for i in range(50, len(df)):
            # Progress cada 1000 velas
            if (i - 50) % 1000 == 0:
                print(f"   🔄 Features: {i - 50}/{total - 50} ({((i - 50) * 100 / (total - 50)):.0f}%)")
            
            window = df.iloc[:i+1]
            
            close = window['close'].values
            high = window['high'].values
            low = window['low'].values
            volume = window['tick_volume'].values
            
            # RSI 14
            rsi = self._calculate_rsi(close, 14)
            
            # EMAs
            ema50 = self._calculate_ema(close, 50)
            ema200 = self._calculate_ema(close, 200)
            
            # ATR 14
            atr = self._calculate_atr(window, 14)
            
            # Posición actual
            current_price = close[-1]
            
            # Features
            features = {
                'rsi': rsi,
                'ema50_position': current_price - ema50,
                'ema200_position': current_price - ema200,
                'ema50_ema200_diff': ema50 - ema200,
                'atr': atr,
                'atr_position': atr / np.mean(close[-20:-1]) if len(close) > 20 else 1,
                'trend': 1 if current_price > ema200 else 0,
                'rsi_change': rsi - self._calculate_rsi(close[:-3], 14) if len(close) > 3 else 0,
                'price_change': (close[-1] - close[-4]) / close[-4] * 100 if len(close) >= 4 else 0,
                'volatility': (np.max(high[-10:]) - np.min(low[-10:])) / np.mean(close[-10:]) * 100,
                'volume_avg': np.mean(volume[-10:]),
            }
            
            features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def calculate_from_market_data(self, market_data: Dict[str, Any], rates: Optional[List] = None) -> List[float]:
        """
        Calcular features desde datos actuales del mercado (para predicción en vivo).
        
        Args:
            market_data: Diccionario con price, ema50, ema200, rsi, atr, trend
            rates: Lista de rates para calcular features adicionales (opcional)
            
        Returns:
            Lista de features [rsi, ema50_position, ...]
        """
        price = market_data.get('price', 0)
        ema50 = market_data.get('ema50', 0)
        ema200 = market_data.get('ema200', 0)
        rsi = market_data.get('rsi', 50)
        atr = market_data.get('atr', 0.5)
        trend = market_data.get('trend', 'NEUTRAL')
        
        # Calcular ATR position si tenemos rates
        atr_position = 1
        if rates and len(rates) > 20:
            closes = [r[4] for r in rates]
            avg_price = np.mean(closes[-20:])
            atr_position = atr / avg_price if avg_price > 0 else 1
        
        trend_val = 1 if trend == 'ALCISTA' else 0
        
        return [
            rsi,
            price - ema50 if ema50 else 0,
            price - ema200 if ema200 else 0,
            (ema50 - ema200) if ema50 and ema200 else 0,
            atr,
            atr_position,
            trend_val,
            0,  # rsi_change - no disponible en vivo
            0,  # price_change - no disponible en vivo
            0,  # volatility - no disponible en vivo
            0,  # volume_avg - no disponible en vivo
        ]
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcular EMA."""
        if len(prices) < period:
            return prices[-1] if len(prices) > 0 else 0
        
        sma = np.mean(prices[-period:])
        multiplier = 2 / (period + 1)
        ema = sma
        
        for price in reversed(prices[:-period]):
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calcular RSI."""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcular ATR."""
        if len(df) < period + 1:
            return 0.5
        
        tr = []
        for i in range(1, len(df)):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            prev_close = df.iloc[i-1]['close']
            
            tr.append(max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            ))
        
        return np.mean(tr[-period:]) if tr else 0.5
    
    def create_labels_from_rates(self, rates: List[List], profit_threshold: float = 0.5) -> pd.Series:
        """
        Crear labels (target) desde rates.
        
        BUY: siguiente vela tuvo profit > threshold
        SELL: siguiente vela tuvo pérdida > threshold  
        NADA: ninguna
        
        Args:
            rates: Lista de rates OHLCV
            profit_threshold: Profit mínimo en $ para considerar BUY
            
        Returns:
            Series con labels
        """
        if not rates or len(rates) < 50:
            return pd.Series()
        
        df = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'
        ])
        
        labels = []
        
        for i in range(50, len(df) - 1):
            current_close = df.iloc[i]['close']
            next_close = df.iloc[i + 1]['close']
            
            # Calcular diferencia
            diff = next_close - current_close
            
            if diff > profit_threshold:
                labels.append('BUY')
            elif diff < -profit_threshold:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        # Ajustar para que coincida con features (skip last row since no next)
        # Features starts at index 50, so labels should start at 50
        while len(labels) < 50:
            labels.insert(0, 'NADA')
        
        return pd.Series(labels[:len(df)-50+50]) if len(labels) > 0 else pd.Series()
    
    def create_labels_from_close(self, closes: List[float], profit_threshold: float = 0.5) -> List[str]:
        """
        Crear labels desde lista de precios de cierre.
        
        Args:
            closes: Lista de precios de cierre
            profit_threshold: Profit mínimo para BUY
            
        Returns:
            Lista de labels
        """
        if not closes or len(closes) < 2:
            return ['NADA'] * len(closes)
        
        labels = ['NADA', 'NADA']  # Primeros dos no tienen anterior
        
        for i in range(2, len(closes)):
            diff = closes[i] - closes[i-1]
            
            if diff > profit_threshold:
                labels.append('BUY')
            elif diff < -profit_threshold:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        return labels