# 🤖 AI Trading Bot - XAU/USD

Bot de trading automatizado con IA para XAU/USD, integrado con MetaTrader 5 y OpenRouter.

## ⚡️ Requisitos

- Python 3.9+
- **Linux:** Wine + mt5linux (ver abajo)
- **Windows:** MetaTrader 5 abierto
- Cuenta en [OpenRouter.ai](https://openrouter.ai) (API key gratuita)

## 📦 Instalación

```bash
# Clonar la rama feature/ai-bot-mt5linux
git checkout origin/feature/ai-bot-mt5linux

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

## 🐧 Linux (mt5linux)

Para correr en Linux, necesitas Wine + mt5linux:

```bash
# 1. Instalar Wine
sudo apt install wine

# 2. Instalar Python for Windows en Wine
# Descarga Python desde python.org/downloads/windows/

# 3. En el Python de Wine:
wine python -m pip install MetaTrader5

# 4. En tu Python Linux:
pip install mt5linux

# 5. Iniciar el servidor mt5linux (en el Python de Wine):
wine python -m mt5linux

# 6. Luego ejecutar el bot
python bot.py --strategy EMARSI
```

**Nota:** MT5 debe estar abierto y el servidor mt5linux debe estar corriendo.

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

### Ver estrategias disponibles:
```bash
python bot.py --list-strategies
```

### Ejecutar con una estrategia:
```bash
# Estrategia EMA/RSI (default)
python bot.py --strategy EMARSI

# Estrategia Structure
python bot.py --strategy STRUCTURE
```

### Con API Server del EA (alternative to MT5 directo):

Si tienes el EA corriendo con el servidor FastAPI:
```bash
# En tu archivo .env:
USE_API_SERVER=true
API_SERVER_URL=http://localhost:5555

# Ejecutar el bot
python bot.py --strategy EMARSI
```

El bot se conectará al servidor del EA en vez de a MT5 directo.

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