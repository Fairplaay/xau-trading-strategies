# -*- coding: utf-8 -*-
"""
Features - Crear features para ML desde datos del mercado

Transforma datos crudos (precios, indicadores) en features listos para sklearn.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from tqdm import tqdm


class Features:
    """Crea features para el modelo ML."""
    
    def __init__(self):
        self.feature_names = [
            'rsi',
            'ema50_position',
            'ema200_position',
            'ema50_ema200_diff',
            'atr',
            'atr_position',
            'trend',
            'rsi_change',
            'price_change',
            'volatility',
            'volume_avg',
        ]
    
    def calculate_from_rates(self, rates: List[List]) -> pd.DataFrame:
        """
        Calcular features desde rates (OHLCV).
        """
        if not rates or len(rates) < 50:
            return pd.DataFrame()
        
        df = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'
        ])
        
        features_list = []
        
        # Progress bar con tqdm
        total = len(df) - 50
        with tqdm(total=total, desc="Features", unit="vela") as pbar:
            for i in range(50, len(df)):
                pbar.update(1)
                
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
                    'atr_position': atr / np.mean(close[-10:-1]) if len(close) > 10 else 1,
                    'trend': 1 if current_price > ema200 else 0,
                    # Simplificados: solo 1 vela en vez de 3-10
                    'rsi_change': rsi - self._calculate_rsi(close[:-1], 14) if len(close) > 1 else 0,
                    'price_change': (close[-1] - close[-2]) / close[-2] * 100 if len(close) >= 2 else 0,
                    'volatility': (max(high[-5:]) - min(low[-5:])) / np.mean(close[-5:]) * 100,
                    'volume_avg': np.mean(volume[-5:]),  # Reducido de 10 a 5
                }
                
                features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def calculate_from_market_data(self, market_data: Dict[str, Any], rates: Optional[List] = None) -> List[float]:
        """Calcular features desde datos actuales del mercado."""
        price = market_data.get('price', 0)
        ema50 = market_data.get('ema50', 0)
        ema200 = market_data.get('ema200', 0)
        rsi = market_data.get('rsi', 50)
        atr = market_data.get('atr', 0.5)
        trend = market_data.get('trend', 'NEUTRAL')
        
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
            0, 0, 0, 0,
        ]
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        if len(prices) < period:
            return prices[-1] if len(prices) > 0 else 0
        
        sma = np.mean(prices[-period:])
        multiplier = 2 / (period + 1)
        ema = sma
        
        for price in reversed(prices[:-period]):
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
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
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
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
