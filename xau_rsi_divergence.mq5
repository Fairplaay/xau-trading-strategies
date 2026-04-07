//+------------------------------------------------------------------+
//| xau_rsi_divergence.mq5 - Trailing SL                           |
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
int OnInit() { Print("xau_rsi_divergence iniciado"); return INIT_SUCCEEDED; }
void OnDeinit(const int reason) { Print("xau_rsi_divergence detenido"); }

//+------------------------------------------------------------------+
void OnTick()
{
   if(PositionSelect(_Symbol)) { ManagePosition(); return; }
   
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period, 0);
   
   // Buscar mínimos y máximos
   double min_price = price, max_price = price;
   double min_rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   double max_rsi = min_rsi;
   
   for(int i = 5; i < Lookback; i++)
   {
      double p = iClose(_Symbol, PERIOD_CURRENT, i);
      double r = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, i);
      if(p < min_price) min_price = p;
      if(r < min_rsi) min_rsi = r;
      if(p > max_price) max_price = p;
      if(r > max_rsi) max_rsi = r;
   }
   
   double rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   
   bool buy = (price < min_price + atr * 0.5) && (rsi > min_rsi + 5);
   bool sell = (price > max_price - atr * 0.5) && (rsi < max_rsi - 5);
   
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
   request.comment = "RSIDiv";
   
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