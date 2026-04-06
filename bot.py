# -*- coding: utf-8 -*-
"""
Bot principal de trading con IA.
Ejecuta análisis y envía órdenes a MT5.
"""

import argparse
import time
import sys
import signal
from datetime import datetime

# Agregar el directorio del módulo al path
sys.path.insert(0, __file__.rsplit("/", 1)[0])

from config import Config
from news.calendar import NewsCalendar
from ai.openrouter_client import AITradingClient
from strategies import get_strategy, list_strategies
from memory import Memory
from learnings import Learnings

# Importar conector según modo (evitar mt5/__init__.py que puede fallar)
if Config.USE_EA_FILE:
    import sys
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from mt5.ea_connector import EAConnector as MT5Connector
else:
    try:
        from mt5.connector import MT5Connector
    except ImportError:
        from mt5.ea_connector import EAConnector as MT5Connector


class TradingBot:
    """Bot de trading automatizado."""
    
    def __init__(self, strategy_name: str = "EMARSI"):
        self.strategy_name = strategy_name
        self.running = False
        
        # Componentes
        self.config = Config
        self.news = None
        self.ai = None
        self.mt5 = None
        self.strategy = None
        self.memory = None
        self.learnings = None
    
    def initialize(self) -> bool:
        """Inicializa todos los componentes."""
        print("=" * 50)
        print("🤖 AI Trading Bot - XAU/USD")
        print("=" * 50)
        
        # 1. Validar configuración
        if not self.config.validate():
            print("⚠️ Advertencia: OPENROUTER_API_KEY no configurada")
        
        # 2. Cargar calendario de noticias
        print("\n📰 Cargando calendario de noticias...")
        self.news = NewsCalendar(self.config.FOREXFACTORY_URL)
        if not self.news.load():
            print("⚠️ No se pudo cargar calendario, continuando sin filtro...")
        
        # 3. Conectar a IA (Ollama primero, luego OpenRouter)
        print("\n🤖 Conectando a IA...")
        
        # Intentar Ollama primero
        from ai.ollama_client import OllamaClient
        self.ai = OllamaClient()
        if self.ai.connect():
            print(f"✅ IA conectada (Ollama: {self.ai.current_model})")
        else:
            # Fallback a OpenRouter
            print("⚠️ Ollama no disponible, usando OpenRouter...")
            from ai.openrouter_client import AITradingClient
            self.ai = AITradingClient(
                api_key=self.config.OPENROUTER_API_KEY,
                model=self.config.MODEL_NAME,
                temperature=self.config.TEMPERATURE,
                max_tokens=self.config.MAX_TOKENS
            )
            if not self.ai.connect():
                print("⚠️ No se pudo conectar a IA, continuando sin análisis...")
        
        # 4. Cargar estrategia
        print(f"\n📊 Cargando estrategia: {self.strategy_name}")
        self.strategy = get_strategy(self.strategy_name)
        if not self.strategy:
            print(f"❌ Estrategia no encontrada: {self.strategy_name}")
            return False
        print(f"   {self.strategy.description}")
        
        # 5. Conectar a MT5 o EA File
        if self.config.USE_EA_FILE:
            print("\n📁 Conectando al EA via archivos...")
            from mt5.ea_connector import EAConnector
            self.mt5 = EAConnector(data_dir=self.config.EA_FILE_PATH if self.config.EA_FILE_PATH else None)
            if not self.mt5.connect():
                print("❌ No se pudo conectar al archivo del EA")
                return False
        else:
            print("\n🔌 Conectando a MetaTrader 5...")
            self.mt5 = MT5Connector()
            if not self.mt5.connect(
                login=self.config.MT5_ACCOUNT,
                password=self.config.MT5_PASSWORD,
                server=self.config.MT5_SERVER
            ):
                print("❌ No se pudo conectar a MT5")
                return False
        
        print("\n✅ Inicialización completa!")
        
        # 6. Cargar contexto (memory + learnings)
        print("\n🧠 Cargando contexto...")
        self.memory = Memory()
        self.learnings = Learnings()
        
        # Inicializar IA con contexto
        if self.ai and self.ai._connected:
            self.ai.initialize_context(
                memory_context=self.memory.get_context(),
                learnings_context=self.learnings.get_context()
            )
            print(f"   Memory: {len(self.memory)} items")
            print(f"   Learnings: {len(self.learnings)} items")
        
        return True
    
    def cleanup(self):
        """Limpieza al cerrar el bot."""
        print("🔄 Cerrando conexiones...")
        if hasattr(self, 'mt5') and self.mt5:
            self.mt5.disconnect()
        if hasattr(self, 'news'):
            print("   ✓ News calendar cerrado")
        print("   ✓ Limpieza completada")
    
    def get_market_data(self) -> dict:
        """Obtiene datos actuales del mercado."""
        symbol = self.config.SYMBOL
        
        # Obtener tick
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return {}
        
        # Obtener rates para calcular indicadores
        rates = self.mt5.get_rates(symbol, self.config.TIMEFRAME, 200)
        if rates is None or len(rates) < 200:
            return {"price": tick.get("bid")}
        
        # Calcular EMAs y RSI manualmente (simplificado)
        closes = [r[4] for r in rates]  # Close prices
        
        # EMA 50 y 200
        ema50 = self._calculate_ema(closes, 50)
        ema200 = self._calculate_ema(closes, 200)
        
        # RSI 14
        rsi = self._calculate_rsi(closes, 14)
        
        # ATR 14
        atr = self._calculate_atr(rates, 14)
        
        # Determinar tendencia
        trend = "ALCISTA" if tick.get("bid", 0) > ema200 else "BAJISTA"
        
        return {
            "price": tick.get("bid"),
            "ema50": ema50,
            "ema200": ema200,
            "rsi": rsi,
            "atr": atr,
            "trend": trend
        }
    
    def _calculate_ema(self, prices: list, period: int) -> float:
        """Calcula EMA."""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        # SMA inicial
        sma = sum(prices[-period:]) / period
        multiplier = 2 / (period + 1)
        
        # Calcular EMA
        ema = sma
        for price in reversed(prices[:-period]):
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calcula RSI."""
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
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, rates: list, period: int = 14) -> float:
        """Calcula ATR."""
        if len(rates) < period + 1:
            return 0.5
        
        trs = []
        for i in range(1, len(rates)):
            high = rates[i][2]
            low = rates[i][3]
            prev_close = rates[i-1][4]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        
        return sum(trs[-period:]) / period
    
    def check_news_block(self) -> dict:
        """Verifica estado de bloqueo por noticias."""
        if not self.news or not self.news._loaded:
            return {"blocked": False, "level": "NONE"}
        
        status = self.news.get_block_status()
        
        if status["high_impact_blocked"]:
            return {
                "blocked": True,
                "level": "HIGH",
                "reason": f"Noticias de alto impacto: {status['upcoming_high']}"
            }
        
        if status["medium_impact_blocked"]:
            return {
                "blocked": True,
                "level": "MEDIUM",
                "reason": f"Noticias de medio impacto: {status['upcoming_medium']}"
            }
        
        return {"blocked": False, "level": "NONE"}
    
    def run(self):
        """Ejecuta el loop principal del bot."""
        if not self.initialize():
            print("❌ Error en inicialización. Saliendo.")
            return
        
        self.running = True
        print(f"\n🔄 Iniciando loop principal (cada {self.config.CHECK_INTERVAL}s)")
        print("Presiona Ctrl+C para detener\n")
        
        # Guardar referencia al bot para el handler
        bot_instance = self
        
        # Handler para Ctrl+C - definido fuera del loop
        def handle_interrupt(signum, frame):
            print("\n\n🛑 Deteniendo bot...")
            print("   Cerrando conexiones...")
            bot_instance.running = False
            bot_instance.cleanup()
            print("✅ Bot detenido correctamente")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handle_interrupt)
        
        # Loop principal - sincronizado con inicio de vela M1
        # Ejecuta 5 segundos ANTES del inicio de cada minuto (anticipación)
        while self.running:
            try:
                # Calcular tiempo hasta próximo minuto
                now = datetime.now()
                # El próximo minuto empieza en (60 - segundo) segundos
                # Ejecutamos 5 segundos antes: (60 - segundo) - 5 = 55 - segundo
                seconds_to_wait = max(1, 55 - now.second)
                
                # Obtener datos ANTES de que termine el minuto actual
                # Esto nos da la vela que está por cerrar
                
                # 1. Verificar noticias
                news_status = self.check_news_block()
                if news_status["blocked"]:
                    print(f"⏸️ [{datetime.now().strftime('%H:%M:%S')}] Bloqueado por noticias ({news_status['level']}): {news_status.get('reason', '')}")
                    # Calcular espera para próximo ciclo (5 seg antes del minuto)
                    time.sleep(55)
                    continue
                
                # 2. Obtener datos del mercado
                market_data = self.get_market_data()
                if not market_data:
                    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] No se pudo obtener datos")
                    time.sleep(55)
                    continue
                
                # Agregar estado de noticias al market_data
                market_data["news_status"] = f"Sin bloqueo ({news_status['level']})"
                
                # 3. Analizar con estrategia (sin IA, solo reglas)
                trade_signal = self.strategy.analyze(market_data)
                
                if trade_signal:
                    print(f"\n🚨 SEÑAL DETECTADA: {trade_signal.direction}")
                    print(f"   Precio: ${trade_signal.price:.2f}")
                    print(f"   SL: ${trade_signal.sl:.2f} | TP1: ${trade_signal.tp1:.2f}")
                    print(f"   Razón: {trade_signal.reason}")
                    
                    # 4. Si hay IA, confirmar con ella
                    if self.ai and self.ai._connected:
                        print("🤖 Confirmando con IA...")
                        ai_decision = self.ai.analyze(
                            market_data,
                            self.strategy.rules
                        )
                        print(f"   IA decisión: {ai_decision}")
                        
                        # Usar decisión de IA
                        if ai_decision != "NADA":
                            # 5. Enviar orden a MT5
                            result = self.mt5.send_order(
                                symbol=self.config.SYMBOL,
                                order_type=ai_decision,
                                volume=self.config.VOLUME,
                                deviation=self.config.DEVIATION,
                                sl=trade_signal.sl,
                                tp=trade_signal.tp1,
                                comment=f"{self.strategy.name} - {trade_signal.reason}"
                            )
                            if result and result.get("success"):
                                print(f"✅ Orden ejecutada!")
                                # Actualizar memory
                                if self.memory:
                                    self.memory.add_operation(
                                        direction=ai_decision,
                                        symbol=self.config.SYMBOL,
                                        pnl="pendiente"
                                    )
                            else:
                                print(f"❌ Error en orden: {result}")
                        else:
                            print("⏭️ IA rechazó la señal")
                    else:
                        # Sin IA, ejecutar directo (opcional)
                        print("⚠️ Sin IA configurada, señal no ejecutada")
                else:
                    print(f"⏳ [{datetime.now().strftime('%H:%M:%S')}] Sin señal - {market_data.get('trend', 'N/A')} | RSI: {market_data.get('rsi', 0):.1f}")
                
                # Esperar hasta 5 segundos antes del próximo minuto
                time.sleep(55)
                
            except Exception as e:
                print(f"❌ Error en loop: {e}")
                time.sleep(55)
        
        # Cleanup
        print("\n🔌 Cerrando conexiones...")
        if self.mt5:
            self.mt5.disconnect()
        print("👋 Bot detenido")
    
    def stop(self):
        """Detiene el bot."""
        self.running = False


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="AI Trading Bot para XAU/USD")
    parser.add_argument(
        "--strategy",
        type=str,
        default="EMARSI",
        choices=["EMARSI", "STRUCTURE"],
        help="Estrategia a usar"
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="Lista estrategias disponibles"
    )
    
    args = parser.parse_args()
    
    if args.list_strategies:
        print("📊 Estrategias disponibles:")
        for name, desc in list_strategies().items():
            print(f"  - {name}: {desc}")
        return
    
    # Crear y ejecutar bot
    bot = TradingBot(strategy_name=args.strategy)
    bot.run()


if __name__ == "__main__":
    main()