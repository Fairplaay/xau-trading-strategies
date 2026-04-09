"""
Backtest: Super Confluence X (Hull + UT Bot + RSI + MACD + ADX)
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

# ==================== PARÁMETROS ====================
hull_len = 55
ut_sens = 1.0
ut_atr_len = 10
rsi_len = 14
rsi_buy = 40
rsi_sell = 60
macd_fast, macd_slow, macd_sig = 12, 26, 9
adx_len = 14
adx_min = 20

# ==================== HULL SUITE ====================
def f_hma(src, length):
    sqrt_len = int(np.sqrt(length))
    wma1 = src.rolling(9).mean()  # approximation
    wma2 = src.rolling(length).mean()
    return 2 * wma1 - wma2

df['HULL'] = f_hma(df['Close'], hull_len)
df['HULL_FAST'] = df['HULL'].shift(2)
df['hull_trend_up'] = df['HULL'] > df['HULL_FAST']
df['hull_trend_down'] = df['HULL'] < df['HULL_FAST']

# ==================== UT BOT ====================
atr = df['High'].rolling(ut_atr_len).apply(lambda x: max(x) - min(x), raw=True)
nLoss = ut_sens * atr

ut_stop = pd.Series(0.0, index=df.index)
for i in range(1, len(df)):
    prev_stop = ut_stop.iloc[i-1] if i > 0 else df['Close'].iloc[0]
    src = df['Close'].iloc[i]
    prev_src = df['Close'].iloc[i-1]
    nl = nLoss.iloc[i]
    
    if src > prev_stop and prev_src > prev_stop:
        ut_stop.iloc[i] = max(prev_stop, src - nl)
    elif src < prev_stop and prev_src < prev_stop:
        ut_stop.iloc[i] = min(prev_stop, src + nl)
    elif src > prev_stop:
        ut_stop.iloc[i] = src - nl
    else:
        ut_stop.iloc[i] = src + nl

df['ut_stop'] = ut_stop
df['ut_buy'] = (df['Close'] > df['ut_stop']) & (df['Close'].shift(1) <= df['ut_stop'].shift(1))
df['ut_sell'] = (df['Close'] < df['ut_stop']) & (df['Close'].shift(1) >= df['ut_stop'].shift(1))

# ==================== RSI ====================
delta = df['Close'].diff()
gain = delta.where(delta > 0, 0).rolling(window=rsi_len).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_len).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# ==================== MACD ====================
ema_fast = df['Close'].ewm(span=macd_fast).mean()
ema_slow = df['Close'].ewm(span=macd_slow).mean()
df['MACD'] = ema_fast - ema_slow
df['MACD_signal'] = df['MACD'].ewm(span=macd_sig).mean()
df['MACD_hist'] = df['MACD'] - df['MACD_signal']
df['macd_bullish'] = (df['MACD_hist'] > 0) & (df['MACD_hist'] > df['MACD_hist'].shift(1))
df['macd_bearish'] = (df['MACD_hist'] < 0) & (df['MACD_hist'] < df['MACD_hist'].shift(1))

# ==================== ADX ====================
high, low = df['High'], df['Low']
plus_dm = high.diff()
minus_dm = -low.diff()
plus_dm[plus_dm < 0] = 0
minus_dm[minus_dm < 0] = 0

tr = np.maximum(high - low, np.abs(high - df['Close'].shift()))
tr = np.maximum(tr, np.abs(low - df['Close'].shift()))
atr_adx = tr.rolling(14).mean()

plus_di = 100 * (plus_dm.rolling(adx_len).mean() / atr_adx)
minus_di = 100 * (minus_dm.rolling(adx_len).mean() / atr_adx)
dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
df['ADX'] = dx.rolling(14).mean()

df['adx_strong'] = df['ADX'] > adx_min
df['trend_up'] = plus_di > minus_di
df['trend_down'] = minus_di > plus_di

# ==================== SEÑALES CONFLUENCE ====================

# BUY: hull up + UT buy + RSI not overbought + MACD bullish + ADX strong + DI+
buy_conf = (
    (df['hull_trend_up'].astype(int)) +
    (df['ut_buy'].astype(int)) +
    ((df['RSI'] < rsi_sell).astype(int)) +
    (df['macd_bullish'].astype(int)) +
    ((df['adx_strong'] & df['trend_up']).astype(int))
)

df['buy_signal'] = buy_conf >= 3  # Min 3 confluencias

# SELL
sell_conf = (
    (df['hull_trend_down'].astype(int)) +
    (df['ut_sell'].astype(int)) +
    ((df['RSI'] > rsi_buy).astype(int)) +
    (df['macd_bearish'].astype(int)) +
    ((df['adx_strong'] & df['trend_down']).astype(int))
)

df['sell_signal'] = sell_conf >= 3

# ==================== BACKTEST ====================

def run_bt(name):
    position = 0
    trades = []
    capital = 10000
    
    for i in range(50, len(df)):
        if position == 0 and df['buy_signal'].iloc[i]:
            position = 1
            entry = df['Close'].iloc[i]
            conf = buy_conf.iloc[i]
        elif position == 1 and df['sell_signal'].iloc[i]:
            exit_price = df['Close'].iloc[i]
            pnl = exit_price - entry
            trades.append({'entry': entry, 'exit': exit_price, 'pnl': pnl, 'conf': conf})
            capital += pnl
            position = 0
    
    if not trades:
        return {'strategy': name, 'trades': 0, 'wins': 0, 'win_rate': 0, 'pnl': 0, 'pf': 0}
    
    wins = len([t for t in trades if t['pnl'] > 0])
    total = len(trades)
    pnl_total = sum(t['pnl'] for t in trades)
    win_rate = wins / total * 100
    
    wins_pnl = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    losses_pnl = sum(t['pnl'] for t in trades if t['pnl'] <= 0)
    pf = abs(wins_pnl / losses_pnl) if losses_pnl != 0 else 0
    
    return {
        'strategy': name,
        'trades': total,
        'wins': wins,
        'win_rate': round(win_rate, 1),
        'pnl': round(pnl_total, 2),
        'pf': round(pf, 2),
        'trades_detail': trades[:5]
    }

# ==================== EJECUTAR ====================

print("\n" + "="*60)
print("🧪 SUPER CONFLUENCE X BACKTEST")
print("="*60)

# Probar diferentes umbrales de confluencia
results = []
for min_conf in [3, 4]:
    df['buy_sig'] = buy_conf >= min_conf
    df['sell_sig'] = sell_conf >= min_conf
    
    bt = run_bt(f"Confluence {min_conf}/5")
    bt['min_conf'] = min_conf
    results.append(bt)
    
    print(f"\n🎯 Min Confluencias: {min_conf}/5")
    print(f"   Trades: {bt['trades']} | Win Rate: {bt['win_rate']}%")
    print(f"   PnL: ${bt['pnl']:.2f} | Profit Factor: {bt['pf']:.2f}")

# Mejor resultado
best = max(results, key=lambda x: x['pnl'])
print(f"\n🏆 Mejor: Confluence {best['min_conf']}/5 (${best['pnl']:.2f})")

# Guardar
with open('/root/.openclaw/workspace/trading/super_confluence_backtest.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✅ Listo!")