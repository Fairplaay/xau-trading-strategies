# -*- coding: utf-8 -*-
"""
Trainer - Entrenar modelo ML para trading

Usa scikit-learn RandomForestClassifier. Labels se generan desde la lógica
de estrategia EMA/RSI existente, así el ML aprende las decisiones de tu estrategia.

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


class Trainer:
    """Entrena modelo ML para predicción de trading."""
    
    def __init__(self, model_path: str = "modelo_xau.pkl"):
        self.model_path = model_path
        self.model = None
        self.features_engine = Features()
        self.feature_names = None
        self.is_trained = False
    
    def train_from_json(self, json_path: str, test_size: float = 0.2) -> dict:
        """
        Entrenar modelo desde archivo JSON con datos históricos.
        
        Labels se crean usando la lógica de EMA/RSI (tu estrategia).
        
        Args:
            json_path: Ruta al archivo JSON (xau_data.json del EA)
            test_size: Porcentaje de datos para test (0.2 = 20%)
            
        Returns:
            Diccionario con métricas de entrenamiento
        """
        # Cargar datos
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        rates = data.get('rates', [])
        
        if not rates or len(rates) < 100:
            raise ValueError(f"Datos insuficientes: {len(rates)} velas (mínimo 100)")
        
        print(f"📊 Cargando {len(rates)} velas...")
        
        # Crear features
        print("🔧 Creando features...")
        features_df = self.features_engine.calculate_from_rates(rates)
        
        # Crear labels desde estrategia EMA/RSI
        print("🏷️ Creando labels (desde lógica EMA/RSI)...")
        labels = self._create_labels_from_strategy(rates)
        
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
        
        # Filtrar solo BUY/SELL (remover NADA)
        valid_indices = [i for i, label in enumerate(y) if label in ['BUY', 'SELL']]
        if len(valid_indices) < 20:
            raise ValueError(f"señales insuficientes: {len(valid_indices)}")
        
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
            'train_accuracy': train_acc,
            'test_accuracy': test_acc,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'n_samples': len(X),
            'trained_at': datetime.now().isoformat()
        }
    
    def _create_labels_from_strategy(self, rates: List[List]) -> List[str]:
        """
        Crear labels usando la lógica de EMA/RSI.
        
        El ML aprende las decisiones de tu estrategia existente.
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
            
            # BUY: precio > EMA200 Y RSI 45-70
            if trend == 'ALCISTA' and 45 <= rsi <= 70:
                labels.append('BUY')
            # SELL: precio < EMA200 Y RSI 30-55
            elif trend == 'BAJISTA' and 30 <= rsi <= 55:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        # Ajustar longitud
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
    
    def save_model(self):
        """Guardar modelo a archivo."""
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
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
            self.is_trained = True
            
            print(f"✅ Modelo cargado: {model_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python trainer.py <json_file>")
        sys.exit(1)
    
    trainer = Trainer()
    results = trainer.train_from_json(sys.argv[1])
    print("\n✅ Entrenamiento completado!")
    print(json.dumps(results, indent=2))