"""
Backtest: Momentum X3 (RSI + ADX + MACD)
"""

import pandas as pd
import numpy as np
import json

# Cargar datos
df = pd.read_csv('/root/.openclaw/workspace/MQL5-Trading-Bot/xauusd.csv', sep='\t', encoding='utf-16-le')
df.columns = df.columns.str.strip()
df['Time'] = pd.to_datetime(df['Time'], format='%Y.%m.%d %H:%M:%S')
df = df.sort_values('Time').reset_index(drop=True)

print(f"📊 Data: {len(df)} candles ({df['Time'].min()} to {df['Time'].max()})")

# ==================== RSI ====================
rsi_period = 14
delta = df['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# ==================== MACD ====================
macd_fast, macd_slow, macd_sig = 12, 26, 9
ema_fast = df['Close'].ewm(span=macd_fast).mean()
ema_slow = df['Close'].ewm(span=macd_slow).mean()
df['MACD'] = ema_fast - ema_slow
df['MACD_signal'] = df['MACD'].ewm(span=macd_sig).mean()
df['MACD_hist'] = df['MACD'] - df['MACD_signal']

# ==================== ADX ====================
adx_len, adx_smooth = 14, 14
high, low, close = df['High'], df['Low'], df['Close']
plus_dm = high.diff()
minus_dm = -low.diff()
plus_dm[plus_dm < 0] = 0
minus_dm[minus_dm < 0] = 0

tr = np.maximum(high - low, np.abs(high - close.shift()))
tr = np.maximum(tr, np.abs(low - close.shift()))

atr = tr.rolling(adx_smooth).mean()
plus_di = 100 * (plus_dm.rolling(adx_len).mean() / atr)
minus_di = 100 * (minus_dm.rolling(adx_len).mean() / atr)
dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
df['ADX'] = dx.rolling(adx_smooth).mean()
df['DI+'] = plus_di
df['DI-'] = minus_di

# ==================== SEÑALES ====================
# BUY: RSI < 35 en últimas 6 velas + MACD hist subiendo + DI+ < DI- + ADX subiendo
rsi_oversold = df['RSI'].rolling(6).min() <= 35
macd_hist_up = (df['MACD_hist'] > df['MACD_hist'].shift(1)) & (df['MACD_hist'].shift(1) > df['MACD_hist'].shift(2))
diplus_weak = df['DI+'] < df['DI-']
adx_rising = df['ADX'] > df['ADX'].shift(3)

df['buy_signal'] = rsi_oversold & macd_hist_up & diplus_weak & adx_rising

# SELL: RSI > 65 en últimas 6 velas + MACD hist bajando + DI- < DI+ + ADX subiendo
rsi_overbought = df['RSI'].rolling(6).max() >= 65
macd_hist_down = (df['MACD_hist'] < df['MACD_hist'].shift(1)) & (df['MACD_hist'].shift(1) < df['MACD_hist'].shift(2))
diminus_weak = df['DI-'] < df['DI+']

df['sell_signal'] = rsi_overbought & macd_hist_down & diminus_weak & adx_rising

# ==================== BACKTEST ====================

def run_bt(buy_col, sell_col, name):
    position = 0
    trades = []
    capital = 10000
    
    for i in range(50, len(df)):
        if position == 0 and buy_col.iloc[i]:
            position = 1
            entry = df['Close'].iloc[i]
        elif position == 1 and sell_col.iloc[i]:
            exit_price = df['Close'].iloc[i]
            pnl = exit_price - entry
            trades.append({'entry': entry, 'exit': exit_price, 'pnl': pnl})
            capital += pnl
            position = 0
    
    if not trades:
        return None
    
    wins = len([t for t in trades if t['pnl'] > 0])
    total = len(trades)
    pnl_total = sum(t['pnl'] for t in trades)
    win_rate = wins / total * 100
    pf = abs(sum(t['pnl'] for t in trades if t['pnl'] > 0) / sum(t['pnl'] for t in trades if t['pnl'] <= 0)) if sum(t['pnl'] for t in trades if t['pnl'] <= 0) != 0 else 0
    
    return {'strategy': name, 'trades': total, 'wins': wins, 'win_rate': win_rate, 'pnl': pnl_total, 'pf': pf}

# Test con parámetros ajustados
rsi_oversold_2 = df['RSI'].rolling(4).min() <= 40
rsi_overbought_2 = df['RSI'].rolling(4).max() >= 60

df['buy_v2'] = rsi_oversold_2 & macd_hist_up & diplus_weak & adx_rising
df['sell_v2'] = rsi_overbought_2 & macd_hist_down & (df['DI-'] < df['DI+']) & adx_rising

print("\n" + "="*50)
print("🧪 MOMENTUM X3 BACKTEST")
print("="*50)

r1 = run_bt(df['buy_signal'], df['sell_signal'], "Momentum X3 (original)")
r2 = run_bt(df['buy_v2'], df['sell_v2'], "Momentum X3 (ajustado)")

results = [r for r in [r1, r2] if r]
for r in results:
    print(f"\n🎯 {r['strategy']}")
    print(f"   Trades: {r['trades']} | Win Rate: {r['win_rate']:.1f}%")
    print(f"   PnL: ${r['pnl']:.2f} | Profit Factor: {r['pf']:.2f}")

if results:
    best = max(results, key=lambda x: x['pnl'])
    print(f"\n🏆 Mejor: {best['strategy']} (${best['pnl']:.2f})")

with open('/root/.openclaw/workspace/trading/momentum_backtest.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ Listo!")