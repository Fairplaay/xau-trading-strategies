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
from mt5.connector import MT5Connector
from strategies import get_strategy, list_strategies
from memory import Memory
from learnings import Learnings


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
        
        # 3. Conectar a OpenRouter (IA)
        print("\n🤖 Conectando a OpenRouter...")
        self.ai = AITradingClient(
            api_key=self.config.OPENROUTER_API_KEY,
            model=self.config.MODEL_NAME,
            temperature=self.config.TEMPERATURE,
            max_tokens=self.config.MAX_TOKENS,
            reasoning_effort=self.config.REASONING_EFFORT
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
        
        # 5. Conectar a MT5
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
        
        # Handler para Ctrl+C
        def signal_handler(sig, frame):
            print("\n🛑 Deteniendo bot...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Loop principal
        while self.running:
            try:
                # 1. Verificar noticias
                news_status = self.check_news_block()
                if news_status["blocked"]:
                    print(f"⏸️ [{datetime.now().strftime('%H:%M:%S')}] Bloqueado por noticias ({news_status['level']}): {news_status.get('reason', '')}")
                    time.sleep(self.config.CHECK_INTERVAL)
                    continue
                
                # 2. Obtener datos del mercado
                market_data = self.get_market_data()
                if not market_data:
                    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] No se pudo obtener datos")
                    time.sleep(self.config.CHECK_INTERVAL)
                    continue
                
                # Agregar estado de noticias al market_data
                market_data["news_status"] = f"Sin bloqueo ({news_status['level']})"
                
                # 3. Analizar con estrategia (sin IA, solo reglas)
                signal = self.strategy.analyze(market_data)
                
                if signal:
                    print(f"\n🚨 SEÑAL DETECTADA: {signal.direction}")
                    print(f"   Precio: ${signal.price:.2f}")
                    print(f"   SL: ${signal.sl:.2f} | TP1: ${signal.tp1:.2f}")
                    print(f"   Razón: {signal.reason}")
                    
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
                                comment=f"{self.strategy.name} - {signal.reason}"
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
                
                time.sleep(self.config.CHECK_INTERVAL)
                
            except Exception as e:
                print(f"❌ Error en loop: {e}")
                time.sleep(self.config.CHECK_INTERVAL)
        
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