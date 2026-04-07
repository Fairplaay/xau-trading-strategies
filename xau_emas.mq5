//+------------------------------------------------------------------+
//| xau_emas.mq5 - Estrategia EMAs                                   |
//| BUY: precio > EMA200 + RSI 45-70 + toca EMA50                     |
//| SELL: precio < EMA200 + RSI 30-55 + toca EMA50                    |
//+------------------------------------------------------------------+

#property copyright "Kilito"
#property version   "1.00"
#property strict

//--- Inputs
input string InpDataFile = "xau_data.json";
input string InpSignalFile = "xau_signals.json";
input double LotSize = 0.01;
input int    RSI_Period = 14;
input int    EMA50_Period = 50;
input int    EMA200_Period = 200;
input int    ATR_Period = 14;
input int    MagicNumber = 123456;

//--- SL/TP (scalping)
input double SL_ATR_Multiplier = 0.5;  // SL = ATR * 0.5
input double TP_ATR_Multiplier = 1.5;  // TP = ATR * 1.5 (3:1)

//--- Handles
int handle_rsi = INVALID_HANDLE;
int handle_ema50 = INVALID_HANDLE;
int handle_ema200 = INVALID_HANDLE;
int handle_atr = INVALID_HANDLE;

//--- State
datetime last_bar_time = 0;
bool has_position = false;
int position_ticket = 0;
string position_type = "";

//+------------------------------------------------------------------+
int OnInit()
{
   handle_rsi = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   handle_ema50 = iMA(_Symbol, PERIOD_CURRENT, EMA50_Period, 0, MODE_EMA, PRICE_CLOSE);
   handle_ema200 = iMA(_Symbol, PERIOD_CURRENT, EMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   handle_atr = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);
   
   if(handle_rsi == INVALID_HANDLE || handle_ema50 == INVALID_HANDLE ||
      handle_ema200 == INVALID_HANDLE || handle_atr == INVALID_HANDLE)
   {
      Print("ERROR: No se pudieron crear los indicadores");
      return INIT_FAILED;
   }
   
   Print("xau_emasStrategy iniciado");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handle_rsi != INVALID_HANDLE) IndicatorRelease(handle_rsi);
   if(handle_ema50 != INVALID_HANDLE) IndicatorRelease(handle_ema50);
   if(handle_ema200 != INVALID_HANDLE) IndicatorRelease(handle_ema200);
   if(handle_atr != INVALID_HANDLE) IndicatorRelease(handle_atr);
   Print("xau_emas detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime curr_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   
   // Solo procesar al inicio de cada vela
   if(curr_time != last_bar_time)
   {
      last_bar_time = curr_time;
      CheckStrategy();
   }
   
   // Manage position
   ManagePosition();
}

//+------------------------------------------------------------------+
void CheckStrategy()
{
   // Obtener datos
   double price = iClose(_Symbol, PERIOD_CURRENT, 0);
   double ema50 = iMAOnArray(0, 0, EMA50_Period, 0, MODE_EMA, PRICE_CLOSE, 0);
   double ema200 = iMAOnArray(0, 0, EMA200_Period, 0, MODE_EMA, PRICE_CLOSE, 0);
   double rsi = iRSIOnArray(0, 0, RSI_Period, PRICE_CLOSE, 0);
   double atr = iATROnArray(0, 0, ATR_Period, 0);
   
   // Verificar si hay posición abierta
   if(!has_position)
   {
      // Señales BUY/SELL según estrategia EMAs
      bool buy_signal = false;
      bool sell_signal = false;
      
      // BUY: precio > EMA200 + RSI 45-70 + toca EMA50
      if(price > ema200 && rsi >= 45 && rsi <= 70)
      {
         double touch_ema50 = MathAbs(price - ema50);
         if(touch_ema50 <= atr * 0.5)  // Toca EMA50
            buy_signal = true;
      }
      
      // SELL: precio < EMA200 + RSI 30-55 + toca EMA50
      if(price < ema200 && rsi >= 30 && rsi <= 55)
      {
         double touch_ema50 = MathAbs(price - ema50);
         if(touch_ema50 <= atr * 0.5)  // Toca EMA50
            sell_signal = true;
      }
      
      // Ejecutar
      if(buy_signal)
         OpenPosition("BUY", price, atr);
      else if(sell_signal)
         OpenPosition("SELL", price, atr);
      
      // Escribir señal
      WriteSignal(buy_signal ? "BUY" : (sell_signal ? "SELL" : "NADA"), price);
   }
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
                          LotSize, price, 10, sl, tp, "EMAs Strategy", MagicNumber, 0, type == "BUY" ? clrGreen : clrRed);
   
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
   double tp = OrderTakeProfit();
   double profit = OrderProfit();
   
   // Check trailing SL (a favor)
   if(position_type == "BUY" && current > price + 0.75)
   {
      double new_sl = price + 0.50;
      if(new_sl > sl)
         OrderModify(position_ticket, price, new_sl, tp, 0, clrGreen);
   }
   else if(position_type == "SELL" && current < price - 0.75)
   {
      double new_sl = price - 0.50;
      if(new_sl < sl || sl == 0)
         OrderModify(position_ticket, price, new_sl, tp, 0, clrRed);
   }
   
   // Check if closed by SL/TP
   if(OrderType() == OP_SELL || OrderType() == OP_BUY)
   {
      if(OrderCloseTime() > 0)
      {
         has_position = false;
         Print("Position closed");
      }
   }
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