# -*- coding: utf-8 -*-
"""
Label Strategies - Sistema de estrategias de labels dinámicos

Permite crear y usar diferentes estrategias de labels para entrenar el modelo.

Uso:
    python -m labels list                    # Listar estrategias
    python -m labels add mi_estrategia.py    # Agregar estrategia
    python -m labels remove nombre           # Eliminar estrategia
"""

import os
import sys
import argparse
import importlib.util
from pathlib import Path

# Directorio de estrategias
LABELS_DIR = Path(__file__).parent / "labels"
LABELS_DIR.mkdir(exist_ok=True)

# Estrategia por defecto
DEFAULT_STRATEGY = """
def create_labels(rates, prices, highs, lows):
    '''
    Estrategia EMA/RSI por defecto.
    '''
    labels = ['NADA'] * 50
    
    for i in range(50, len(rates) - 1):
        closes = [r[4] for r in rates[:i+1]]
        current = closes[-1]
        
        ema50 = _ema(closes, 50)
        ema200 = _ema(closes, 200)
        rsi = _rsi(closes, 14)
        
        trend = 'ALCISTA' if current > ema200 else 'BAJISTA'
        
        if trend == 'ALCISTA' and 45 <= rsi <= 70:
            labels.append('BUY')
        elif trend == 'BAJISTA' and 30 <= rsi <= 55:
            labels.append('SELL')
        else:
            labels.append('NADA')
    
    while len(labels) < len(rates):
        labels.append('NADA')
    
    return labels[:len(rates)]

def _ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    sma = sum(prices[-period:]) / period
    mult = 2 / (period + 1)
    ema = sma
    for p in reversed(prices[:-period]):
        ema = (p - ema) * mult + ema
    return ema

def _rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        c = prices[i] - prices[i-1]
        if c > 0:
            gains.append(c)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(c))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain/avg_loss))
"""


class LabelStrategyManager:
    """Administrador de estrategias de labels."""
    
    def __init__(self):
        self.strategies = {}
        self._load_builtin()
        self._load_custom()
    
    def _load_builtin(self):
        """Cargar estrategias integradas."""
        self.strategies['ema_rsi'] = {
            'name': 'EMA/RSI',
            'description': 'Precio > EMA200 + RSI 45-70 = BUY, precio < EMA200 + RSI 30-55 = SELL',
            'file': '__builtin__',
            'function': self._create_labels_ema_rsi
        }
        
        self.strategies['price_structure'] = {
            'name': 'Price Structure',
            'description': 'Precio toca soporte = BUY, resistencia = SELL',
            'file': '__builtin__',
            'function': self._create_labels_price_structure
        }
    
    def _load_custom(self):
        """Cargar estrategias personalizadas desde archivo."""
        custom_file = LABELS_DIR / "custom_strategies.py"
        if custom_file.exists():
            spec = importlib.util.spec_from_file_location("custom", custom_file)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                if hasattr(module, 'strategies'):
                    for name, strategy in module.strategies.items():
                        self.strategies[name] = {
                            'name': strategy.get('name', name),
                            'description': strategy.get('description', ''),
                            'file': str(custom_file),
                            'function': strategy.get('function')
                        }
            except Exception as e:
                print(f"⚠️ Error cargando estrategias personalizadas: {e}")
    
    def _create_labels_ema_rsi(self, rates):
        """Estrategia EMA/RSI."""
        labels = ['NADA'] * 50
        for i in range(50, len(rates) - 1):
            closes = [r[4] for r in rates[:i+1]]
            current = closes[-1]
            
            ema50 = self._ema(closes, 50)
            ema200 = self._ema(closes, 200)
            rsi = self._rsi(closes, 14)
            
            if current > ema200 and 45 <= rsi <= 70:
                labels.append('BUY')
            elif current < ema200 and 30 <= rsi <= 55:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        while len(labels) < len(rates):
            labels.append('NADA')
        return labels[:len(rates)]
    
    def _create_labels_price_structure(self, rates):
        """Estrategia Price Structure."""
        labels = ['NADA'] * 50
        for i in range(50, len(rates) - 1):
            closes = [r[4] for r in rates[:i+1]]
            highs = [r[2] for r in rates[:i+1]]
            lows = [r[3] for r in rates[:i+1]]
            current = closes[-1]
            
            lookback = 20
            resistance = max(highs[-lookback:-1])
            support = min(lows[-lookback:-1])
            
            atr = self._atr(rates[:i+1], 14)
            
            if current - support < atr and current > support:
                labels.append('BUY')
            elif resistance - current < atr and current < resistance:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        while len(labels) < len(rates):
            labels.append('NADA')
        return labels[:len(rates)]
    
    def _ema(self, prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        sma = sum(prices[-period:]) / period
        mult = 2 / (period + 1)
        ema = sma
        for p in reversed(prices[:-period]):
            ema = (p - ema) * mult + ema
        return ema
    
    def _rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        gains, losses = [], []
        for i in range(1, len(prices)):
            c = prices[i] - prices[i-1]
            gains.append(c if c > 0 else 0)
            losses.append(abs(c) if c < 0 else 0)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        return 100 - (100 / (1 + avg_gain/avg_loss))
    
    def _atr(self, rates, period=14):
        if len(rates) < period + 1:
            return 0.5
        trs = []
        for i in range(1, len(rates)):
            h, l, pc = rates[i][2], rates[i][3], rates[i-1][4]
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        return sum(trs[-period:]) / period if trs else 0.5
    
    def list_strategies(self):
        """Listar todas las estrategias disponibles."""
        print("\n📋 Estrategias de labels disponibles:\n")
        for key, info in self.strategies.items():
            source = "builtin" if info['file'] == '__builtin__' else "custom"
            print(f"  {key}")
            print(f"    Nombre: {info['name']}")
            print(f"    Desc: {info['description']}")
            print(f"    Tipo: {source}")
            print()
    
    def get_strategy(self, name):
        """Obtener función de estrategia por nombre."""
        if name not in self.strategies:
            return None
        return self.strategies[name]['function']
    
    def create_labels(self, name, rates):
        """Crear labels usando una estrategia."""
        func = self.get_strategy(name)
        if func is None:
            raise ValueError(f"Estrategia no encontrada: {name}")
        return func(rates)


def main():
    parser = argparse.ArgumentParser(description="Label Strategies CLI")
    subparsers = parser.add_subparsers(dest='command', help='Comandos')
    
    # Listar estrategias
    subparsers.add_parser('list', help='Listar estrategias disponibles')
    
    # Agregar estrategia
    add_parser = subparsers.add_parser('add', help='Agregar estrategia desde archivo')
    add_parser.add_argument('file', help='Archivo Python con estrategia')
    
    # Remover estrategia
    remove_parser = subparsers.add_parser('remove', help='Eliminar estrategia')
    remove_parser.add_argument('name', help='Nombre de la estrategia')
    
    args = parser.parse_args()
    
    manager = LabelStrategyManager()
    
    if args.command == 'list':
        manager.list_strategies()
    elif args.command == 'add':
        print(f"📂 Agregando estrategia desde: {args.file}")
        print("⚠️ Esta función necesita más implementación")
    elif args.command == 'remove':
        print(f"🗑️ Eliminando: {args.name}")
        print("⚠️ Esta función necesita más implementación")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()