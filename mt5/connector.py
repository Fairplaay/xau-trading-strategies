# -*- coding: utf-8 -*-
"""
Conector MetaTrader5 para Linux.
Usa mt5linux para conectar via Wine/RPyC.
"""

try:
    from mt5linux import MetaTrader5
except ImportError:
    # Fallback para Windows (desarrollo local)
    import MetaTrader5 as _mt5
    MetaTrader5 = _mt5

from typing import Optional, Dict, Any


class MT5Connector:
    """Conector para MetaTrader 5."""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
    
    def connect(self, login: int = 0, password: str = "", server: str = "") -> bool:
        """Conecta a MT5."""
        if not MetaTrader5.initialize():
            print(f"❌ Error inicializando MT5: {MetaTrader5.last_error()}")
            return False
        
        # Si hay login proporcionado, hacer login
        if login > 0 and password and server:
            authorized = MetaTrader5.login(login=login, password=password, server=server)
            if not authorized:
                print(f"❌ Error login MT5: {MetaTrader5.last_error()}")
                MetaTrader5.shutdown()
                return False
        
        self.connected = True
        self.account_info = MetaTrader5.account_info()
        
        print(f"✅ Conectado a MT5")
        print(f"   Cuenta: {self.account_info.login}")
        print(f"   Balance: ${self.account_info.balance}")
        
        return True
    
    def disconnect(self):
        """Desconecta de MT5."""
        if self.connected:
            MetaTrader5.shutdown()
            self.connected = False
            print("🔌 Desconectado de MT5")
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Obtiene información del símbolo."""
        if not self.connected:
            return None
        
        info = MetaTrader5.symbol_info(symbol)
        if info is None:
            return None
        
        return {
            "symbol": info.name,
            "bid": info.bid,
            "ask": info.ask,
            "spread": info.spread,
            "digits": info.digits,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max
        }
    
    def get_tick(self, symbol: str) -> Optional[Dict]:
        """Obtiene el tick actual del símbolo."""
        if not self.connected:
            return None
        
        tick = MetaTrader5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "time": tick.time
        }
    
    def get_rates(self, symbol: str, timeframe: str = "M1", count: int = 100) -> Optional[list]:
        """Obtiene datos OHLC de candles."""
        if not self.connected:
            return None
        
        # Mapear timeframe
        tf_map = {
            "M1": MetaTrader5.TIMEFRAME_M1,
            "M5": MetaTrader5.TIMEFRAME_M5,
            "M15": MetaTrader5.TIMEFRAME_M15,
            "H1": MetaTrader5.TIMEFRAME_H1,
            "H4": MetaTrader5.TIMEFRAME_H4,
            "D1": MetaTrader5.TIMEFRAME_D1
        }
        
        tf = tf_map.get(timeframe, MetaTrader5.TIMEFRAME_M1)
        rates = MetaTrader5.copy_rates_from_pos(symbol, tf, 0, count)
        
        return rates
    
    def send_order(
        self,
        symbol: str,
        order_type: str,
        volume: float = 0.01,
        deviation: int = 20,
        magic: int = 123456,
        comment: str = ""
    ) -> Optional[Dict]:
        """
        Envía una orden a MT5.
        
        Args:
            symbol: Símbolo (ej: "XAUUSD")
            order_type: "BUY" o "SELL"
            volume: Volumen
            deviation: Desviación máxima
            magic: Número mágico
            comment: Comentario
            
        Returns:
            Dict con resultado o None si falla
        """
        if not self.connected:
            return None
        
        # Obtener precio actual
        tick = self.get_tick(symbol)
        if not tick:
            print(f"❌ No se pudo obtener precio para {symbol}")
            return None
        
        # Determinar precio y tipo de orden
        if order_type.upper() == "BUY":
            price = tick["ask"]
            mt5_type = MetaTrader5.ORDER_TYPE_BUY
        else:
            price = tick["bid"]
            mt5_type = MetaTrader5.ORDER_TYPE_SELL
        
        # Preparar request
        request = {
            "action": MetaTrader5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_type,
            "price": price,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": MetaTrader5.ORDER_TIME_GTC,
            "type_filling": MetaTrader5.ORDER_FILLING_IOC
        }
        
        # Enviar orden
        result = MetaTrader5.order_send(request)
        
        if result is None:
            print(f"❌ Error enviando orden: {MetaTrader5.last_error()}")
            return None
        
        if result.retcode != MetaTrader5.TRADE_RETCODE_DONE:
            print(f"❌ Orden fallida: {result.comment}")
            return {
                "success": False,
                "retcode": result.retcode,
                "comment": result.comment
            }
        
        print(f"✅ Orden enviada: {order_type} {symbol} {volume} @ ${price}")
        return {
            "success": True,
            "order_id": result.order,
            "retcode": result.retcode,
            "comment": result.comment
        }
    
    def get_positions(self) -> list:
        """Obtiene posiciones abiertas."""
        if not self.connected:
            return []
        return MetaTrader5.positions_get()
    
    def close_position(self, ticket: int) -> bool:
        """Cierra una posición por ticket."""
        if not self.connected:
            return False
        
        position = MetaTrader5.position_get(ticket=ticket)
        if position is None:
            return False
        
        # Determinar tipo de orden opuesto
        if position.type == MetaTrader5.POSITION_TYPE_BUY:
            order_type = MetaTrader5.ORDER_TYPE_SELL
        else:
            order_type = MetaTrader5.ORDER_TYPE_BUY
        
        request = {
            "action": MetaTrader5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "price": MetaTrader5.symbol_info_tick(position.symbol).bid if order_type == MetaTrader5.ORDER_TYPE_SELL 
                   else MetaTrader5.symbol_info_tick(position.symbol).ask,
            "deviation": 20,
            "magic": position.magic,
            "comment": f"Close #{ticket}",
            "position": ticket
        }
        
        result = MetaTrader5.order_send(request)
        return result.retcode == MetaTrader5.TRADE_RETCODE_DONE
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False