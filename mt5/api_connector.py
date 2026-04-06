# -*- coding: utf-8 -*-
"""
Conector API alternativa — FastAPI server del EA.
Usa el servidor xau_data_server.py como fuente de datos.
"""

import requests
from typing import Optional, Dict, Any
import time


class APIConnector:
    """Conector que usa el servidor FastAPI del EA."""
    
    def __init__(self, api_url: str = "http://localhost:5555"):
        self.api_url = api_url
        self.connected = False
        self.account_info = None
    
    def connect(self, login: int = 0, password: str = "", server: str = "") -> bool:
        """Verifica que el servidor API esté disponible."""
        try:
            response = requests.get(f"{self.api_url}/api/xau/status", timeout=5)
            if response.status_code == 200:
                self.connected = True
                # Extraer info de la cuenta del status
                status = response.json()
                self.account_info = type('obj', (object,), {
                    'login': status.get('data_file', 'N/A'),
                    'balance': 0,
                    'server': 'API'
                })()
                print(f"✅ Conectado a XAU Data Server ({self.api_url})")
                return True
        except Exception as e:
            print(f"❌ Error conectando al servidor API: {e}")
        return False
    
    def disconnect(self):
        """No hay conexión real que cerrar."""
        self.connected = False
        print("🔌 Desconectado del servidor API")
    
    def get_tick(self, symbol: str = "XAUUSD") -> Optional[Dict]:
        """Obtiene el tick actual del servidor."""
        if not self.connected:
            return None
        
        try:
            response = requests.get(f"{self.api_url}/api/xau/full", timeout=5)
            if response.status_code == 200:
                data = response.json()
                precio = data.get("precio", {})
                return {
                    "bid": precio.get("bid"),
                    "ask": precio.get("ask"),
                    "time": int(time.time())
                }
        except:
            pass
        return None
    
    def get_rates(self, symbol: str = "XAUUSD", timeframe: str = "M1", count: int = 100) -> Optional[list]:
        """Obtiene velas del servidor API."""
        if not self.connected:
            return None
        
        try:
            response = requests.get(f"{self.api_url}/api/xau/full", timeout=5)
            if response.status_code == 200:
                data = response.json()
                velas = data.get("ultimas_velas_m1", [])
                # Convertir al formato que espera el bot: [time, open, high, low, close, tick_volume]
                rates = []
                for v in velas[-count:]:
                    # Parse time string to timestamp
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(v["time"].replace('Z', '+00:00'))
                        ts = int(dt.timestamp())
                    except:
                        ts = int(time.time())
                    
                    rates.append([
                        ts,
                        v["open"],
                        v["high"],
                        v["low"],
                        v["close"],
                        0  # tick_volume
                    ])
                return rates
        except:
            pass
        return None
    
    def get_indicators(self) -> Optional[Dict]:
        """Obtiene indicadores directamente del servidor."""
        if not self.connected:
            return None
        
        try:
            response = requests.get(f"{self.api_url}/api/xau/full", timeout=5)
            if response.status_code == 200:
                data = response.json()
                indicadores = data.get("indicadores", {})
                return {
                    "rsi": indicadores.get("rsi14"),
                    "ema50": indicadores.get("ema50"),
                    "ema200": indicadores.get("ema200"),
                    "atr": indicadores.get("atr14")
                }
        except:
            pass
        return None
    
    def get_signal(self) -> Optional[Dict]:
        """Obtiene la señal del servidor (si existe)."""
        if not self.connected:
            return None
        
        try:
            response = requests.get(f"{self.api_url}/api/xau/full", timeout=5)
            if response.status_code == 200:
                data = response.json()
                senal = data.get("senal")
                if senal:
                    return senal.dict() if hasattr(senal, 'dict') else senal
        except:
            pass
        return None
    
    def send_order(self, symbol: str, order_type: str, volume: float = 0.01, 
                   deviation: int = 20, magic: int = 123456, comment: str = "") -> Optional[Dict]:
        """No soportado en modo API — el servidor es de solo lectura."""
        print("⚠️ Envío de órdenes no disponible en modo API")
        return None
    
    def get_positions(self) -> list:
        """No soportado en modo API."""
        return []
    
    def close_position(self, ticket: int) -> bool:
        """No soportado en modo API."""
        return False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False