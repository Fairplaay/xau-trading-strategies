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

int hRSI, hATR;
double bufRSI[], bufATR[];

//+------------------------------------------------------------------+
int OnInit()
{
   hRSI = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   hATR = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   ArraySetAsSeries(bufRSI, true);
   ArraySetAsSeries(bufATR, true);
   Print("xau_rsi_divergence iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(hRSI);
   IndicatorRelease(hATR);
   Print("xau_rsi_divergence detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(PositionSelect(_Symbol)) { ManagePosition(); return; }
   
   if(CopyBuffer(hRSI, 0, 0, Lookback + 1, bufRSI) <= 0) return;
   if(CopyBuffer(hATR, 0, 0, 1, bufATR) <= 0) return;
   
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double atr = bufATR[0];
   
   // Buscar min/max
   double min_price = price, max_price = price;
   double min_rsi = bufRSI[0], max_rsi = bufRSI[0];
   
   for(int i = 5; i < Lookback; i++)
   {
      double p = iClose(_Symbol, PERIOD_CURRENT, i);
      double r = bufRSI[i];
      if(p < min_price) min_price = p;
      if(r < min_rsi) min_rsi = r;
      if(p > max_price) max_price = p;
      if(r > max_rsi) max_rsi = r;
   }
   
   double rsi = bufRSI[0];
   
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
   if(OrderSend(request, result)) Print("Abierto");
}

//+------------------------------------------------------------------+
void ManagePosition()
{
   if(!PositionSelect(_Symbol)) return;
   
   double entry = PositionOpenPrice();
   ENUM_POSITION_TYPE type = PositionType();
   double current = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   if(type == POSITION_TYPE_BUY && current > entry + TrailProfit && PositionStopLoss() < entry + TrailLock)
      ModifySL(entry + TrailLock);
   else if(type == POSITION_TYPE_SELL && current < entry - TrailProfit && (PositionStopLoss() == 0 || PositionStopLoss() > entry - TrailLock))
      ModifySL(entry - TrailLock);
}

//+------------------------------------------------------------------+
void ModifySL(double new_sl)
{
   MqlTradeRequest request = {};
   request.action = TRADE_ACTION_SLTP;
   request.position = PositionGetTicket();
   request.sl = new_sl;
   request.tp = PositionTakeProfit();
   MqlTradeResult result;
   OrderSend(request, result);
}