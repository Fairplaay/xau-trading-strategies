# -*- coding: utf-8 -*-
"""
Trainer - Entrenar modelo ML para trading

Usa scikit-learn RandomForestClassifier.
Soporta múltiples estrategias de labels (ver ml/labels.py):
- ema_rsi: Lógica EMA/RSI
- price_structure: Price action

参考: ctx7 docs /websites/scikit-learn_stable "RandomForestClassifier"
"""

import os
import json
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score

from .features import Features
from .labels import LabelStrategyManager


# Estrategias de labels disponibles
LABEL_STRATEGIES = {
    'emas': 'EMAs (Triple Confirmación) - EMA200 + RSI + EMA50/breaks',
    'price_structure': 'Price Structure (soporte/resistencia)',
    'rsi_divergence': 'RSI Divergencia (precio nuevo minimo/maximo pero RSI opposite)'
}


class Trainer:
    """Entrena modelo ML para predicción de trading."""
    
    def __init__(self, model_path: str = "modelo_xau.pkl", label_strategy: str = 'ema_rsi'):
        self.model_path = model_path
        self.label_strategy = label_strategy
        self.model = None
        self.features_engine = Features()
        self.feature_names = None
        self.is_trained = False
    
    def train_from_json(self, json_path: str, test_size: float = 0.2) -> dict:
        """
        Entrenar modelo desde archivo JSON con datos históricos.
        
        Args:
            json_path: Ruta al archivo JSON (xau_data.json del EA)
            test_size: Porcentaje de datos para test (0.2 = 20%)
            label_strategy: 'ema_rsi' o 'price_structure'
            
        Returns:
            Diccionario con métricas de entrenamiento
        """
        # Validar estrategia
        if self.label_strategy not in LABEL_STRATEGIES:
            raise ValueError(f"Estrategia desconocida: {self.label_strategy}")
        
        # Cargar datos
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        rates = data.get('rates', data.get('velas', []))
        
        # Convertir formato velas si es necesario (del EA)
        if rates and isinstance(rates[0], dict):
            rates = [[
                int(d['t'].replace('.', '').replace(':', '').replace(' ', '')),  # time
                d['o'],  # open
                d['h'],  # high
                d['l'],  # low
                d['c'],  # close
                0,  # tick_volume (no disponible en EA)
                0,  # spread (no disponible en EA, usar 0)
                0,  # real_volume (no disponible en EA)
            ] for d in rates]
        
        if not rates or len(rates) < 100:
            raise ValueError(f"Datos insuficientes: {len(rates)} velas (mínimo 100)")
        
        print(f"📊 Cargando {len(rates)} velas...")
        print(f"📋 Estrategia de labels: {LABEL_STRATEGIES[self.label_strategy]}")
        
        # Crear features
        print("🔧 Creando features...")
        features_df = self.features_engine.calculate_from_rates(rates)
        
        # Crear labels según estrategia
        print(f"🏷️ Creando labels ({self.label_strategy})...")
        labels = self._create_labels(rates)
        
        # Ajustar tamaños
        min_len = min(len(features_df), len(labels))
        features_df = features_df.iloc[:min_len]
        labels = labels[:min_len]
        
        # Limpiar: eliminar NaN
        mask = ~(features_df.isnull().any(axis=1))
        X = features_df[mask].reset_index(drop=True)
        y = [l for l, m in zip(labels, mask) if m]
        
        if len(X) < 50:
            raise ValueError(f"Datos insuficientes: {len(X)} samples")
        
        # Filtrar solo BUY/SELL (remover NADA para entrenamiento)
        valid_indices = [i for i, label in enumerate(y) if label in ['BUY', 'SELL']]
        if len(valid_indices) < 20:
            raise ValueError(f"Señales insuficientes: {len(valid_indices)}")
        
        X = X.iloc[valid_indices]
        y = [y[i] for i in valid_indices]
        
        print(f"✅ {len(X)} samples para entrenamiento (BUY/SELL)")
        
        self.feature_names = list(features_df.columns)
        
        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, shuffle=True
        )
        
        # Entrenar
        print("🤖 Entrenando RandomForest...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )
        
        self.model.fit(X_train, y_train)
        
        # Métricas
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        train_acc = accuracy_score(y_train, y_pred_train)
        test_acc = accuracy_score(y_test, y_pred_test)
        
        print(f"\n📈 Resultados:")
        print(f"   Train Accuracy: {train_acc:.2%}")
        print(f"   Test Accuracy:  {test_acc:.2%}")
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5)
        print(f"   CV Score: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")
        
        # Classification report
        print("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred_test))
        
        # Feature importance
        print("\n🔍 Top 5 Features:")
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for _, row in importance.head(5).iterrows():
            print(f"   {row['feature']}: {row['importance']:.3f}")
        
        self.is_trained = True
        self.save_model()
        
        return {
            'label_strategy': self.label_strategy,
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'n_samples': len(X),
            'trained_at': datetime.now().isoformat()
        }
    
    def _create_labels(self, rates: List[List]) -> List[str]:
        """Crear labels según la estrategia seleccionada."""
        if self.label_strategy in ('ema_rsi', 'emas'):
            return self._create_labels_ema_rsi(rates)
        elif self.label_strategy == 'price_structure':
            return self._create_labels_price_structure(rates)
        else:
            return ['NADA'] * len(rates)
    
    def _create_labels_ema_rsi(self, rates: List[List]) -> List[str]:
        """
        Labels desde lógica EMA/RSI:
        - BUY: precio > EMA200 Y RSI entre 45-70
        - SELL: precio < EMA200 Y RSI entre 30-55
        - NADA: ninguna
        """
        labels = ['NADA'] * 50  # Primeros no tienen datos suficientes
        
        for i in range(50, len(rates) - 1):
            window = rates[:i+1]
            closes = [r[4] for r in window]
            current_price = closes[-1]
            
            ema50 = self._calculate_ema(closes, 50)
            ema200 = self._calculate_ema(closes, 200)
            rsi = self._calculate_rsi(closes, 14)
            
            # Lógica EMA/RSI
            trend = 'ALCISTA' if current_price > ema200 else 'BAJISTA'
            
            if trend == 'ALCISTA' and 45 <= rsi <= 70:
                labels.append('BUY')
            elif trend == 'BAJISTA' and 30 <= rsi <= 55:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        # Ajustar longitud
        while len(labels) < len(rates):
            labels.append('NADA')
        
        return labels[:len(rates)]
    
    def _create_labels_price_structure(self, rates: List[List]) -> List[str]:
        """
        Labels desde lógica de Price Structure:
        - BUY: precio toca soporte (mínimo local) y rebota
        - SELL: precio toca resistencia (máximo local) y rebota
        - NADA: precio en rango sin tocar SR
        """
        labels = ['NADA'] * 50
        
        for i in range(50, len(rates) - 1):
            window = rates[:i+1]
            closes = [r[4] for r in window]
            highs = [r[2] for r in window]
            lows = [r[3] for r in window]
            current_price = closes[-1]
            
            # Encontrar soporte y resistencia locales (últimas 20 velas)
            lookback = 20
            recent_closes = closes[-lookback:-1]
            recent_highs = highs[-lookback:-1]
            recent_lows = lows[-lookback:-1]
            
            resistance = max(recent_highs)
            support = min(recent_lows)
            
            # Distancia a SR
            dist_to_resistance = resistance - current_price
            dist_to_support = current_price - support
            
            # Calcular ATR para contexto
            atr = self._calculate_atr(window, 14)
            
            # BUY: precio cerca de soporte (< 1 ATR) y rebota
            if dist_to_support < atr and dist_to_support > 0:
                labels.append('BUY')
            # SELL: precio cerca de resistencia (< 1 ATR) y rebota
            elif dist_to_resistance < atr and dist_to_resistance > 0:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        while len(labels) < len(rates):
            labels.append('NADA')
        
        return labels[:len(rates)]
    
    def _calculate_ema(self, prices: list, period: int) -> float:
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        sma = sum(prices[-period:]) / period
        multiplier = 2 / (period + 1)
        ema = sma
        
        for price in reversed(prices[:-period]):
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
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
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, rates: List[List], period: int = 14) -> float:
        """Calcular ATR desde rates."""
        if len(rates) < period + 1:
            return 0.5
        
        trs = []
        for i in range(1, len(rates)):
            high = rates[i][2]
            low = rates[i][3]
            prev_close = rates[i-1][4]
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        return sum(trs[-period:]) / period if trs else 0.5
    
    def save_model(self):
        """Guardar modelo a archivo."""
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'label_strategy': self.label_strategy,
            'trained_at': datetime.now().isoformat()
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"💾 Modelo guardado: {self.model_path}")
    
    def load_model(self, path: Optional[str] = None) -> bool:
        """Cargar modelo desde archivo."""
        model_path = path or self.model_path
        
        if not os.path.exists(model_path):
            print(f"⚠️ Modelo no encontrado: {model_path}")
            return False
        
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data.get('model')
            self.feature_names = model_data.get('feature_names')
            self.label_strategy = model_data.get('label_strategy', 'ema_rsi')
            self.is_trained = True
            
            print(f"✅ Modelo cargado: {model_path}")
            print(f"   Estrategia: {self.label_strategy}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            return False


# Función helper para CLI
def list_strategies():
    """Listar estrategias de labels disponibles."""
    print("\n📋 Estrategias de labels disponibles:")
    for key, desc in LABEL_STRATEGIES.items():
        print(f"   {key}: {desc}")
    print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python trainer.py <json_file> [--strategy ema_rsi|price_structure]")
        list_strategies()
        sys.exit(1)
    
    # Parsear argumentos
    strategy = 'ema_rsi'
    json_path = sys.argv[1]
    
    if '--strategy' in sys.argv:
        idx = sys.argv.index('--strategy')
        if idx + 1 < len(sys.argv):
            strategy = sys.argv[idx + 1]
    
    print(f"🎯 Usando estrategia: {strategy}")
    
    trainer = Trainer(label_strategy=strategy)
    results = trainer.train_from_json(json_path)
    print("\n✅ Entrenamiento completado!")
    print(json.dumps(results, indent=2))