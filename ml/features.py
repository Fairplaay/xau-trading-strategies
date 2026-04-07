# -*- coding: utf-8 -*-
"""
Features - Cálculo vectorizado de features para ML (version optimizada)
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any


class Features:
    """Crea features para el modelo ML (version vectorizada rapida)."""
    
    def __init__(self):
        # Los 18 features (para estrategia sin_reglas)
        self.feature_names = [
            # Originales (6)
            'rsi',
            'ema50_position',
            'ema200_position',
            'ema50_ema200_diff',
            'atr',
            'trend',
            # Nuevos (12)
            'return_1d',
            'return_5d',
            'volatility_5',
            'volatility_15',
            'macd',
            'macd_signal',
            'bb_upper',
            'bb_lower',
            'bb_width',
            'stoch_k',
            'stoch_d',
            'adx',
            'momentum_5',
            'hour_of_day',
            'day_of_week',
        ]
    
    def calculate_from_rates(self, rates: List[List]) -> pd.DataFrame:
        """
        Calcular features desde rates (OHLCV) - VERSION VECTORIZADA.
        """
        if not rates or len(rates) < 50:
            return pd.DataFrame()
        
        # Crear DataFrame
        df = pd.DataFrame(rates, columns=[
            'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'
        ])
        
        print(f"📊 Calculando features para {len(df)} velas (vectorizado)...")
        
        # Calcular TODOS los features de forma vectorizada
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        # ===== INDICADORES BASICOS (vectorizados) =====
        
        # RSI (14) - vectorizado
        df['rsi'] = self._rsi_vectorized(close, 14)
        
        # EMAs (vectorizado con pandas ewm)
        df['ema50'] = pd.Series(close).ewm(span=50, adjust=False).mean().values
        df['ema200'] = pd.Series(close).ewm(span=200, adjust=False).mean().values
        
        # ATR (14) - vectorizado
        df['atr'] = self._atr_vectorized(high, low, close, 14)
        
        # ===== INDICADORES AVANZADOS (vectorizados) =====
        
        # Returns
        df['return_1d'] = pd.Series(close).pct_change(1).fillna(0).values * 100
        df['return_5d'] = pd.Series(close).pct_change(5).fillna(0).values * 100
        
        # Volatilidad (rolling std)
        df['volatility_5'] = pd.Series(close).rolling(5).std().fillna(0).values
        df['volatility_15'] = pd.Series(close).rolling(15).std().fillna(0).values
        
        # MACD (12, 26, 9)
        ema12 = pd.Series(close).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close).ewm(span=26, adjust=False).mean()
        df['macd'] = (ema12 - ema26).values
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean().values
        
        # Bollinger Bands (20, 2)
        bb_period = 20
        df['bb_ma'] = pd.Series(close).rolling(bb_period).mean()
        df['bb_std'] = pd.Series(close).rolling(bb_period).std()
        df['bb_upper'] = (df['bb_ma'] + 2 * df['bb_std']).values
        df['bb_lower'] = (df['bb_ma'] - 2 * df['bb_std']).values
        df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_ma'] * 100).values
        
        # Stochastic (14, 3, 3)
        low14 = pd.Series(low).rolling(14).min()
        high14 = pd.Series(high).rolling(14).max()
        stoch_k = ((close - low14) / (high14 - low14) * 100)
        df['stoch_k'] = stoch_k.fillna(50).values
        df['stoch_d'] = stoch_k.rolling(3).mean().fillna(50).values
        
        # ADX (simplificado)
        df['adx'] = self._adx_vectorized(high, low, close, 14)
        
        # Momentum
        df['momentum_5'] = pd.Series(close).pct_change(5).fillna(0).values * 100
        
        # Time features
        if 'time' in df.columns and df['time'].iloc[0] > 0:
            try:
                df['datetime'] = pd.to_datetime(df['time'], unit='s')
                df['hour_of_day'] = df['datetime'].dt.hour
                df['day_of_week'] = df['datetime'].dt.dayofweek
            except:
                df['hour_of_day'] = 12
                df['day_of_week'] = 3
        else:
            df['hour_of_day'] = 12
            df['day_of_week'] = 3
        
        # ===== FEATURES FINALES =====
        close_series = df['close']
        
        features_df = pd.DataFrame({
            # Originales
            'rsi': df['rsi'],
            'ema50_position': close_series - df['ema50'],
            'ema200_position': close_series - df['ema200'],
            'ema50_ema200_diff': df['ema50'] - df['ema200'],
            'atr': df['atr'],
            'trend': (close_series > df['ema200']).astype(int),
            
            # Nuevos
            'return_1d': df['return_1d'],
            'return_5d': df['return_5d'],
            'volatility_5': df['volatility_5'],
            'volatility_15': df['volatility_15'],
            'macd': df['macd'],
            'macd_signal': df['macd_signal'],
            'bb_upper': df['bb_upper'],
            'bb_lower': df['bb_lower'],
            'bb_width': df['bb_width'],
            'stoch_k': df['stoch_k'],
            'stoch_d': df['stoch_d'],
            'adx': df['adx'],
            'momentum_5': df['momentum_5'],
            'hour_of_day': df['hour_of_day'],
            'day_of_week': df['day_of_week'],
        })
        
        # Limpiar NaN (solo los primeros 200 que no tienen suficientes datos)
        features_df = features_df.iloc[200:].reset_index(drop=True)
        
        print(f"   ✅ {len(features_df)} samples generados")
        
        return features_df
    
    def _rsi_vectorized(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI vectorizado usando pandas."""
        series = pd.Series(prices)
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.fillna(50).values
    
    def _atr_vectorized(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """ATR vectorizado."""
        high_s = pd.Series(high)
        low_s = pd.Series(low)
        close_s = pd.Series(close)
        
        tr1 = high_s - low_s
        tr2 = (high_s - close_s.shift(1)).abs()
        tr3 = (low_s - close_s.shift(1)).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr.fillna(0.5).values
    
    def _adx_vectorized(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """ADX simplificado vectorizado."""
        high_s = pd.Series(high)
        low_s = pd.Series(low)
        close_s = pd.Series(close)
        
        plus_dm = high_s.diff()
        minus_dm = -low_s.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        atr = self._atr_vectorized(high, low, close, period)
        
        plus_di = (plus_dm.rolling(window=period).mean() / atr) * 100
        minus_di = (minus_dm.rolling(window=period).mean() / atr) * 100
        
        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di) * 100)
        
        return dx.fillna(25).values
    
    def calculate_from_market_data(self, market_data: Dict[str, Any], rates: Optional[List] = None) -> List[float]:
        """Calcular los 18 features desde datos actuales del mercado (para predictor)."""
        price = market_data.get('price', 0)
        ema50 = market_data.get('ema50', 0)
        ema200 = market_data.get('ema200', 0)
        rsi = market_data.get('rsi', 50)
        atr = market_data.get('atr', 0.5)
        trend = market_data.get('trend', 'NEUTRAL')
        
        closes = []
        if rates:
            closes = [r[4] for r in rates]
        
        # Features basics
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
            series = pd.Series(closes)
            ema12_val = series.ewm(span=12, adjust=False).mean().iloc[-1]
            ema26_val = series.ewm(span=26, adjust=False).mean().iloc[-1]
            macd = ema12_val - ema26_val
        
        if len(closes) >= 20:
            series = pd.Series(closes)
            bb_std = series.tail(20).std()
            bb_ma = series.tail(20).mean()
            bb_upper = bb_ma + (bb_std * 2)
            bb_lower = bb_ma - (bb_std * 2)
            bb_width = (bb_upper - bb_lower) / bb_ma * 100 if bb_ma > 0 else 0
        
        if rates and len(rates) > 0 and rates[-1][0] > 0:
            try:
                import datetime
                ts = datetime.datetime.fromtimestamp(rates[-1][0])
                hour_of_day = ts.hour
                day_of_week = ts.weekday()
            except:
                pass
        
        trend_val = 1 if trend == 'ALCISTA' else 0
        
        return [
            rsi,
            price - ema50 if ema50 else 0,
            price - ema200 if ema200 else 0,
            (ema50 - ema200) if ema50 and ema200 else 0,
            atr,
            trend_val,
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