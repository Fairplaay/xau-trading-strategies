//+------------------------------------------------------------------+
//| xau_price_structure.mq5 - Estrategia Price Structure           |
//| BUY: precio toca soporte + RSI > 50                              |
//| SELL: precio toca resistencia + RSI < 50                         |
//+------------------------------------------------------------------+

#property copyright "Kilito"
#property version   "1.00"
#property strict

//--- Inputs
input string InpSignalFile = "xau_signals.json";
input double LotSize = 0.01;
input int    RSI_Period = 14;
input int    Lookback = 20;
input int    ATR_Period = 14;
input int    MagicNumber = 123457;

//--- SL/TP
input double SL_ATR_Multiplier = 0.5;
input double TP_ATR_Multiplier = 1.5;

//--- Handles
int handle_rsi = INVALID_HANDLE;
int handle_atr = INVALID_HANDLE;

//--- Buffers
double buffer_rsi[], buffer_atr[];

//--- State
datetime last_bar_time = 0;
bool has_position = false;
int position_ticket = 0;
string position_type = "";

//+------------------------------------------------------------------+
int OnInit()
{
   handle_rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   handle_atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   
   if(handle_rsi == INVALID_HANDLE || handle_atr == INVALID_HANDLE)
   {
      Print("ERROR: No se pudieron crear los indicadores");
      return INIT_FAILED;
   }
   
   ArraySetAsSeries(buffer_rsi, true);
   ArraySetAsSeries(buffer_atr, true);
   
   Print("xau_price_structure iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handle_rsi != INVALID_HANDLE) IndicatorRelease(handle_rsi);
   if(handle_atr != INVALID_HANDLE) IndicatorRelease(handle_atr);
   Print("xau_price_structure detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime curr_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   
   if(curr_time != last_bar_time)
   {
      last_bar_time = curr_time;
      if(CopyIndicators())
         CheckStrategy();
   }
   
   ManagePosition();
}

//+------------------------------------------------------------------+
bool CopyIndicators()
{
   if(CopyBuffer(handle_rsi, 0, 0, 1, buffer_rsi) <= 0) return false;
   if(CopyBuffer(handle_atr, 0, 0, 1, buffer_atr) <= 0) return false;
   return true;
}

//+------------------------------------------------------------------+
void CheckStrategy()
{
   if(has_position)
      return;
   
   double price = iClose(_Symbol, PERIOD_CURRENT, 0);
   double rsi = buffer_rsi[0];
   double atr = buffer_atr[0];
   
   // Calcular soporte y resistencia
   double support = price;
   double resistance = price;
   
   for(int i = 1; i <= Lookback; i++)
   {
      double low = iLow(_Symbol, PERIOD_CURRENT, i);
      double high = iHigh(_Symbol, PERIOD_CURRENT, i);
      
      if(low < support)
         support = low;
      if(high > resistance)
         resistance = high;
   }
   
   // Señales
   bool buy_signal = false;
   bool sell_signal = false;
   
   // BUY: toca soporte + RSI > 50 + precio recupera
   if(MathAbs(price - support) <= atr * 0.3 && rsi > 50)
   {
      double prev_price = iClose(_Symbol, PERIOD_CURRENT, 1);
      if(price > prev_price)
         buy_signal = true;
   }
   
   // SELL: toca resistencia + RSI < 50 + precio baja
   if(MathAbs(price - resistance) <= atr * 0.3 && rsi < 50)
   {
      double prev_price = iClose(_Symbol, PERIOD_CURRENT, 1);
      if(price < prev_price)
         sell_signal = true;
   }
   
   if(buy_signal)
      OpenPosition("BUY", price, atr);
   else if(sell_signal)
      OpenPosition("SELL", price, atr);
   
   WriteSignal(buy_signal ? "BUY" : (sell_signal ? "SELL" : "NADA"), price);
}

//+------------------------------------------------------------------+
void OpenPosition(string type, double price, double atr)
{
   double sl = 0, tp = 0;
   
   if(type == "BUY")
   {
      sl = price - (atr * SL_ATR_Multiplier);
      tp = price + (atr * TP_ATR_Multiplier);
   }
   else
   {
      sl = price + (atr * SL_ATR_Multiplier);
      tp = price - (atr * TP_ATR_Multiplier);
   }
   
   int ticket = OrderSend(_Symbol, type == "BUY" ? ORDER_TYPE_BUY : ORDER_TYPE_SELL,
                          LotSize, price, 10, sl, tp, "PriceStructure", MagicNumber, 0, 
                          type == "BUY" ? clrGreen : clrRed);
   
   if(ticket > 0)
   {
      has_position = true;
      position_ticket = ticket;
      position_type = type;
      Print("Opened ", type, " ticket=", ticket, " SL=", sl, " TP=", tp);
   }
}

//+------------------------------------------------------------------+
void ManagePosition()
{
   if(!has_position)
      return;
   
   if(!OrderSelect(position_ticket, SELECT_BY_TICKET))
   {
      has_position = false;
      return;
   }
   
   double price = OrderOpenPrice();
   double current = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = OrderStopLoss();
   
   // Trailing SL
   if(position_type == "BUY" && current > price + 0.75)
   {
      double new_sl = price + 0.50;
      if(new_sl > sl)
         OrderModify(position_ticket, price, new_sl, OrderTakeProfit(), 0, clrGreen);
   }
   else if(position_type == "SELL" && current < price - 0.75)
   {
      double new_sl = price - 0.50;
      if(new_sl < sl || sl == 0)
         OrderModify(position_ticket, price, new_sl, OrderTakeProfit(), 0, clrRed);
   }
   
   if(OrderCloseTime() > 0)
      has_position = false;
}

//+------------------------------------------------------------------+
void WriteSignal(string signal, double price)
{
   int h = FileOpen(InpSignalFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h != INVALID_HANDLE)
   {
      string data = "{\"signal\":\"" + signal + "\",\"price\":" + DoubleToString(price, 2) + 
                    ",\"time\":\"" + TimeToString(TimeCurrent()) + "\"}";
      FileWriteString(h, data);
      FileClose(h);
   }
}