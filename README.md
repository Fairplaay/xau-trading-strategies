# XAU/USD Scalping Strategies

Colección de estrategias de scalping para XAU/USD desarrolladas para trading automatizado y manual.

## Estructura del Repositorio

```
xau-trading-strategies/
├── docs/
│   ├── estrategia-a-mt5-fastapi.md    # EMA/RSI/ATR strategy
│   └── estrategia-b-tradingview.md     # Price structure strategy
├── prompts/
│   ├── xau-scalping-prompt.md         # Original prompt (A)
│   └── xau-tv-scalping-prompt.md      # TradingView prompt (B)
├── scripts/
│   └── (scripts de trading)
└── README.md
```

## Estrategias Disponibles

### Estrategia A: MT5 + FastAPI (EMA/RSI/ATR)
- **Filosofía:** Indicadores técnicos clásicos
- **Indicadores:** EMA50, EMA200, RSI14, ATR14
- **Timeframe:** M1 (1 minuto)
- **Ventana:** 08:00-16:00 VET

### Estrategia B: TradingView (Estructura de Precio)
- **Filosofía:** Estructura primero, indicadores después
- **Indicadores:** Stoch, CCI, RSI (contexto)
- **Timeframe:** M5 (5 minutos)
- **Gates rígidos:** ATR>8, noticias, 21:00-22:00 UTC = skip

## Licencia

Para uso personal y educativo.