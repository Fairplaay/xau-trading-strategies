# -*- coding: utf-8 -*-
"""
Configuración del bot de trading.
Carga variables de entorno y provee valores por defecto.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "meta-llama/llama-3.2-3b-instruct:free")
    
    # IA Parameters
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))  # Precisión vs creatividad
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "20"))  # Solo respuesta corta
    REASONING_EFFORT: str = os.getenv("REASONING_EFFORT", "low")  # low/medium/high
    
    # MT5
    SYMBOL: str = os.getenv("SYMBOL", "XAUUSD")
    TIMEFRAME: str = os.getenv("TIMEFRAME", "M1")
    MT5_ACCOUNT: int = int(os.getenv("MT5_ACCOUNT", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    
    # Bot
    CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "60"))  # segundos
    VOLUME: float = float(os.getenv("VOLUME", "0.01"))
    DEVIATION: int = int(os.getenv("DEVIATION", "20"))  # pips
    
    # News Filter
    NEWS_LOOKAHEAD_MINUTES: int = int(os.getenv("NEWS_LOOKAHEAD_MINUTES", "30"))
    HIGH_IMPACT_BUFFER: int = int(os.getenv("HIGH_IMPACT_BUFFER", "30"))  # min antes/después
    MEDIUM_IMPACT_BUFFER: int = int(os.getenv("MEDIUM_IMPACT_BUFFER", "10"))
    
    # News API
    FOREXFACTORY_URL: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    
    # EA File Connector (lee xau_data.json y escribe xau_commands.json)
    USE_EA_FILE: bool = os.getenv("USE_EA_FILE", "false").lower() == "true"
    EA_FILE_PATH: str = os.getenv("EA_FILE_PATH", "")  # opcional
    
    @classmethod
    def validate(cls) -> bool:
        """Valida que las variables obligatorias estén configuradas."""
        if not cls.OPENROUTER_API_KEY:
            print("⚠️ OPENROUTER_API_KEY no configurada")
            return False
        return True