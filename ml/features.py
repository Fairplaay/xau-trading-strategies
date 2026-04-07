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
                
                # Return 1d (retorno últimas 24 horas)
                return_1d = (close[-1] - close[-2]) / close[-2] * 100 if len(close) >= 2 else 0
                
                # Return 5d
                return_5d = (close[-1] - close[-6]) / close[-6] * 100 if len(close) >= 6 else 0
                
                # Volatilidad 5 y 15
                volatility_5 = np.std(close[-5:]) if len(close) >= 5 else 0
                volatility_15 = np.std(close[-15:]) if len(close) >= 15 else 0
                
                # MACD (12, 26, 9)
                ema12 = self._calculate_ema(close, 12)
                ema26 = self._calculate_ema(close, 26)
                macd = ema12 - ema26
                macd_signal = macd - self._calculate_ema(np.append(close[-9:], macd), 9) if len(close) >= 9 else macd
                
                # Bollinger Bands
                bb_period = 20
                bb_std = np.std(close[-bb_period:]) if len(close) >= bb_period else 0
                bb_ma = np.mean(close[-bb_period:]) if len(close) >= bb_period else close[-1]
                bb_upper = bb_ma + (bb_std * 2)
                bb_lower = bb_ma - (bb_std * 2)
                bb_width = (bb_upper - bb_lower) / bb_ma * 100 if bb_ma > 0 else 0
                
                # Stochastic (14, 3, 3)
                stoch_k = 0
                stoch_d = 0
                if len(close) >= 14:
                    low14 = np.min(low[-14:])
                    high14 = np.max(high[-14:])
                    stoch_k = ((close[-1] - low14) / (high14 - low14)) * 100 if (high14 - low14) > 0 else 50
                    stoch_d = stoch_k  # Simplificado
                
                # ADX (14)
                adx = self._calculate_adx(window, 14)
                
                # Momentum 5
                momentum_5 = (close[-1] - close[-6]) / close[-6] * 100 if len(close) >= 6 else 0
                
                # Time features (desde timestamp)
                if len(rates) > i and rates[i][0] > 0:
                    import datetime
                    try:
                        ts = datetime.datetime.fromtimestamp(rates[i][0])
                        hour_of_day = ts.hour
                        day_of_week = ts.weekday()
                    except:
                        hour_of_day = 12
                        day_of_week = 3
                else:
                    hour_of_day = 12
                    day_of_week = 3
                
                # Posición actual
                current_price = close[-1]
                
                # Features (los que usa la investigación)
                features = {
                    # Originales
                    'rsi': rsi,
                    'ema50_position': current_price - ema50,
                    'ema200_position': current_price - ema200,
                    'ema50_ema200_diff': ema50 - ema200,
                    'atr': atr,
                    'trend': 1 if current_price > ema200 else 0,
                    
                    # Nuevos de la investigación
                    'return_1d': return_1d,
                    'return_5d': return_5d,
                    'volatility_5': volatility_5,
                    'volatility_15': volatility_15,
                    'macd': macd,
                    'macd_signal': macd_signal,
                    'bb_upper': bb_upper,
                    'bb_lower': bb_lower,
                    'bb_width': bb_width,
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d,
                    'adx': adx,
                    'momentum_5': momentum_5,
                    'hour_of_day': hour_of_day,
                    'day_of_week': day_of_week,
                }
                
                features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def calculate_from_market_data(self, market_data: Dict[str, Any], rates: Optional[List] = None) -> List[float]:
        """Calcular los 18 features desde datos actuales del mercado."""
        price = market_data.get('price', 0)
        ema50 = market_data.get('ema50', 0)
        ema200 = market_data.get('ema200', 0)
        rsi = market_data.get('rsi', 50)
        atr = market_data.get('atr', 0.5)
        trend = market_data.get('trend', 'NEUTRAL')
        
        closes = []
        if rates:
            closes = [r[4] for r in rates]
        
        # Calcular features adicionales
        return_1d = 0
        return_5d = 0
        volatility_5 = 0
        volatility_15 = 0
        macd = 0
        macd_signal = 0
        bb_upper = 0
        bb_lower = 0
        bb_width = 0
        stoch_k = 50
        stoch_d = 50
        adx = 25
        momentum_5 = 0
        hour_of_day = 12
        day_of_week = 3
        
        if len(closes) >= 2:
            return_1d = (closes[-1] - closes[-2]) / closes[-2] * 100
        if len(closes) >= 6:
            return_5d = (closes[-1] - closes[-6]) / closes[-6] * 100
        if len(closes) >= 5:
            volatility_5 = np.std(closes[-5:])
        if len(closes) >= 15:
            volatility_15 = np.std(closes[-15:])
        if len(closes) >= 26:
            ema12 = self._calculate_ema(np.array(closes), 12)
            ema26 = self._calculate_ema(np.array(closes), 26)
            macd = ema12 - ema26
        if len(closes) >= 35:
            macd_signal = macd - self._calculate_ema(np.array(closes[-9:] + [macd]*9), 9)
        
        # Bollinger
        if len(closes) >= 20:
            bb_std = np.std(closes[-20:])
            bb_ma = np.mean(closes[-20:])
            bb_upper = bb_ma + (bb_std * 2)
            bb_lower = bb_ma - (bb_std * 2)
            bb_width = (bb_upper - bb_lower) / bb_ma * 100 if bb_ma > 0 else 0
        
        # Time
        if rates and len(rates) > 0 and rates[-1][0] > 0:
            try:
                import datetime
                ts = datetime.datetime.fromtimestamp(rates[-1][0])
                hour_of_day = ts.hour
                day_of_week = ts.weekday()
            except:
                pass
        
        trend_val = 1 if trend == 'ALCISTA' else 0
        
        # Los 18 features (orden matching con features.py calculate_from_rates)
        return [
            # Originales (7)
            rsi,
            price - ema50 if ema50 else 0,
            price - ema200 if ema200 else 0,
            (ema50 - ema200) if ema50 and ema200 else 0,
            atr,
            trend_val,
            
            # Nuevos (11)
            return_1d,
            return_5d,
            volatility_5,
            volatility_15,
            macd,
            macd_signal,
            bb_upper,
            bb_lower,
            bb_width,
            stoch_k,
            stoch_d,
            adx,
            momentum_5,
            hour_of_day,
            day_of_week,
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
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcular ADX (Average Directional Index)."""
        if len(df) < period + 2:
            return 25  # Valor por defecto (tendencia neutral)
        
        # Calcular +DM y -DM
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(df)):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            
            up_move = high - prev_high
            down_move = prev_low - low
            
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
        
        # Calcular ATR
        atr = self._calculate_atr(df, period)
        
        if atr == 0:
            return 25
        
        # Calcular +DI y -DI
        plus_di = (np.mean(plus_dm[-period:]) / atr) * 100
        minus_di = (np.mean(minus_dm[-period:]) / atr) * 100
        
        # Calcular DX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 25
        
        dx = abs(plus_di - minus_di) / di_sum * 100
        
        return dx  # Esto es aproximadamente ADX (simplificado)
