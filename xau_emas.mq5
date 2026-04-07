//+------------------------------------------------------------------+
//| xau_emas.mq5 - Estrategia EMAs con trailing SL                |
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
input double SL_ATR = 0.5;
input double TP_ATR = 1.5;
input double TrailProfit = 0.75;
input double TrailLock = 0.50;

//--- Handles
int hRSI, hEMA50, hEMA200, hATR;

//--- Buffers
double bufRSI[], bufEMA50[], bufEMA200[], bufATR[];

//+------------------------------------------------------------------+
int OnInit()
{
   hRSI = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   hEMA50 = iMA(_Symbol, PERIOD_CURRENT, EMA50_Period, 0, MODE_EMA, PRICE_CLOSE);
   hEMA200 = iMA(_Symbol, PERIOD_CURRENT, EMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   hATR = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   
   ArraySetAsSeries(bufRSI, true);
   ArraySetAsSeries(bufEMA50, true);
   ArraySetAsSeries(bufEMA200, true);
   ArraySetAsSeries(bufATR, true);
   
   Print("xau_emas iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(hRSI);
   IndicatorRelease(hEMA50);
   IndicatorRelease(hEMA200);
   IndicatorRelease(hATR);
   Print("xau_emas detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   // Verificar posición
   if(PositionSelect(_Symbol))
   {
      ManagePosition();
      return;
   }
   
   // Copiar indicadores
   if(CopyBuffer(hRSI, 0, 0, 1, bufRSI) <= 0) return;
   if(CopyBuffer(hEMA50, 0, 0, 1, bufEMA50) <= 0) return;
   if(CopyBuffer(hEMA200, 0, 0, 1, bufEMA200) <= 0) return;
   if(CopyBuffer(hATR, 0, 0, 1, bufATR) <= 0) return;
   
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ema50 = bufEMA50[0];
   double ema200 = bufEMA200[0];
   double rsi = bufRSI[0];
   double atr = bufATR[0];
   
   // Señales
   bool buy = false, sell = false;
   
   if(price > ema200 && rsi >= 45 && rsi <= 70 && MathAbs(price - ema50) <= atr * 0.5)
      buy = true;
   
   if(price < ema200 && rsi >= 30 && rsi <= 55 && MathAbs(price - ema50) <= atr * 0.5)
      sell = true;
   
   if(buy) OpenOrder(ORDER_TYPE_BUY, price, atr);
   else if(sell) OpenOrder(ORDER_TYPE_SELL, price, atr);
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
   if(!PositionSelect(_Symbol)) return;
   
   double entry = PositionOpenPrice();
   ENUM_POSITION_TYPE type = PositionType();
   double current = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) 
                                                 : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   // Trailing SL
   if(type == POSITION_TYPE_BUY && current > entry + TrailProfit)
   {
      double new_sl = entry + TrailLock;
      if(PositionStopLoss() < new_sl)
         ModifySL(new_sl);
   }
   else if(type == POSITION_TYPE_SELL && current < entry - TrailProfit)
   {
      double new_sl = entry - TrailLock;
      if(PositionStopLoss() == 0 || PositionStopLoss() > new_sl)
         ModifySL(new_sl);
   }
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