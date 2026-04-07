//+------------------------------------------------------------------+
//| xau_rsi_divergence.mq5 - RSI Divergence                         |
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
   Print("xau_rsi_divergence iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("xau_rsi_divergence detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   if(PositionSelect(_Symbol))
      return;
   
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period, 0);
   
   // Buscar mínimos y máximos en ventana
   double min_price = price;
   double min_rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE, 0);
   double max_price = price;
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
   
   bool buy = false;
   bool sell = false;
   
   // BUY: precio cerca mínimo pero RSI no tan bajo (divergencia +)
   if(price < min_price + atr * 0.5 && rsi > min_rsi + 5)
      buy = true;
   
   // SELL: precio cerca máximo pero RSI no tan alto (divergencia -)
   if(price > max_price - atr * 0.5 && rsi < max_rsi - 5)
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
   request.comment = "RSIDiv";
   
   if(OrderSend(request, result))
      Print("Orden: ", type == ORDER_TYPE_BUY ? "BUY" : "SELL");
}