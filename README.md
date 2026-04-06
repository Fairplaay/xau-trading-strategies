# 🤖 AI Trading Bot - XAU/USD

Bot de trading automatizado con IA para XAU/USD, integrado con MetaTrader 5 y OpenRouter.

## ⚡️ Requisitos

- Python 3.9+
- MetaTrader 5 (Windows) - debe estar abierto
- Cuenta en [OpenRouter.ai](https://openrouter.ai) (API key gratuita)

## 📦 Instalación

```bash
# Clonar y entrar al directorio
cd xau-trading-strategies/ai-bot

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## ⚙️ Configuración

1. Copia el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Edita `.env` y agrega tu API key de OpenRouter:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
```

## 🚀 Uso

### Ver estrategias disponibles:
```bash
python bot.py --list-strategies
```

### Ejecutar con una estrategia:
```bash
# Estrategia EMA/RSI/ATR (default)
python bot.py --strategy EMARSI

# Estrategia Price Structure
python bot.py --strategy STRUCTURE
```

### Con MT5 automático (agrega a .env):
```bash
MT5_ACCOUNT=12345678
MT5_PASSWORD=tu_password
MT5_SERVER=TuBroker-Server
```

## 🧠 Modelos Gratuitos

OpenRouter ofrece modelos gratuitos. El default es:

| Modelo | ID |
|--------|-----|
| Llama 3.2 3B | `meta-llama/llama-3.2-3b-instruct:free` |

Otros modelos gratuitos disponibles:
- `deepseek/deepseek-r1:free`
- `qwen/qwen-2.5-7b-instruct:free`

## 📁 Estructura

```
ai-bot/
├── bot.py                 # Loop principal
├── config.py              # Configuración (ENV)
├── requirements.txt       # Dependencias
├── .env.example          # Template de variables
├── strategies/            # Estrategias de trading
│   ├── base.py           # Clase base
│   ├── ema_rsi_atr.py    # Estrategia A
│   └── price_structure.py # Estrategia B
├── news/                  # Calendario de noticias
│   └── calendar.py       # ForexFactory
├── ai/                   # Cliente IA
│   └── openrouter_client.py
└── mt5/                  # Conector MT5
    └── connector.py
```

## ⚠️ Disclaimer

Este bot es para fines educativos. Sempre verifica las señales antes de operar. El autor no se hace responsable de pérdidas financieras.