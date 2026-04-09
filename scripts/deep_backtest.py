"""
Deep Backtest - Multi-Estrategia para XAU/USD
Prueba múltiples estrategias y genera análisis profundo
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

# Cargar datos
df = pd.read_csv('/root/.openclaw/workspace/MQL5-Trading-Bot/xauusd.csv', sep='\t', encoding='utf-16-le')
# Limpiar nombres de columnas
df.columns = df.columns.str.strip()
df['Time'] = pd.to_datetime(df['Time'], format='%Y.%m.%d %H:%M:%S')
df = df.sort_values('Time').reset_index(drop=True)

print(f"📊 Data loaded: {len(df)} candles ({df['Time'].min()} to {df['Time'].max()})")

# ==================== STRATEGY FUNCTIONS ====================

def estrategia_rsi_ema(df, rsi_period=14, ema_fast=9, ema_slow=21, rsi_oversold=30, rsi_overbought=70):
    """Estrategia RSI + EMA Cross"""
    signals = []
    position = 0
    
    # Calculate indicators
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['EMA_FAST'] = df['Close'].ewm(span=ema_fast).mean()
    df['EMA_SLOW'] = df['Close'].ewm(span=ema_slow).mean()
    
    for i in range(ema_slow, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # Buy: RSI < oversold AND EMA fast crosses above EMA slow
        if position == 0:
            if row['RSI'] < rsi_oversold and prev['EMA_FAST'] <= prev['EMA_SLOW'] and row['EMA_FAST'] > row['EMA_SLOW']:
                signals.append({'time': row['Time'], 'type': 'BUY', 'price': row['Close'], 'rsi': row['RSI']})
                position = 1
                entry_price = row['Close']
        
        # Sell: RSI > overbought AND EMA fast crosses below EMA slow
        elif position == 1:
            if row['RSI'] > rsi_overbought and prev['EMA_FAST'] >= prev['EMA_SLOW'] and row['EMA_FAST'] < row['EMA_SLOW']:
                signals.append({'time': row['Time'], 'type': 'SELL', 'price': row['Close'], 'rsi': row['RSI']})
                position = 0
    
    return signals

def estrategia_macd_atr(df, fast=12, slow=26, signal=9, atr_period=14, atr_multiplier=2):
    """Estrategia MACD + ATR para stops"""
    signals = []
    position = 0
    
    # MACD
    ema_fast = df['Close'].ewm(span=fast).mean()
    ema_slow = df['Close'].ewm(span=slow).mean()
    df['MACD'] = ema_fast - ema_slow
    df['SIGNAL'] = df['MACD'].ewm(span=signal).mean()
    df['HIST'] = df['MACD'] - df['SIGNAL']
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=atr_period).mean()
    
    for i in range(slow, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        if position == 0:
            # Buy: MACD cross above signal
            if prev['HIST'] <= 0 and row['HIST'] > 0:
                signals.append({'time': row['Time'], 'type': 'BUY', 'price': row['Close'], 'macd': row['MACD'], 'atr': row['ATR']})
                position = 1
        
        elif position == 1:
            # Sell: MACD cross below signal
            if prev['HIST'] >= 0 and row['HIST'] < 0:
                signals.append({'time': row['Time'], 'type': 'SELL', 'price': row['Close'], 'macd': row['MACD'], 'atr': row['ATR']})
                position = 0
    
    return signals

def estrategia_bollinger(df, period=20, std_dev=2):
    """Estrategia Bollinger Bands"""
    signals = []
    position = 0
    
    df['BB_MID'] = df['Close'].rolling(window=period).mean()
    df['BB_STD'] = df['Close'].rolling(window=period).std()
    df['BB_UPPER'] = df['BB_MID'] + (std_dev * df['BB_STD'])
    df['BB_LOWER'] = df['BB_MID'] - (std_dev * df['BB_STD'])
    
    for i in range(period, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        if position == 0:
            # Buy en lower band
            if row['Close'] <= row['BB_LOWER']:
                signals.append({'time': row['Time'], 'type': 'BUY', 'price': row['Close'], 'bb_lower': row['BB_LOWER']})
                position = 1
        
        elif position == 1:
            # Sell en middle band o upper band
            if row['Close'] >= row['BB_MID'] or row['Close'] >= row['BB_UPPER']:
                signals.append({'time': row['Time'], 'type': 'SELL', 'price': row['Close'], 'bb_mid': row['BB_MID']})
                position = 0
    
    return signals

def estrategia_breakout_atr(df, atr_period=20, atr_multiplier=1.5):
    """Estrategia Breakout con ATR"""
    signals = []
    position = 0
    
    # ATR
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=atr_period).mean()
    
    # Rolling high/low
    df['ROLL_HIGH'] = df['High'].rolling(window=20).max().shift(1)
    df['ROLL_LOW'] = df['Low'].rolling(window=20).min().shift(1)
    
    for i in range(21, len(df)):
        row = df.iloc[i]
        
        if position == 0:
            # Buy breakout
            if row['Close'] > row['ROLL_HIGH']:
                signals.append({'time': row['Time'], 'type': 'BUY', 'price': row['Close'], 'atr': row['ATR']})
                position = 1
                atr_val = row['ATR']
                entry_price = row['Close']
        
        elif position == 1:
            # Sell en rollback o ATR trail
            if row['Close'] < row['ROLL_LOW'] or row['Close'] < entry_price - (atr_val * atr_multiplier):
                signals.append({'time': row['Time'], 'type': 'SELL', 'price': row['Close']})
                position = 0
    
    return signals

def estrategia_ema_cross_only(df, fast=9, slow=21):
    """Simple EMA Cross"""
    signals = []
    position = 0
    
    df['EMA_FAST'] = df['Close'].ewm(span=fast).mean()
    df['EMA_SLOW'] = df['Close'].ewm(span=slow).mean()
    
    for i in range(slow, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        if position == 0:
            if prev['EMA_FAST'] <= prev['EMA_SLOW'] and row['EMA_FAST'] > row['EMA_SLOW']:
                signals.append({'time': row['Time'], 'type': 'BUY', 'price': row['Close']})
                position = 1
        
        elif position == 1:
            if prev['EMA_FAST'] >= prev['EMA_SLOW'] and row['EMA_FAST'] < row['EMA_SLOW']:
                signals.append({'time': row['Time'], 'type': 'SELL', 'price': row['Close']})
                position = 0
    
    return signals

# ==================== BACKTEST ENGINE ====================

def run_backtest(signals, df, strategy_name, initial_capital=10000, risk_per_trade=0.02):
    """Ejecuta backtest con métricas completas"""
    
    if len(signals) < 2:
        return None
    
    trades = []
    capital = initial_capital
    position = None
    equity_curve = []
    
    for sig in signals:
        if sig['type'] == 'BUY' and position is None:
            position = {'entry': sig['price'], 'time': sig['time']}
        elif sig['type'] == 'SELL' and position is not None:
            pnl = sig['price'] - position['entry']
            pnl_pct = (pnl / position['entry']) * 100
            trades.append({
                'entry_time': position['time'],
                'exit_time': sig['time'],
                'entry_price': position['entry'],
                'exit_price': sig['price'],
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            capital += pnl
            position = None
        
        equity_curve.append({'time': sig['time'], 'capital': capital})
    
    # Métricas
    if not trades:
        return None
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    
    total_trades = len(trades)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    
    avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
    
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # Max Drawdown
    peak = equity_curve[0]['capital']
    max_dd = 0
    for e in equity_curve:
        if e['capital'] > peak:
            peak = e['capital']
        dd = (peak - e['capital']) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    # Sharpe (simplificado)
    returns = [t['pnl_pct'] for t in trades]
    sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
    
    return {
        'strategy': strategy_name,
        'total_trades': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate * 100,
        'total_pnl': capital - initial_capital,
        'total_pnl_pct': ((capital - initial_capital) / initial_capital) * 100,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'trades': trades[:5]  # Prime 5 trades
    }

# ==================== RUN ALL STRATEGIES ====================

print("\n" + "="*60)
print("🔬 DEEP BACKTEST ANALYSIS - XAU/USD")
print("="*60)

results = []

# 1. RSI + EMA
signals_rsi = estrategia_rsi_ema(df.copy())
result_rsi = run_backtest(signals_rsi, df, "RSI + EMA")
if result_rsi:
    results.append(result_rsi)

# 2. MACD + ATR
signals_macd = estrategia_macd_atr(df.copy())
result_macd = run_backtest(signals_macd, df, "MACD + ATR")
if result_macd:
    results.append(result_macd)

# 3. Bollinger
signals_bb = estrategia_bollinger(df.copy())
result_bb = run_backtest(signals_bb, df, "Bollinger Bands")
if result_bb:
    results.append(result_bb)

# 4. Breakout ATR
signals_bo = estrategia_breakout_atr(df.copy())
result_bo = run_backtest(signals_bo, df, "Breakout ATR")
if result_bo:
    results.append(result_bo)

# 5. EMA Cross Simple
signals_ema = estrategia_ema_cross_only(df.copy())
result_ema = run_backtest(signals_ema, df, "EMA Cross 9/21")
if result_ema:
    results.append(result_ema)

# ==================== RESULTS ====================

print("\n📈 RESULTADOS POR ESTRATEGIA:\n")

for r in results:
    print(f"🎯 {r['strategy']}")
    print(f"   Trades: {r['total_trades']} | Win Rate: {r['win_rate']:.1f}%")
    print(f"   PnL: ${r['total_pnl']:.2f} ({r['total_pnl_pct']:.2f}%)")
    print(f"   Profit Factor: {r['profit_factor']:.2f}")
    print(f"   Max Drawdown: {r['max_drawdown']:.2f}%")
    print(f"   Sharpe: {r['sharpe_ratio']:.2f}")
    print()

# Best strategy
best = max(results, key=lambda x: x['total_pnl'])
print("="*60)
print(f"🏆 MEJOR ESTRATEGIA: {best['strategy']}")
print(f"   PnL: ${best['total_pnl']:.2f} | Win Rate: {best['win_rate']:.1f}%")
print(f"   Profit Factor: {best['profit_factor']:.2f}")
print("="*60)

# Guardar resultados
with open('/root/.openclaw/workspace/trading/backtest_results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print("\n✅ Resultados guardados en trading/backtest_results.json")