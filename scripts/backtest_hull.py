"""
Backtest: UT BOT + Hull + DEMA + TEMA (hull.txt)
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

# ==================== UT BOT ====================
a = 1  # Sensitivity
c = 10  # ATR Period

df['ATR'] = df['High'].rolling(c).apply(lambda x: max(x) - min(x), raw=True)
nLoss = a * df['ATR']

# ATR Trailing Stop
df['xATRTrailingStop'] = 0.0
for i in range(1, len(df)):
    src = df['Close'].iloc[i]
    prev_stop = df['xATRTrailingStop'].iloc[i-1]
    prev_src = df['Close'].iloc[i-1]
    
    if src > prev_stop and prev_src > prev_stop:
        df.loc[df.index[i], 'xATRTrailingStop'] = max(prev_stop, src - nLoss.iloc[i])
    elif src < prev_stop and prev_src < prev_stop:
        df.loc[df.index[i], 'xATRTrailingStop'] = min(prev_stop, src + nLoss.iloc[i])
    elif src > prev_stop:
        df.loc[df.index[i], 'xATRTrailingStop'] = src - nLoss.iloc[i]
    else:
        df.loc[df.index[i], 'xATRTrailingStop'] = src + nLoss.iloc[i]

# UT Signals
df['ema_ut'] = df['Close']
df['ut_above'] = df['ema_ut'] > df['xATRTrailingStop']
df['ut_below'] = df['ema_ut'] < df['xATRTrailingStop']

df['ut_buy'] = (df['Close'] > df['xATRTrailingStop']) & (df['Close'].shift(1) <= df['xATRTrailingStop'].shift(1))
df['ut_sell'] = (df['Close'] < df['xATRTrailingStop']) & (df['Close'].shift(1) >= df['xATRTrailingStop'].shift(1))

# ==================== HULL ====================
def HMA(src, length):
    return 2 * src.rolling(9).mean() - src.rolling(55).mean()

df['HULL'] = HMA(df['Close'], 55)
df['hull_up'] = df['HULL'] > df['HULL'].shift(2)
df['hull_down'] = df['HULL'] < df['HULL'].shift(2)

# ==================== DEMA ====================
def DEMA(src, length):
    ema1 = src.ewm(span=length).mean()
    ema2 = ema1.ewm(span=length).mean()
    return 2 * ema1 - ema2

df['DEMA'] = DEMA(df['Close'], 21)
df['dema_up'] = df['DEMA'] > df['DEMA'].shift(1)
df['dema_down'] = df['DEMA'] < df['DEMA'].shift(1)

# ==================== TEMA ====================
def TEMA(src, length):
    ema1 = src.ewm(span=length).mean()
    ema2 = ema1.ewm(span=length).mean()
    ema3 = ema2.ewm(span=length).mean()
    return 3 * (ema1 - ema2) + ema3

df['TEMA1'] = TEMA(df['Close'], 21)
df['TEMA2'] = TEMA(df['Close'], 50)
df['tema_cross_up'] = (df['TEMA1'] > df['TEMA2']) & (df['TEMA1'].shift(1) <= df['TEMA2'].shift(1))
df['tema_cross_down'] = (df['TEMA1'] < df['TEMA2']) & (df['TEMA1'].shift(1) >= df['TEMA2'].shift(1))

# ==================== SEÑALES COMBINADAS ====================

# UT + Hull + DEMA
df['buy_combined'] = df['ut_buy'] & df['hull_up'] & df['dema_up']
df['sell_combined'] = df['ut_sell'] & df['hull_down'] & df['dema_down']

# TEMA + UT + Hull (más estricta)
df['tema_buy'] = df['tema_cross_up'] & df['ut_buy'] & df['hull_up']
df['tema_sell'] = df['tema_cross_down'] & df['ut_sell'] & df['hull_down']

# ==================== BACKTEST ====================

def run_bt(signals_buy, signals_sell, name):
    position = 0
    trades = []
    capital = 10000
    
    for i in range(50, len(df)):
        if position == 0 and signals_buy.iloc[i]:
            position = 1
            entry = df['Close'].iloc[i]
            entry_time = df['Time'].iloc[i]
        elif position == 1 and signals_sell.iloc[i]:
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

print("\n" + "="*50)
print("🧪 HULL + UT BOT + DEMA + TEMA BACKTEST")
print("="*50)

# Testear diferentes estrategias
r1 = run_bt(df['ut_buy'], df['ut_sell'], "UT Bot Only")
r2 = run_bt(df['buy_combined'], df['sell_combined'], "UT+Hull+DEMA")
r3 = run_bt(df['tema_buy'], df['tema_sell'], "TEMA+UT+Hull")

results = [r for r in [r1, r2, r3] if r]
for r in results:
    print(f"\n🎯 {r['strategy']}")
    print(f"   Trades: {r['trades']} | Win Rate: {r['win_rate']:.1f}%")
    print(f"   PnL: ${r['pnl']:.2f} | Profit Factor: {r['pf']:.2f}")

best = max(results, key=lambda x: x['pnl'])
print(f"\n🏆 Mejor: {best['strategy']} (${best['pnl']:.2f})")

# Guardar
with open('/root/.openclaw/workspace/trading/hull_backtest.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ Listo!")