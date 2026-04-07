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
        
        self.strategies['emas'] = {
            'name': 'EMAs (Triple Confirmación)',
            'description': 'EMA200 + RSI + EMA50/breaks - Señales más precisas',
            'file': '__builtin__',
            'function': self._create_labels_emas
        }
        
        self.strategies['rsi_divergence'] = {
            'name': 'RSI Divergencia',
            'description': 'Divergencia RSI: precio nuevo minimo pero RSI hace minimo mayor = BUY',
            'file': '__builtin__',
            'function': self._create_labels_rsi_divergence
        }
        
        self.strategies['sin_reglas'] = {
            'name': 'Sin Reglas (Resultado Futuro)',
            'description': 'Label basado en precio futuro: si price[i+5] > price[i] + atr*0.3 = BUY',
            'file': '__builtin__',
            'function': self._create_labels_sin_reglas
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
    
    def _create_labels_emas(self, rates):
        """
        Estrategia EMAs (Más estricto):
        - BUY: precio > EMA200 + RSI 50-60 + toca EMA50 (pullback confirmado)
        - SELL: precio < EMA200 + RSI 40-50 + toca EMA50
        - Solo operar a favor de la tendencia principal
        """
        labels = ['NADA'] * 50
        
        for i in range(50, len(rates) - 1):
            closes = [r[4] for r in rates[:i+1]]
            current = closes[-1]
            
            # Calcular indicadores
            ema50 = self._ema(closes, 50)
            ema200 = self._ema(closes, 200)
            rsi = self._rsi(closes, 14)
            
            # Tendencia principal
            trend_up = current > ema200
            trend_down = current < ema200
            
            # RSI en zona más estricta
            rsi_buy = 55 <= rsi <= 65  # Más estricto
            rsi_sell = 35 <= rsi <= 45  # Más estricto
            
            # Precio toca EMA50 (pullback) - con ATR
            atr = self._atr(rates[:i+1], 14)
            touch_ema50 = abs(current - ema50) < (atr * 0.3)  # Más estricto (era 0.5)
            
            # BUY: tendencia alcista + RSI estricto + toca EMA50
            if trend_up and rsi_buy and touch_ema50:
                labels.append('BUY')
            # SELL: tendencia bajista + RSI estricto + toca EMA50
            elif trend_down and rsi_sell and touch_ema50:
                labels.append('SELL')
            else:
                labels.append('NADA')
        
        while len(labels) < len(rates):
            labels.append('NADA')
        
        return labels[:len(rates)]
    def _create_labels_rsi_divergence(self, rates):
        """
        Estrategia RSI Divergencia:
        - BUY: Precio hace nuevo MÍNIMO pero RSI hace MÍNIMO MAYOR (divergencia positiva)
        - SELL: Precio hace nuevo MÁXIMO pero RSI hace MÁXIMO MENOR (divergencia negativa)
        """
        labels = ['NADA'] * 50
        
        for i in range(50, len(rates) - 1):
            closes = [r[4] for r in rates[:i+1]]
            current = closes[-1]
            
            # Calcular RSI actual y anteriores
            rsi_now = self._rsi(closes, 14)
            
            # Encontrar mínimo/máximo de precio en ventanas anteriores
            lookback = 20
            
            # Mínimo de precio y RSI en ventana anterior (hace 5-20 velas)
            if len(closes) > 25:
                prev_window = closes[-lookback:-5]
                prev_rsi_window = [self._rsi(closes[:j], 14) for j in range(len(closes)-lookback, len(closes)-5)]
                
                price_min_prev = min(prev_window) if prev_window else current
                price_max_prev = max(prev_window) if prev_window else current
                rsi_min_prev = min(prev_rsi_window) if prev_rsi_window else rsi_now
                rsi_max_prev = max(prev_rsi_window) if prev_rsi_window else rsi_now
                
                # Precio actual vs anterior
                current_is_lower = current < price_min_prev
                current_is_higher = current > price_max_prev
                
                # RSI actual vs anterior
                rsi_higher_low = rsi_now > rsi_min_prev
                rsi_lower_high = rsi_now < rsi_max_prev
                
                # BUY: Divergencia positiva (precio baja, RSI sube)
                if current_is_lower and rsi_higher_low:
                    labels.append('BUY')
                # SELL: Divergencia negativa (precio sube, RSI baja)
                elif current_is_higher and rsi_lower_high:
                    labels.append('SELL')
                else:
                    labels.append('NADA')
            else:
                labels.append('NADA')
        
        while len(labels) < len(rates):
            labels.append('NADA')
        return labels[:len(rates)]
    
    def _create_labels_sin_reglas(self, rates):
        """
        Estrategia SIN REGLAS - Label basado en resultado futuro.
        
        BUY: si price[i+5] >= price[i] + ATR*0.3
        SELL: si price[i+5] <= price[i] - ATR*0.3
        NADA: en cualquier otro caso
        
        El ML aprende patrones que predicen movimiento futuro,
        no reglas deterministas.
        """
        labels = ['NADA'] * 50
        lookahead = 5  # 5 minutos para scalping M1
        
        for i in range(50, len(rates) - lookahead - 1):
            closes = [r[4] for r in rates[:i+1]]
            current = closes[-1]
            
            # Calcular ATR para SL/TP
            window = rates[:i+1]
            atr = self._atr(window, 14)
            
            # Scalping M1: SL muy ajustado, TP 3:1
            sl_distance = max(0.10, atr * 0.5)  # SL pequeño
            tp_distance = max(0.30, atr * 1.5)   # TP 3:1
            
            entry = current
            sl_level = entry - sl_distance
            tp_level = entry + tp_distance
            
            # Buscar en las próximas 5 velas
            future_closes = closes[1:lookahead+1]
            
            hit_tp = False
            hit_sl = False
            
            for price in future_closes:
                if price >= tp_level:
                    hit_tp = True
                    break
                if price <= sl_level:
                    hit_sl = True
                    break
            
            # Label profesional: qué se tocó primero
            if hit_tp:
                labels.append('BUY')
            elif hit_sl:
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