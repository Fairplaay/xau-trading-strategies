//+------------------------------------------------------------------+
//| xau_price_structure.mq5 - Price Structure                        |
//+------------------------------------------------------------------+

#property copyright "Kilito"
#property version   "1.00"
#property strict

//--- Inputs
input double LotSize = 0.01;
input int    RSI_Period = 14;
input int    Lookback = 20;
input int    ATR_Period = 14;

//--- SL/TP
input double SL_ATR = 0.5;
input double TP_ATR = 1.5;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("xau_price_structure iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("xau_price_structure detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(PositionSelect(_Symbol))
      return;
   
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   double atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period, 0);
   
   // Soporte y Resistencia
   double support = price;
   double resistance = price;
   
   for(int i = 1; i <= Lookback; i++)
   {
      double low = iLow(_Symbol, PERIOD_CURRENT, i);
      double high = iHigh(_Symbol, PERIOD_CURRENT, i);
      if(low < support) support = low;
      if(high > resistance) resistance = high;
   }
   
   bool buy = false;
   bool sell = false;
   
   // BUY: toca soporte + RSI > 50 + recupera
   if(MathAbs(price - support) <= atr * 0.3 && rsi > 50)
   {
      if(iClose(_Symbol, PERIOD_CURRENT, 1) < price)
         buy = true;
   }
   
   // SELL: toca resistencia + RSI < 50 + baja
   if(MathAbs(price - resistance) <= atr * 0.3 && rsi < 50)
   {
      if(iClose(_Symbol, PERIOD_CURRENT, 1) > price)
         sell = true;
   }
   
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
   request.comment = "PriceStruct";
   
   if(OrderSend(request, result))
      Print("Orden: ", type == ORDER_TYPE_BUY ? "BUY" : "SELL");
}