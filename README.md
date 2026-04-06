# 🤖 AI Trading Bot - XAU/USD

Bot de trading automatizado con IA para XAU/USD. Se comunica con el EA de MT5 via archivos JSON (sin necesidad de mt5linux ni servidor HTTP).

## ⚡️ Requisitos

- Python 3.9+
- MetaTrader 5 con el EA `xau.mq5` corriendo
- Cuenta en [OpenRouter.ai](https://openrouter.ai) (API key gratuita)

## 📦 Instalación

```bash
# Clonar la rama bot-mt5-fastapi
git checkout origin/bot-mt5-fastapi

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# O si solo necesitas requests y dotenv:
pip install requests python-dotenv
```

## ⚙️ Configuración

1. Copia el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Edita `.env`:
```bash
# === OBLIGATORIO ===
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx

# === MODO EA FILE (usar este) ===
USE_EA_FILE=true

# === OPCIONALES ===
# VOLUME=0.01
# CHECK_INTERVAL=60
```

## 📋 Flujo de Comunicación

```
┌──────────────┐    xau_data.json     ┌──────────────┐
│  MT5 + EA    │ ◄──────────────────► │    Python    │
│  (xau.mq5)   │    xau_commands.json │   (bot.py)   │
└──────────────┘                     └──────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │  OpenRouter  │
                                       │     (IA)     │
                                       └──────────────┘
```

- **EA → Python**: Escribe `xau_data.json` (precio, RSI, EMA, ATR, velas)
- **Python → EA**: Escribe `xau_commands.json` (BUY, SELL, CLOSE, MODIFY)

## 🚀 Uso

### 1. Compilar el EA en MT5

Abre MetaEditor (F4), abre `xau.mq5` y compila (F7). Luego arrastra el EA al gráfico de XAUUSD M1.

### 2. Ejecutar el bot

```bash
python bot.py --strategy EMARSI
```

El bot:
- Lee `xau_data.json` para obtener datos del mercado
- Analiza con la IA (OpenRouter)
- Decide si comprar, vender, o no hacer nada
- Escribe la orden en `xau_commands.json`
- El EA la ejecuta en MT5

### Ver estrategias disponibles

```bash
python bot.py --list-strategies
```

## 🎯 Comandos Soportados (xau_commands.json)

```json
{
  "action": "BUY",
  "volume": 0.01,
  "sl": 3010.50,
  "tp": 3020.00,
  "timestamp": "2026-04-06 13:00:00"
}
```

```json
{
  "action": "SELL",
  "volume": 0.01,
  "sl": 3020.00,
  "tp": 3010.00,
  "timestamp": "2026-04-06 13:00:00"
}
```

```json
{
  "action": "CLOSE",
  "ticket": 12345
}
```

```json
{
  "action": "MODIFY",
  "ticket": 12345,
  "sl": 3015.00,
  "tp": 3025.00
}
```

## 📁 Estructura

```
xau-trading-strategies/
├── bot.py                 # Loop principal
├── config.py              # Configuración (ENV)
├── xau.mq5               # EA para MT5 (v4)
├── list_models.py         # Listador de modelos
├── requirements.txt       # Dependencias
├── .env.example          # Template de variables
├── strategies/            # Estrategias de trading
│   ├── base.py           # Clase base
│   ├── ema_rsi_atr.py    # EMARSI
│   └── price_structure.py # STRUCTURE
├── news/                  # Calendario de noticias
│   └── calendar.py       # ForexFactory
├── ai/                   # Cliente IA
│   └── openrouter_client.py
└── mt5/                  # Conectores
    ├── connector.py      # MT5 directo
    └── ea_connector.py   # EA via archivos
```

## ⚠️ Disclaimer

Este bot es para fines educativos. Siempre verifica las señales antes de operar. El autor no se hace responsable de pérdidas financieras.