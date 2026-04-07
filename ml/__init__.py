# -*- coding: utf-8 -*-
"""
ML Module - Machine Learning para trading XAU/USD
Basado en scikit-learn RandomForestClassifier

参考: ctx7 docs /websites/scikit-learn_stable "RandomForestClassifier"
"""

from .features import Features
from .trainer import Trainer, LABEL_STRATEGIES
from .predictor import Predictor
from .labels import LabelStrategyManager

__all__ = ['Features', 'Trainer', 'Predictor', 'LabelStrategyManager', 'LABEL_STRATEGIES']