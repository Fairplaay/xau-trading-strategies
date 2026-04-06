# 🤖 AI Trading Bot - XAU/USD

Bot de trading automatizado con IA para XAU/USD, integrado con MetaTrader 5 y OpenRouter.

## ⚡️ Requisitos

- Python 3.9+
- MetaTrader 5 (Windows) - debe estar abierto
- Cuenta en [OpenRouter.ai](https://openrouter.ai) (API key gratuita)

## 📦 Instalación

```bash
# Clonar la rama feature/ai-bot
git checkout origin/feature/ai-bot

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

## 🔍 Ver Modelos Disponibles

Para ver qué modelos hay disponibles y filtrar por free/paid:

```bash
# Todos los modelos
python list_models.py

# Solo gratuitos
python list_models.py --free

# Con API key directa
python list_models.py --api-key tu-api-key
```

Esto te mostrará los IDs exactos para poner en `MODEL_NAME`.

## 🚀 Uso

### Modo EA File (recomendado - sin MT5 directo)

El bot se comunica con el EA via archivos JSON:
- **EA → Bot**: Escribe `xau_data.json` (precio, indicadores, velas)
- **Bot → EA**: Escribe `xau_commands.json` (órdenes BUY/SELL/CLOSE)

```bash
# En tu archivo .env:
USE_EA_FILE=true
#EA_FILE_PATH=  # opcional, ruta de los archivos

# Ejecutar el bot
python bot.py --strategy EMARSI
```

### Modo MT5 directo (requiere mt5linux en Linux)</```bash
#MT5_ACCOUNT=12345678
#MT5_PASSWORD=tu_password
#MT5_SERVER=YourServer

python bot.py --strategy EMARSI
```

## 🧠 Modelos (DEFAULT)

El bot viene con este modelo gratuito por defecto:

```bash
MODEL_NAME=meta-llama/llama-3.2-3b-instruct:free
```

Para ver todos los disponibles, ejecuta:
```bash
python list_models.py --free
```

## 📁 Estructura

```
xau-trading-strategies/
├── bot.py                 # Loop principal
├── config.py              # Configuración (ENV)
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
└── mt5/                  # Conector MT5
    └── connector.py
```

## ⚠️ Disclaimer

Este bot es para fines educativos. Siempre verifica las señales antes de operar. El autor no se hace responsable de pérdidas financieras.