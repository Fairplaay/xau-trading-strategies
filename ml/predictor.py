# -*- coding: utf-8 -*-
"""
Predictor - Predicción en vivo usando modelo ML

Carga el modelo entrenado y predice señales de trading.
"""

import os
import pickle
import numpy as np
from typing import Dict, Any, List, Optional

from .features import Features


class Predictor:
    """Predice señales de trading usando modelo ML."""
    
    def __init__(self, model_path: str = "modelo_xau.pkl"):
        self.model_path = model_path
        self.model = None
        self.feature_names = None
        self.features_engine = Features()
        self.is_loaded = False
        
        # Cargar automáticamente si existe
        if os.path.exists(model_path):
            self.load_model()
    
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
            self.feature_names = model_data.get('feature_names', [])
            
            if self.model is None:
                print(f"❌ Modelo corrupto en: {model_path}")
                return False
            
            self.is_loaded = True
            print(f"✅ Modelo ML cargado: {model_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            return False
    
    def predict(self, market_data: Dict[str, Any], rates: Optional[List] = None) -> str:
        """
        Predecir señal de trading.
        
        Args:
            market_data: Diccionario con price, ema50, ema200, rsi, atr, trend
            rates: Lista de rates para calcular features adicionales (opcional)
            
        Returns:
            'BUY', 'SELL', o 'NADA'
        """
        if not self.is_loaded or self.model is None:
            print("⚠️ Modelo no cargado, retornando NADA")
            return "NADA"
        
        try:
            # Calcular features
            features = self.features_engine.calculate_from_market_data(market_data, rates)
            
            # Verificar que tenemos todos los features
            if self.feature_names and len(features) != len(self.feature_names):
                print(f"⚠️ Feature mismatch: {len(features)} vs {len(self.feature_names)}")
                # Ajustar si es necesario
                while len(features) < len(self.feature_names):
                    features.append(0)
                features = features[:len(self.feature_names)]
            
            # Convertir a array 2D para sklearn
            X = np.array([features])
            
            # Predecir
            prediction = self.model.predict(X)[0]
            
            # Obtener probabilidades si está disponible
            proba = None
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[0]
                classes = self.model.classes_
                
                # Mostrar probabilidades
                print(f"   Probabilidades: ", end="")
                for cls, pr in zip(classes, proba):
                    print(f"{cls}={pr:.1%} ", end="")
                print()
            
            return prediction
            
        except Exception as e:
            print(f"❌ Error en predicción: {e}")
            return "NADA"
    
    def predict_with_confidence(self, market_data: Dict[str, Any], rates: Optional[List] = None) -> Dict[str, Any]:
        """
        Predecir con información de confianza.
        
        Returns:
            Diccionario con signal, confidence, probabilities
        """
        if not self.is_loaded or self.model is None:
            return {
                'signal': 'NADA',
                'confidence': 0,
                'probabilities': {}
            }
        
        try:
            features = self.features_engine.calculate_from_market_data(market_data, rates)
            
            if self.feature_names and len(features) != len(self.feature_names):
                while len(features) < len(self.feature_names):
                    features.append(0)
                features = features[:len(self.feature_names)]
            
            X = np.array([features])
            
            # Predicción
            prediction = self.model.predict(X)[0]
            
            # Probabilidades
            result = {
                'signal': prediction,
                'confidence': 0,
                'probabilities': {}
            }
            
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[0]
                classes = self.model.classes_
                
                result['probabilities'] = {cls: float(pr) for cls, pr in zip(classes, proba)}
                
                # Confidence = max probability
                result['confidence'] = float(max(proba))
            
            return result
            
        except Exception as e:
            print(f"❌ Error en predicción: {e}")
            return {
                'signal': 'NADA',
                'confidence': 0,
                'probabilities': {}
            }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Obtener importancia de features del modelo."""
        if not self.is_loaded or self.model is None or not self.feature_names:
            return {}
        
        importance = self.model.feature_importances_
        return {name: float(imp) for name, imp in zip(self.feature_names, importance)}
    
    def is_ready(self) -> bool:
        """Verificar si el modelo está listo."""
        return self.is_loaded and self.model is not None


# Función de ayuda para CLI
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Uso: python predictor.py <model_path> [market_data_json]")
        sys.exit(1)
    
    predictor = Predictor(sys.argv[1])
    
    if not predictor.is_ready():
        print("❌ Modelo no disponible")
        sys.exit(1)
    
    # Si hay segundo argumento, usar esos datos
    if len(sys.argv) >= 3:
        with open(sys.argv[2]) as f:
            market_data = json.load(f)
    else:
        # Datos de ejemplo
        market_data = {
            'price': 3010.0,
            'ema50': 3008.0,
            'ema200': 3005.0,
            'rsi': 55,
            'atr': 0.8,
            'trend': 'ALCISTA'
        }
    
    result = predictor.predict_with_confidence(market_data)
    print(json.dumps(result, indent=2))