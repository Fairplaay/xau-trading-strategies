# -*- coding: utf-8 -*-
"""
Bot de trading con ML (RandomForest)
Reemplaza estrategia determinista + LLM por modelo sklearn.

Uso:
    python bot.py                    # Usar modelo ML
    python bot.py --train            # Entrenar modelo primero
    python bot.py --model path.pkl   # Usar modelo específico
"""

import argparse
import time
import sys
import signal
import os
from datetime import datetime

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from config import Config
from news.calendar import NewsCalendar
from memory import Memory

# ML imports
from ml.predictor import Predictor
from ml.trainer import Trainer
from ml.features import Features

# Conector EA
if Config.USE_EA_FILE:
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from mt5.ea_connector import EAConnector as MT5Connector
else:
    try:
        from mt5.connector import MT5Connector
    except ImportError:
        from mt5.ea_connector import EAConnector as MT5Connector


class TradingBot:
    """Bot de trading con ML."""
    
    def __init__(self, model_path: str = "modelo_xau.pkl", label_strategy: str = "ema_rsi"):
        self.model_path = model_path
        self.label_strategy = label_strategy
        self.running = False
        
        # Componentes
        self.config = Config
        self.news = None
        self.mt5 = None
        self.predictor = None
        self.features_engine = None
        self.memory = None
        
        # Estado del bot
        self.start_time = None
        self.warmup = 60  # 1 minuto
        self.position_state = "IDLE"  # IDLE = sin posición, OPEN = posición abierta
        self.last_order_time = 0
        self.cooldown = 300  # 5 minutos entre operaciones
        self.daily_pnl = 0
        self.max_daily_loss = 10.0  # $10 max por día
        self.max_daily_profit = 15.0  # $15 objetivo
        self.min_profit = 0.50  # $0.50 profit mínimo para cerrar
    
    def initialize(self, train_mode: bool = False) -> bool:
        """Inicializar componentes."""
        print("=" * 50)
        print("🤖 ML Trading Bot - XAU/USD")
        print("=" * 50)
        
        # 1. News calendar (filtro de noticias)
        print("\n📰 Cargando calendario de noticias...")
        self.news = NewsCalendar(self.config.FOREXFACTORY_URL)
        if not self.news.load():
            print("⚠️ Sin filtro de noticias")
        
        # 2. ML: entrenar o cargar modelo
        if train_mode:
            print("\n🎓 Modo entrenamiento...")
            self._train_model()
        else:
            print("\n🤖 Cargando modelo ML...")
            self.predictor = Predictor(self.model_path)
            if not self.predictor.is_loaded:
                print("⚠️ Modelo no encontrado. Usa --train para crear uno.")
                return False
        
        # 3. Features engine
        self.features_engine = Features()
        
        # 4. Conectar a EA/MT5
        if Config.USE_EA_FILE:
            print("\n📁 Conectando al EA...")
            from mt5.ea_connector import EAConnector
            self.mt5 = EAConnector(data_dir=Config.EA_FILE_PATH)
            if not self.mt5.connect():
                print("❌ No se pudo conectar al EA")
                return False
        else:
            print("\n🔌 Conectando a MT5...")
            self.mt5 = MT5Connector()
            if not self.mt5.connect(
                login=Config.MT5_ACCOUNT,
                password=Config.MT5_PASSWORD,
                server=Config.MT5_SERVER
            ):
                print("❌ No se pudo conectar a MT5")
                return False
        
        # 5. Memory
        self.memory = Memory()
        
        print("\n✅ Inicialización completa!")
        return True
    
    def _train_model(self):
        """Entrenar modelo desde datos del EA."""
        print("\n📂 Buscando datos para entrenamiento...")
        
        # Buscar archivo de datos
        data_paths = [
            "xau_data.json",
            os.path.expanduser("~/Documentos/trading/xau_data.json"),
            os.path.join(Config.EA_FILE_PATH, "xau_data.json") if Config.EA_FILE_PATH else None,
        ]
        data_paths = [p for p in data_paths if p]  # filtrar None
        
        data_path = None
        for path in data_paths:
            if os.path.exists(path):
                data_path = path
                break
        
        if not data_path:
            print("❌ No se encontró xau_data.json")
            print("   Ejecuta el EA en MT5 para generar datos")
            return False
        
        print(f"   Usando: {data_path}")
        
        # Entrenar con la estrategia de labels seleccionada
        from ml.trainer import LABEL_STRATEGIES
        strategy_name = LABEL_STRATEGIES.get(self.label_strategy, self.label_strategy)
        print(f"📋 Estrategia de labels: {strategy_name}")
        
        trainer = Trainer(self.model_path, label_strategy=self.label_strategy)
        try:
            results = trainer.train_from_json(data_path)
            print("\n✅ Modelo entrenado!")
            print(f"   Estrategia: {results['label_strategy']}")
            print(f"   Test Accuracy: {results['test_accuracy']:.2%}")
            print(f"   CV Score: {results['cv_mean']:.2%}")
            
            # Cargar el modelo entrenado
            self.predictor = Predictor(self.model_path)
            
        except Exception as e:
            print(f"❌ Error entrenando: {e}")
            return False
    
    def cleanup(self):
        """Limpieza al cerrar."""
        print("\n🔄 Cerrando...")
        if hasattr(self, 'mt5') and self.mt5:
            self.mt5.disconnect()
        print("✅ Listo")
    
    def get_market_data(self) -> dict:
        """Obtener datos del mercado."""
        symbol = Config.SYMBOL
        
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return {}
        
        rates = self.mt5.get_rates(symbol, Config.TIMEFRAME, 200)
        if rates is None or len(rates) < 200:
            return {"price": tick.get("bid")}
        
        # Calcular indicadores
        closes = [r[4] for r in rates]
        
        ema50 = self._calculate_ema(closes, 50)
        ema200 = self._calculate_ema(closes, 200)
        rsi = self._calculate_rsi(closes, 14)
        atr = self._calculate_atr(rates, 14)
        
        trend = "ALCISTA" if tick.get("bid", 0) > ema200 else "BAJISTA"
        
        return {
            "price": tick.get("bid"),
            "ema50": ema50,
            "ema200": ema200,
            "rsi": rsi,
            "atr": atr,
            "trend": trend,
            "rates": rates
        }
    
    def _calculate_ema(self, prices: list, period: int) -> float:
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        sma = sum(prices[-period:]) / period
        multiplier = 2 / (period + 1)
        ema = sma
        
        for price in reversed(prices[:-period]):
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, rates: list, period: int = 14) -> float:
        if len(rates) < period + 1:
            return 0.5
        
        trs = []
        for i in range(1, len(rates)):
            high = rates[i][2]
            low = rates[i][3]
            prev_close = rates[i-1][4]
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        return sum(trs[-period:]) / period
    
    def check_position(self) -> dict:
        """Verificar si hay posición abierta en MT5."""
        try:
            # Primero intentar con EA (funciona en Linux/Wine)
            positions = self.mt5.get_positions()
            
            if positions and len(positions) > 0:
                for pos in positions:
                    if pos.get("symbol") == Config.SYMBOL:
                        return {
                            "has_position": True,
                            "ticket": pos.get("ticket", 0),
                            "type": pos.get("type", "SELL"),
                            "open_price": pos.get("open_price", 0),
                            "profit": pos.get("profit", 0),
                            "sl": pos.get("sl", 0),
                            "tp": pos.get("tp", 0),
                            "closed": False,
                            "close_reason": None
                        }
            
            return {"has_position": False, "closed": False}
            
        except Exception as e:
            print(f"⚠️ Error verificando posición: {e}")
            return {"has_position": False, "closed": False}
    
    def close_position(self, ticket: int) -> bool:
        """Cerrar posición por ticket."""
        try:
            # Intentar MT5 directo
            try:
                import MetaTrader5 as mt5
                result = mt5.order_close(ticket)
                if result:
                    print(f"✅ Posición {ticket} cerrada")
                    return True
            except ImportError:
                # Fallback: usar EA
                result = self.mt5.close_position(ticket)
                if result:
                    print(f"✅ Posición {ticket} cerrada")
                    return True
            
            return False
        except Exception as e:
            print(f"❌ Error cerrando posición: {e}")
            return False
    
    def check_news_block(self) -> dict:
        """Verificar bloqueo por noticias."""
        if not self.news or not self.news._loaded:
            return {"blocked": False, "level": "NONE"}
        
        status = self.news.get_block_status()
        
        if status.get("high_impact_blocked"):
            return {
                "blocked": True,
                "level": "HIGH",
                "reason": f"Noticias alto impacto: {status.get('upcoming_high')}"
            }
        
        return {"blocked": False, "level": "NONE"}
    
    def calculate_sl_tp(self, direction: str, price: float, atr: float) -> dict:
        """Calcular SL y TP."""
        sl_distance = max(0.25, min(atr * 1.5, 1.0))
        tp_distance = max(0.25, min(atr * 1.0, 2.0))
        
        if direction == "BUY":
            return {"sl": price - sl_distance, "tp": price + tp_distance}
        else:
            return {"sl": price + sl_distance, "tp": price - tp_distance}
    
    def run(self):
        """Loop principal."""
        if not self.initialize():
            print("❌ Error de inicialización")
            return
        
        self.running = True
        print(f"\n🔄 Loop principal (cada {Config.CHECK_INTERVAL}s)")
        print("Presiona Ctrl+C para detener\n")
        
        bot_instance = self
        
        def handle_interrupt(signum, frame):
            print("\n🛑 Deteniendo bot...")
            bot_instance.running = False
            bot_instance.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_interrupt)
        
        # Iniciar timer para warmup
        self.start_time = time.time()
        
        while self.running:
            try:
                # 0. Warmup: esperar 1 minuto antes de operar
                if time.time() - self.start_time < self.warmup:
                    wait_left = int(self.warmup - (time.time() - self.start_time))
                    print(f"⏳ Warmup: {wait_left}s restantes...")
                    time.sleep(10)
                    continue
                
                # 0b. Verificar estado de posición abierta
                position_status = self.check_position()
                if position_status["has_position"]:
                    # Ya hay posiciónabierta
                    print(f"⏸️ [{datetime.now().strftime('%H:%M:%S')}] "
                          f"Posiciónabierta: {position_status['type']} | "
                          f"Profit: ${position_status['profit']:.2f} | "
                          f"SL: {position_status['sl']} | TP: {position_status['tp']}")
                    
                    # Verificar si cerró por SL/TP
                    if position_status["closed"]:
                        print(f"✅ Posicióncerrada: {position_status['close_reason']}")
                        self.position_state = "IDLE"
                        self.last_order_time = time.time()
                    
                    # Verificar profit objetivo
                    elif position_status["profit"] >= self.min_profit:
                        print(f"🎯 Profit objetivo alcanzado, cerrando...")
                        self.close_position(position_status["ticket"])
                        self.position_state = "IDLE"
                        self.last_order_time = time.time()
                    
                    time.sleep(55)
                    continue
                
                # 0c. Verificar cooldown
                if time.time() - self.last_order_time < self.cooldown:
                    wait_left = int(self.cooldown - (time.time() - self.last_order_time))
                    print(f"⏳ Cooldown: {wait_left}s restantes...")
                    time.sleep(55)
                    continue
                
                # 1. Verificar noticias
                news_status = self.check_news_block()
                if news_status["blocked"]:
                    print(f"⏸️ [{datetime.now().strftime('%H:%M:%S')}] "
                          f"Bloqueado por noticias ({news_status['level']})")
                    wait = 55 - datetime.now().second
                    if wait <= 0:
                        wait += 60
                    time.sleep(wait)
                    continue
                
                # 2. Obtener datos
                market_data = self.get_market_data()
                if not market_data:
                    print(f"⚠️ Sin datos del mercado")
                    wait = 55 - datetime.now().second
                    if wait <= 0:
                        wait += 60
                    time.sleep(wait)
                    continue
                
                # 3. Predecir con ML
                rates = market_data.pop("rates", None)
                prediction = self.predictor.predict(market_data, rates)
                
                if prediction == "NADA":
                    print(f"⏳ [{datetime.now().strftime('%H:%M:%S')}] "
                          f"Sin señal - {market_data.get('trend', 'N/A')} | "
                          f"RSI: {market_data.get('rsi', 0):.1f}")
                else:
                    # 4. Ejecutar orden
                    print(f"\n🚨 SEÑAL: {prediction}")
                    print(f"   Precio: ${market_data.get('price', 0):.2f}")
                    
                    # Calcular SL/TP
                    sl_tp = self.calculate_sl_tp(
                        prediction,
                        market_data.get('price', 0),
                        market_data.get('atr', 0.5)
                    )
                    
                    # Enviar orden
                    result = self.mt5.send_order(
                        symbol=Config.SYMBOL,
                        order_type=prediction,
                        volume=Config.VOLUME,
                        deviation=Config.DEVIATION,
                        sl=sl_tp["sl"],
                        tp=sl_tp["tp"],
                        comment=f"ML - {prediction}"
                    )
                    
                    if result and result.get("success"):
                        print(f"✅ Orden ejecutada!")
                        if self.memory:
                            self.memory.add_operation(
                                direction=prediction,
                                symbol=Config.SYMBOL,
                                pnl="pendiente"
                            )
                    else:
                        print(f"❌ Error: {result}")
                
                # Esperar
                wait = 55 - datetime.now().second
                if wait <= 0:
                    wait += 60
                time.sleep(wait)
                
            except Exception as e:
                print(f"❌ Error en loop: {e}")
                time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description="ML Trading Bot")
    parser.add_argument("--train", action="store_true",
                        help="Entrenar modelo antes de iniciar")
    parser.add_argument("--model", default="modelo_xau.pkl",
                        help="Ruta al modelo")
    parser.add_argument("--strategy", default="emas",
                        choices=["emas", "price_structure", "rsi_divergence"],
                        help="Estrategia de labels: emas, price_structure, rsi_divergence")
    parser.add_argument("--no-validate", action="store_true",
                        help="Saltar validación de config")
    
    args = parser.parse_args()
    
    bot = TradingBot(model_path=args.model, label_strategy=args.strategy)
    bot.run()


if __name__ == "__main__":
    main()