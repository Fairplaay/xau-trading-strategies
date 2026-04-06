# -*- coding: utf-8 -*-
"""
Conector de archivo — lee el JSON directamente del EA.
Sin servidor, sin HTTP, sin dependencias extra.
"""

import os
import json
import glob
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta


VET = timezone(timedelta(hours=-4))


class FileConnector:
    """Conector que lee el archivo JSON del EA directamente."""
    
    EA_FILENAME = "xau_data.json"
    
    def __init__(self, data_dir: str = None):
        # Buscar en Wine o directorio actual
        self.data_file = self._find_data_file(data_dir)
        self.connected = False
        self.account_info = None
    
    def _find_data_file(self, data_dir=None) -> Optional[str]:
        """Buscar el archivo xau_data.json."""
        home = os.path.expanduser("~")
        
        # Rutas de búsqueda
        search_paths = []
        
        if data_dir:
            search_paths.append(os.path.join(data_dir, self.EA_FILENAME))
        
        # Wine MT5 paths
        wine_paths = [
            os.path.join(home, ".wine", "drive_c", "users", "**", "AppData", "Roaming", "MetaQuotes", "Terminal", "**", "MQL5", "Files", self.EA_FILENAME),
            os.path.join(home, ".wine", "drive_c", "Program Files", "MetaTrader 5", "MQL5", "Files", self.EA_FILENAME),
            os.path.join(home, ".wine", "drive_c", "Program Files (x86)", "MetaTrader 5", "MQL5", "Files", self.EA_FILENAME),
        ]
        search_paths.extend(wine_paths)
        
        # Directorio actual del proyecto
        search_paths.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), self.EA_FILENAME))
        search_paths.append(os.path.join(os.getcwd(), self.EA_FILENAME))
        
        for pattern in search_paths:
            if "**" in pattern:
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    return matches[0]
            elif os.path.exists(pattern):
                return pattern
        
        # Buscar en todo el Wine prefix
        wine_root = os.path.join(home, ".wine", "drive_c")
        if os.path.exists(wine_root):
            for root, dirs, files in os.walk(wine_root):
                if self.EA_FILENAME in files:
                    return os.path.join(root, self.EA_FILENAME)
        
        return None
    
    def connect(self, login: int = 0, password: str = "", server: str = "") -> bool:
        """Verifica que el archivo exista."""
        self.data_file = self._find_data_file()
        
        if self.data_file and os.path.exists(self.data_file):
            self.connected = True
            self.account_info = type('obj', (object,), {
                'login': 'EA_File',
                'balance': 0,
                'server': 'File'
            })()
            print(f"✅ Conectado al archivo del EA: {self.data_file}")
            return True
        
        print(f"⚠️ No se encontró {self.EA_FILENAME}")
        print(f"   Asegúrate de tener el EA corriendo en MT5")
        return False
    
    def disconnect(self):
        """No hay conexión real que cerrar."""
        self.connected = False
    
    def get_tick(self, symbol: str = "XAUUSD") -> Optional[Dict]:
        """Obtiene el tick del archivo."""
        if not self.connected:
            return None
        
        data = self._read_data()
        if not data:
            return None
        
        return {
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "time": int(datetime.now().timestamp())
        }
    
    def get_rates(self, symbol: str = "XAUUSD", timeframe: str = "M1", count: int = 100) -> Optional[list]:
        """Obtiene velas del archivo."""
        if not self.connected:
            return None
        
        data = self._read_data()
        if not data or "velas" not in data:
            return None
        
        velas = data["velas"][-count:]
        # Convertir al formato [time, open, high, low, close, tick_volume]
        rates = []
        for v in velas:
            try:
                from datetime import datetime
                dt = datetime.strptime(v["t"], "%Y.%m.%d %H:%M:%S")
                ts = int(dt.timestamp())
            except:
                ts = int(datetime.now().timestamp())
            
            rates.append([ts, v["o"], v["h"], v["l"], v["c"], 0])
        
        return rates
    
    def get_indicators(self) -> Optional[Dict]:
        """Obtiene indicadores del archivo."""
        if not self.connected:
            return None
        
        data = self._read_data()
        if not data:
            return None
        
        return {
            "rsi": data.get("rsi14"),
            "ema50": data.get("ema50"),
            "ema200": data.get("ema200"),
            "atr": data.get("atr14")
        }
    
    def get_signal(self) -> Optional[Dict]:
        """Retorna None — la detección de señales se hace en el bot."""
        return None
    
    def _read_data(self) -> Optional[Dict]:
        """Lee el archivo JSON."""
        if not self.data_file or not os.path.exists(self.data_file):
            return None
        
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error leyendo archivo: {e}")
            return None
    
    def send_order(self, symbol: str, order_type: str, volume: float = 0.01, 
                   deviation: int = 20, magic: int = 123456, comment: str = "") -> Optional[Dict]:
        """No soportado — modo solo lectura."""
        print("⚠️ Envío de órdenes no soportado en modo archivo")
        return None
    
    def get_positions(self) -> list:
        return []
    
    def close_position(self, ticket: int) -> bool:
        return False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False