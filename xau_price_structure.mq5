//+------------------------------------------------------------------+
//| xau_price_structure.mq5 - Trailing SL                          |
//+------------------------------------------------------------------+

#property copyright "Kilito"
#property version   "1.00"
#property strict

input double LotSize = 0.01;
input int    RSI_Period = 14;
input int    Lookback = 20;
input int    ATR_Period = 14;
input double SL_ATR = 0.5;
input double TP_ATR = 1.5;
input double TrailProfit = 0.75;
input double TrailLock = 0.50;

//+------------------------------------------------------------------+
int OnInit() { Print("xau_price_structure iniciado"); return INIT_SUCCEEDED; }
void OnDeinit(const int reason) { Print("xau_price_structure detenido"); }

//+------------------------------------------------------------------+
void OnTick()
{
   if(PositionSelect(_Symbol)) { ManagePosition(); return; }
   
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   double atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period, 0);
   
   double support = price, resistance = price;
   for(int i = 1; i <= Lookback; i++)
   {
      double low = iLow(_Symbol, PERIOD_CURRENT, i);
      double high = iHigh(_Symbol, PERIOD_CURRENT, i);
      if(low < support) support = low;
      if(high > resistance) resistance = high;
   }
   
   bool buy = MathAbs(price - support) <= atr * 0.3 && rsi > 50 && iClose(_Symbol, PERIOD_CURRENT, 1) < price;
   bool sell = MathAbs(price - resistance) <= atr * 0.3 && rsi < 50 && iClose(_Symbol, PERIOD_CURRENT, 1) > price;
   
   if(buy) OpenOrder(ORDER_TYPE_BUY, price, atr);
   else if(sell) OpenOrder(ORDER_TYPE_SELL, price, atr);
}

//+------------------------------------------------------------------+
void OpenOrder(ENUM_ORDER_TYPE type, double price, double atr)
{
   double sl = (type == ORDER_TYPE_BUY) ? price - atr * SL_ATR : price + atr * SL_ATR;
   double tp = (type == ORDER_TYPE_BUY) ? price + atr * TP_ATR : price - atr * TP_ATR;
   
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = LotSize;
   request.type = type;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.deviation = 10;
   request.comment = "PriceStruct";
   
   MqlTradeResult result;
   if(OrderSend(request, result)) Print("Abierto: ", type == ORDER_TYPE_BUY ? "BUY" : "SELL");
}

//+------------------------------------------------------------------+
void ManagePosition()
{
   if(!PositionSelect(_Symbol)) return;
   
   double entry = PositionOpenPrice();
   double sl = PositionStopLoss();
   ENUM_POSITION_TYPE type = PositionType();
   double current = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   if(type == POSITION_TYPE_BUY && current > entry + TrailProfit && sl < entry + TrailLock)
      ModifySL(entry + TrailLock);
   else if(type == POSITION_TYPE_SELL && current < entry - TrailProfit && (sl == 0 || sl > entry - TrailLock))
      ModifySL(entry - TrailLock);
}

//+------------------------------------------------------------------+
void ModifySL(double new_sl)
{
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_SLTP;
   request.position = PositionGetTicket(0);
   request.sl = new_sl;
   request.tp = PositionTakeProfit();
   MqlTradeResult result;
   OrderSend(request, result);
}