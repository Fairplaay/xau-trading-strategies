//+------------------------------------------------------------------+
//| xau_emas.mq5 - Estrategia EMAs simple                            |
//+------------------------------------------------------------------+

#property copyright "Kilito"
#property version   "1.00"
#property strict

//--- Inputs
input double LotSize = 0.01;
input int    RSI_Period = 14;
input int    EMA50_Period = 50;
input int    EMA200_Period = 200;
input int    ATR_Period = 14;

//--- SL/TP
input double SL_ATR = 0.5;
input double TP_ATR = 1.5;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("xau_emas iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("xau_emas detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   // Solo operar si no hay posición abierta
   if(PositionSelect(_Symbol))
      return;
   
   // Obtener datos
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ema50 = iMA(_Symbol, PERIOD_CURRENT, EMA50_Period, 0, MODE_EMA, PRICE_CLOSE, 0);
   double ema200 = iMA(_Symbol, PERIOD_CURRENT, EMA200_Period, 0, MODE_EMA, PRICE_CLOSE, 0);
   double rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   double atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period, 0);
   
   // Señales
   bool buy = false;
   bool sell = false;
   
   // BUY: precio > EMA200 + RSI 45-70 + toca EMA50
   if(price > ema200 && rsi >= 45 && rsi <= 70)
   {
      if(MathAbs(price - ema50) <= atr * 0.5)
         buy = true;
   }
   
   // SELL: precio < EMA200 + RSI 30-55 + toca EMA50  
   if(price < ema200 && rsi >= 30 && rsi <= 55)
   {
      if(MathAbs(price - ema50) <= atr * 0.5)
         sell = true;
   }
   
   // Ejecutar
   if(buy)
      OpenOrder(ORDER_TYPE_BUY, price, atr);
   else if(sell)
      OpenOrder(ORDER_TYPE_SELL, price, atr);
}

//+------------------------------------------------------------------+
void OpenOrder(ENUM_ORDER_TYPE type, double price, double atr)
{
   double sl, tp;
   
   if(type == ORDER_TYPE_BUY)
   {
      sl = price - (atr * SL_ATR);
      tp = price + (atr * TP_ATR);
   }
   else
   {
      sl = price + (atr * SL_ATR);
      tp = price - (atr * TP_ATR);
   }
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = LotSize;
   request.type = type;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.deviation = 10;
   request.comment = "EMAs";
   
   if(OrderSend(request, result))
      Print("Orden abierta: ", type == ORDER_TYPE_BUY ? "BUY" : "SELL");
}