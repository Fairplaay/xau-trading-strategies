//+------------------------------------------------------------------+
//| xau_emas.mq5 - Estrategia EMAs con trailing SL                 |
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

//--- Trailing SL
input double TrailProfit = 0.75;  // Cuando mover SL
input double TrailLock = 0.50;    // Nuevo SL

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
   // Verificar posición existente
   if(PositionSelect(_Symbol))
   {
      ManagePosition();
      return;
   }
   
   // Solo operar si no hay posición
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ema50 = iMA(_Symbol, PERIOD_CURRENT, EMA50_Period, 0, MODE_EMA, PRICE_CLOSE, 0);
   double ema200 = iMA(_Symbol, PERIOD_CURRENT, EMA200_Period, 0, MODE_EMA, PRICE_CLOSE, 0);
   double rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   double atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period, 0);
   
   bool buy = false;
   bool sell = false;
   
   // BUY: precio > EMA200 + RSI 45-70 + toca EMA50
   if(price > ema200 && rsi >= 45 && rsi <= 70)
      if(MathAbs(price - ema50) <= atr * 0.5)
         buy = true;
   
   // SELL: precio < EMA200 + RSI 30-55 + toca EMA50
   if(price < ema200 && rsi >= 30 && rsi <= 55)
      if(MathAbs(price - ema50) <= atr * 0.5)
         sell = true;
   
   if(buy)
      OpenOrder(ORDER_TYPE_BUY, price, atr);
   else if(sell)
      OpenOrder(ORDER_TYPE_SELL, price, atr);
}

//+------------------------------------------------------------------+
void OpenOrder(ENUM_ORDER_TYPE type, double price, double atr)
{
   double sl = (type == ORDER_TYPE_BUY) ? price - atr * SL_ATR : price + atr * SL_ATR;
   double tp = (type == ORDER_TYPE_BUY) ? price + atr * TP_ATR : price - atr * TP_ATR;
   
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
      Print("Abierto: ", type == ORDER_TYPE_BUY ? "BUY" : "SELL");
}

//+------------------------------------------------------------------+
void ManagePosition()
{
   if(!PositionSelect(_Symbol))
      return;
   
   double entry = PositionOpenPrice();
   double sl = PositionStopLoss();
   double tp = PositionTakeProfit();
   ENUM_POSITION_TYPE type = PositionType();
   
   double current = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) 
                                                 : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   // Trailing SL
   if(type == POSITION_TYPE_BUY)
   {
      if(current > entry + TrailProfit && sl < entry + TrailLock)
      {
         double new_sl = entry + TrailLock;
         ModifySL(new_sl);
      }
   }
   else
   {
      if(current < entry - TrailProfit && (sl == 0 || sl > entry - TrailLock))
      {
         double new_sl = entry - TrailLock;
         ModifySL(new_sl);
      }
   }
}

//+------------------------------------------------------------------+
void ModifySL(double new_sl)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = PositionGetTicket(0);
   request.sl = new_sl;
   request.tp = PositionTakeProfit();
   
   OrderSend(request, result);
}