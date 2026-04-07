# 🤖 ML Trading Bot - XAU/USD

Bot de trading automatizado con Machine Learning (RandomForest) para XAU/USD.

## 🚀 Quick Start

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar entorno
cp .env.example .env
# Editar .env con tu configuración

# 3. Ejecutar EA en MT5 (xau.mq5) - genera xau_data.json

# 4. Entrenar modelo (necesita datos del EA)
python bot.py --train

# 5. Ejecutar bot
python bot.py
```

## 📋 Requisitos

- Python 3.9+
- MetaTrader 5 con el EA (xau.mq5) corriendo
- **1000+ velas históricas** para entrenar el modelo
- Vantage Demo (o outro broker)

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                         EA MT5                               │
│                   (xau.mq5 en MT5)                          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓ xau_data.json (1000 velas)
┌─────────────────────────────────────────────────────────────┐
│                        bot.py                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   ML        │→ │  Predictor  │→ │  Send Order         │  │
│  │  Features   │  │  (predict)  │  │  (xau_commands.json) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Estructura

```
xau-trading/
├── bot.py              # Bot principal (ML)
├── config.py          # Configuración
├── requirements.txt   # Dependencias
├── xau.mq5           # EA para MT5
├── modelo_xau.pkl    # Modelo ML entrenado (se crea con --train)
├── ml/                # Módulo de Machine Learning
│   ├── __init__.py
│   ├── features.py    # Crear features desde datos
│   ├── trainer.py     # Entrenar modelo
│   └── predictor.py   # Predecir señales
├── mt5/               # Conectores MT5
│   └── ea_connector.py
└── news/              # Filtro de noticias
    └── calendar.py
```

## 📂 Archivos JSON

### xau_data.json (EA → Python)
Generado por el EA cada minuto:
- `bid`, `ask` - precios actuales
- `rsi14`, `ema50`, `ema200`, `atr14` - indicadores
- `velas` - últimas 1000 velas OHLC

### xau_commands.json (Python → EA)
Comandos del bot al EA:
```json
{"action":"BUY","volume":0.01,"sl":3010.50,"tp":3020.00}
{"action":"SELL","volume":0.01,"sl":3020.00,"tp":3010.00}
{"action":"CLOSE","ticket":12345}
```

## 🔧 Configuración (.env)

```env
# Conexión EA (usar archivo)
USE_EA_FILE=true

# símbolo y timeframe
SYMBOL=XAUUSD
TIMEFRAME=M1

# Volumen de trading
VOLUME=0.01
DEVIATION=20

# Intervalo de verificación (segundos)
CHECK_INTERVAL=60
```

## 🎓 Cómo funciona el ML

### 1. Features
Desde los datos del mercado (precio, EMAs, RSI, ATR):
- `rsi` - RSI 14
- `ema50_position` - Precio vs EMA50
- `ema200_position` - Precio vs EMA200
- `atr` - ATR 14
- `trend` - 1=Alcista, 0=Bajista

### 2. Labels (Entrenamiento)
El modelo aprende desde la lógica EMA/RSI:
- **BUY**: precio > EMA200 Y RSI entre 45-70
- **SELL**: precio < EMA200 Y RSI entre 30-55
- **NADA**: ninguna condición cumplida

### 3. Modelo
- **RandomForestClassifier** (100 árboles, max_depth=10)
- sklearn

### 4. Filtro de Noticias
Bloquea operaciones durante noticias de alto impacto (±30 min):
-信息来源: ForexFactory

## 📊 Uso

### Entrenar modelo
```bash
python bot.py --train
```
Necesita `xau_data.json` con 1000+ velas.
Crea `modelo_xau.pkl`.

### Ejecutar bot
```bash
python bot.py
```
Usa el modelo `modelo_xau.pkl` existente.

### Opciones
```bash
python bot.py --train              # Entrenar antes de ejecutar
python bot.py --model mi_modelo.pkl  # Usar modelo específico
```

## 🎯 Flujo completo

1. **MT5**: Ejecutar EA (xau.mq5) → genera xau_data.json
2. **Python**: Leer datos → calcular features → predecir con ML
3. **Python**: Escribir comando en xau_commands.json
4. **MT5**: EA ejecuta la orden en el broker

## ⚠️ Disclaimer

Este bot es para fines educativos. Siempre verifica las señales antes de operar. El autor no se hace responsable de pérdidas financieras.

## 📝 Historial

- **v2.0 (2026-04-07)**: Agregado ML (RandomForest) - remplaza estrategia+LLM
- **v1.0**: Versión original con EMA/RSI + Ollama/OpenRouter