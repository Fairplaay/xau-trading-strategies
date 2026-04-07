# -*- coding: utf-8 -*-
"""
Backtest Script - Probar el modelo ML con datos históricos

Uso:
    python backtest.py --model modelo_xau.pkl --data xau_data.json
    python backtest.py --model modelo_xau.pkl --data xau_data.json --initial-balance 100
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml.predictor import Predictor
from ml.features import Features


class Backtest:
    """Backtest para el modelo ML."""
    
    def __init__(self, model_path: str, data_path: str, initial_balance: float = 100):
        self.model_path = model_path
        self.data_path = data_path
        self.initial_balance = initial_balance
        self.balance = initial_balance
        
        self.predictor = Predictor(model_path)
        self.features_engine = Features()
        
        # Resultados
        self.trades = []
        self.wins = 0
        self.losses = 0
        
    def load_data(self) -> List:
        """Cargar datos del archivo JSON."""
        with open(self.data_path, 'r') as f:
            data = json.load(f)
        
        rates = data.get('rates', data.get('velas', []))
        
        # Convertir formato si es necesario
        if rates and isinstance(rates[0], dict):
            rates = [[
                0,  # time
                d['o'],
                d['h'],
                d['l'],
                d['c'],
                0,  # volume
                0,  # spread
                0,  # real_volume
            ] for d in rates]
        
        return rates
    
    def run(self) -> Dict:
        """Ejecutar backtest."""
        print("=" * 60)
        print("📊 BACKTEST - ML Trading Bot")
        print("=" * 60)
        
        # Cargar datos
        print("\n📂 Cargando datos...")
        rates = self.load_data()
        print(f"   {len(rates)} velas cargadas")
        
        # Verificar modelo
        if not self.predictor.is_ready():
            print(f"❌ Modelo no encontrado: {self.model_path}")
            return {}
        
        print(f"✅ Modelo cargado: {self.model_path}")
        print(f"💰 Balance inicial: ${self.initial_balance:.2f}")
        print("\n🔄 Ejecutando backtest...\n")
        
        # Simular trading
        position = None  # {"type": "BUY/SELL", "entry": price, "sl": sl, "tp": tp}
        
        for i in range(200, len(rates) - 1):
            # Obtener datos hasta esta vela
            window = rates[:i+1]
            closes = [r[4] for r in window]
            current_price = closes[-1]
            
            # Calcular indicadores
            ema50 = self._ema(closes, 50)
            ema200 = self._ema(closes, 200)
            rsi = self._rsi(closes, 14)
            atr = self._atr(window, 14)
            trend = "ALCISTA" if current_price > ema200 else "BAJISTA"
            
            market_data = {
                "price": current_price,
                "ema50": ema50,
                "ema200": ema200,
                "rsi": rsi,
                "atr": atr,
                "trend": trend
            }
            
            # Predecir
            prediction = self.predictor.predict(market_data, window)
            
            if prediction == "NADA":
                continue
            
            # Si hay posiciónabierta, verificar si cerrar
            if position:
                # Check SL/TP
                if position["type"] == "BUY":
                    if current_price <= position["sl"]:
                        self._close_trade(position, current_price, "SL")
                        position = None
                    elif current_price >= position["tp"]:
                        self._close_trade(position, current_price, "TP")
                        position = None
                else:  # SELL
                    if current_price >= position["sl"]:
                        self._close_trade(position, current_price, "SL")
                        position = None
                    elif current_price <= position["tp"]:
                        self._close_trade(position, current_price, "TP")
                        position = None
            
            # Si no hay posición, abrir nueva
            if not position and prediction != "NADA":
                # Usar mismo SL/TP que el label profesional (3:1 ratio)
                sl_dist = max(0.25, atr * 1.5)
                tp_dist = max(0.75, atr * 4.5)  # 3:1 ratio
                
                if prediction == "BUY":
                    position = {
                        "type": "BUY",
                        "entry": current_price,
                        "sl": current_price - sl_dist,
                        "tp": current_price + tp_dist
                    }
                else:
                    position = {
                        "type": "SELL",
                        "entry": current_price,
                        "sl": current_price + sl_dist,
                        "tp": current_price - tp_dist
                    }
        
        # Cerrar posición final si hay
        if position:
            final_price = rates[-1][4]
            self._close_trade(position, final_price, "END")
        
        return self.get_results()
    
    def _close_trade(self, position: dict, close_price: float, reason: str):
        """Cerrar operación."""
        if position["type"] == "BUY":
            pnl = close_price - position["entry"]
        else:
            pnl = position["entry"] - close_price
        
        self.balance += pnl
        
        trade = {
            "type": position["type"],
            "entry": position["entry"],
            "exit": close_price,
            "pnl": pnl,
            "reason": reason
        }
        
        self.trades.append(trade)
        
        if pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
    
    def get_results(self) -> Dict:
        """Obtener resultados del backtest."""
        total_trades = len(self.trades)
        
        if total_trades == 0:
            print("⚠️ No se ejecutaron operaciones")
            return {}
        
        win_rate = (self.wins / total_trades) * 100
        total_pnl = self.balance - self.initial_balance
        
        # Calcular max drawdown
        peak = self.initial_balance
        max_dd = 0
        equity = self.initial_balance
        
        for trade in self.trades:
            equity += trade["pnl"]
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        results = {
            "total_trades": total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": win_rate,
            "initial_balance": self.initial_balance,
            "final_balance": self.balance,
            "total_pnl": total_pnl,
            "max_drawdown": max_dd,
            "trades": self.trades
        }
        
        # Print results
        print("=" * 60)
        print("📊 RESULTADOS DEL BACKTEST")
        print("=" * 60)
        print(f"📈 Total trades: {total_trades}")
        print(f"✅ Wins: {self.wins}")
        print(f"❌ Losses: {self.losses}")
        print(f"📊 Win rate: {win_rate:.1f}%")
        print(f"💰 Balance inicial: ${self.initial_balance:.2f}")
        print(f"💵 Balance final: ${self.balance:.2f}")
        print(f"📈 PnL total: ${total_pnl:.2f}")
        print(f"📉 Max drawdown: {max_dd:.1f}%")
        
        # Trade log
        print("\n📋 Últimos 10 trades:")
        for trade in self.trades[-10:]:
            print(f"   {trade['type']}: entry={trade['entry']:.2f} exit={trade['exit']:.2f} "
                  f"pnl=${trade['pnl']:.2f} ({trade['reason']})")
        
        return results
    
    def _ema(self, prices: list, period: int) -> float:
        if len(prices) < period:
            return prices[-1] if prices else 0
        sma = sum(prices[-period:]) / period
        mult = 2 / (period + 1)
        ema = sma
        for p in reversed(prices[:-period]):
            ema = (p - ema) * mult + ema
        return ema
    
    def _rsi(self, prices: list, period: int = 14) -> float:
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
    
    def _atr(self, rates: list, period: int = 14) -> float:
        if len(rates) < period + 1:
            return 0.5
        trs = []
        for i in range(1, len(rates)):
            h, l, pc = rates[i][2], rates[i][3], rates[i-1][4]
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        return sum(trs[-period:]) / period if trs else 0.5


def main():
    parser = argparse.ArgumentParser(description="Backtest ML Trading Bot")
    parser.add_argument("--model", default="modelo_xau.pkl", help="Ruta al modelo")
    parser.add_argument("--data", default="xau_data.json", help="Ruta a los datos")
    parser.add_argument("--initial-balance", type=float, default=100, help="Balance inicial")
    
    args = parser.parse_args()
    
    # Buscar archivos
    if not os.path.exists(args.data):
        # Buscar en Wine
        wine_path = os.path.expanduser("~/.wine/drive_c/Program Files/Vantage International MT5/MQL5/Files/xau_data.json")
        if os.path.exists(wine_path):
            args.data = wine_path
        else:
            print(f"❌ Datos no encontrados: {args.data}")
            sys.exit(1)
    
    if not os.path.exists(args.model):
        print(f"❌ Modelo no encontrado: {args.model}")
        sys.exit(1)
    
    # Ejecutar backtest
    bt = Backtest(args.model, args.data, args.initial_balance)
    bt.run()


if __name__ == "__main__":
    main()
