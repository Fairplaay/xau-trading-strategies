# -*- coding: utf-8 -*-
"""
Conector de archivo — lee/escribe directamente los JSON del EA.
Sin servidor HTTP, sin FastAPI — solo archivos.
"""

import os
import json
import glob
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta


VET = timezone(timedelta(hours=-4))


class EAConnector:
    """Conector que se comunica con el EA via archivos JSON."""
    
    DATA_FILE = "xau_data.json"
    COMMAND_FILE = "xau_commands.json"
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir
        self.data_file = None
        self.command_file = None
        self.connected = False
        self.account_info = None
        self.last_command_result = ""
    
    def _find_files(self):
        """Buscar los archivos JSON en Wine o directorio actual."""
        home = os.path.expanduser("~")
        
        # Rutas de búsqueda
        search_paths = []
        
        if self.data_dir:
            search_paths.append(os.path.join(self.data_dir, self.DATA_FILE))
            search_paths.append(os.path.join(self.data_dir, self.COMMAND_FILE))
        
        # Wine MT5 paths
        wine_paths = [
            os.path.join(home, ".wine", "drive_c", "users", "**", "AppData", "Roaming", "MetaQuotes", "Terminal", "**", "MQL5", "Files", self.DATA_FILE),
            os.path.join(home, ".wine", "drive_c", "Program Files", "MetaTrader 5", "MQL5", "Files", self.DATA_FILE),
            os.path.join(home, ".wine", "drive_c", "Program Files (x86)", "MetaTrader 5", "MQL5", "Files", self.DATA_FILE),
        ]
        
        for p in wine_paths:
            base = os.path.dirname(p)
            if glob.glob(base.replace(self.DATA_FILE, "*"), recursive=True):
                self.data_dir = base
                break
        
        # Directorio actual del proyecto
        project_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), self.DATA_FILE),
            os.path.join(os.getcwd(), self.DATA_FILE),
            os.path.join(os.path.expanduser("~/Documentos/trading"), self.DATA_FILE),
        ]
        search_paths.extend(project_paths)
        
        for pattern in search_paths:
            if "**" in pattern:
                matches = glob.glob(pattern.replace(self.DATA_FILE, "*"), recursive=True)
                if matches:
                    base = os.path.dirname(matches[0])
                    self.data_file = os.path.join(base, self.DATA_FILE)
                    self.command_file = os.path.join(base, self.COMMAND_FILE)
                    return
            elif os.path.exists(pattern):
                self.data_file = pattern
                base = os.path.dirname(pattern)
                self.command_file = os.path.join(base, self.COMMAND_FILE)
                return
        
        # Buscar en todo el Wine prefix
        wine_root = os.path.join(home, ".wine", "drive_c")
        if os.path.exists(wine_root):
            for root, dirs, files in os.walk(wine_root):
                if self.DATA_FILE in files:
                    self.data_file = os.path.join(root, self.DATA_FILE)
                    self.command_file = os.path.join(root, self.COMMAND_FILE)
                    return
    
    def connect(self, login: int = 0, password: str = "", server: str = "") -> bool:
        """Conectar — verificar que existe el archivo de datos."""
        self._find_files()
        
        if self.data_file and os.path.exists(self.data_file):
            # Leer datos iniciales para obtener info de cuenta
            data = self._read_data()
            self.connected = True
            self.account_info = type('obj', (object,), {
                'login': data.get('account', 'N/A') if data else 'N/A',
                'balance': 0,
                'server': data.get('server', 'N/A') if data else 'N/A'
            })()
            print(f"✅ Conectado al EA: {self.data_file}")
            return True
        
        print(f"⚠️ No se encontró {self.DATA_FILE}")
        print(f"   Asegúrate de tener el EA corriendo en MT5")
        return False
    
    def disconnect(self):
        self.connected = False
        print("🔌 Desconectado del EA")
    
    def _read_data(self) -> Optional[Dict]:
        """Leer archivo de datos del EA."""
        if not self.data_file or not os.path.exists(self.data_file):
            return None
        
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error leyendo datos: {e}")
            return None
    
    def get_tick(self, symbol: str = "XAUUSD") -> Optional[Dict]:
        """Obtener el tick actual."""
        if not self.connected:
            return None
        
        data = self._read_data()
        if not data:
            return None
        
        # Guardar resultado del último comando
        self.last_command_result = data.get("last_command_result", "")
        
        return {
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "time": int(datetime.now().timestamp())
        }
    
    def get_rates(self, symbol: str = "XAUUSD", timeframe: str = "M1", count: int = 100) -> Optional[list]:
        """Obtener velas."""
        if not self.connected:
            return None
        
        data = self._read_data()
        if not data or "velas" not in data:
            return None
        
        velas = data["velas"][-count:]
        rates = []
        for v in velas:
            try:
                dt = datetime.strptime(v["t"], "%Y.%m.%d %H:%M:%S")
                ts = int(dt.timestamp())
            except:
                ts = int(datetime.now().timestamp())
            
            rates.append([ts, v["o"], v["h"], v["l"], v["c"], 0])
        
        return rates
    
    def get_indicators(self) -> Optional[Dict]:
        """Obtener indicadores."""
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
    
    def get_full_data(self) -> Optional[Dict]:
        """Obtener todos los datos del EA."""
        return self._read_data()
    
    def get_last_command_result(self) -> str:
        """Obtener resultado del último comando."""
        return self.last_command_result
    
    def send_command(self, action: str, volume: float = 0.01, 
                     sl: float = 0, tp: float = 0, ticket: int = 0) -> bool:
        """
        Enviar comando al EA.
        
        action: BUY, SELL, CLOSE, MODIFY
        volume: tamaño de la orden
        sl: stop loss
        tp: take profit
        ticket: número de orden para CLOSE/MODIFY
        """
        if not self.connected or not self.command_file:
            return False
        
        command = {
            "action": action.upper(),
            "volume": volume,
            "sl": round(sl, 2) if sl else 0,
            "tp": round(tp, 2) if tp else 0,
            "ticket": ticket,
            "timestamp": datetime.now(VET).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Escribir comando
            with open(self.command_file, "w", encoding="utf-8") as f:
                json.dump(command, f, indent=2)
            
            print(f"✅ Comando enviado: {action} (vol: {volume}, sl: {sl}, tp: {tp})")
            return True
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")
            return False
    
    def buy(self, volume: float, sl: float, tp: float) -> bool:
        """Enviar orden BUY."""
        return self.send_command("BUY", volume, sl, tp)
    
    def sell(self, volume: float, sl: float, tp: float) -> bool:
        """Enviar orden SELL."""
        return self.send_command("SELL", volume, sl, tp)
    
    def close(self, ticket: int) -> bool:
        """Cerrar orden por ticket."""
        return self.send_command("CLOSE", ticket=ticket)
    
    def modify(self, ticket: int, sl: float, tp: float) -> bool:
        """Modificar SL/TP de una orden."""
        return self.send_command("MODIFY", sl=sl, tp=tp, ticket=ticket)
    
    def send_order(self, symbol: str, order_type: str, volume: float = 0.01, 
                   deviation: int = 20, magic: int = 123456, comment: str = "",
                   sl: float = 0, tp: float = 0) -> Optional[Dict]:
        """Interfaz compatible con el resto del código."""
        action = "BUY" if order_type.upper() == "BUY" else "SELL"
        success = self.send_command(action, volume, sl, tp)
        
        return {
            "success": success,
            "order_id": 0,
            "comment": "Command sent to EA"
        }
    
    def get_positions(self) -> list:
        """No disponible — el EA no reporta posiciones."""
        return []
    
    def close_position(self, ticket: int) -> bool:
        """Cerrar posición."""
        return self.close(ticket)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False