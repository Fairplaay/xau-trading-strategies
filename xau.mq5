//+------------------------------------------------------------------+
//|                                        XAU_DataSender.mq5       |
//|                                        Para Kilito — v5          |
//|                                        Envía y recibe comandos   |
//+------------------------------------------------------------------+

#property copyright "Kilito - Trading System"
#property version   "5.00"
#property strict

//--- Input parameters
input string OutputFile   = "xau_data.json";
input string CommandFile  = "xau_commands.json";
input int    RSI_Period   = 14;
input int    EMA50_Period = 50;
input int    EMA200_Period = 200;
input int    ATR_Period   = 14;
input int    CandlesToSend = 250;

//--- Handles de indicadores
int rsi_handle;
int ema50_handle;
int ema200_handle;
int atr_handle;
datetime lastBarTime = 0;
datetime lastCommandTime = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   rsi_handle = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
   ema50_handle = iMA(_Symbol, PERIOD_CURRENT, EMA50_Period, 0, MODE_EMA, PRICE_CLOSE);
   ema200_handle = iMA(_Symbol, PERIOD_CURRENT, EMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   atr_handle = iATR(_Symbol, PERIOD_CURRENT, ATR_Period);

   if(rsi_handle == INVALID_HANDLE || ema50_handle == INVALID_HANDLE ||
      ema200_handle == INVALID_HANDLE || atr_handle == INVALID_HANDLE)
   {
      Print("Error creando handles de indicadores");
      return(INIT_FAILED);
   }

   Print("XAU DataSender v5 iniciado");
   WriteData();
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(rsi_handle);
   IndicatorRelease(ema50_handle);
   IndicatorRelease(ema200_handle);
   IndicatorRelease(atr_handle);
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   
   ProcessCommands();
   
   if(currentBarTime != lastBarTime)
   {
      lastBarTime = currentBarTime;
      WriteData();
   }
}

//+------------------------------------------------------------------+
void ProcessCommands()
{
   int handle = FileOpen(CommandFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;
   
   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle);
   FileClose(handle);
   
   if(content == "")
      return;
   
   // Extraer timestamp
   int tsPos = StringFind(content, "\"timestamp\":");
   if(tsPos == -1)
   {
      FileDelete(CommandFile);
      return;
   }
   
   // Extraer valor del timestamp entre comillas
   int tsStart = StringFind(content, "\"", tsPos + 10) + 1;
   int tsEnd = StringFind(content, "\"", tsStart);
   string tsStr = StringSubstr(content, tsStart, tsEnd - tsStart);
   datetime cmdTime = StringToTime(tsStr);
   
   if(cmdTime <= lastCommandTime)
      return;
   
   lastCommandTime = cmdTime;
   
   // Extraer action
   int actionPos = StringFind(content, "\"action\":");
   if(actionPos == -1)
   {
      FileDelete(CommandFile);
      return;
   }
   
   int actStart = StringFind(content, "\"", actionPos + 8) + 1;
   int actEnd = StringFind(content, "\"", actStart);
   string action = StringSubstr(content, actStart, actEnd - actStart);
   
   // Extraer volume
   double volume = GetDoubleParam(content, "volume");
   double sl = GetDoubleParam(content, "sl");
   double tp = GetDoubleParam(content, "tp");
   long ticket = (long)GetDoubleParam(content, "ticket");
   
   string result = "OK";
   int orderTicket = 0;
   
   if(action == "BUY")
      orderTicket = (int)ExecuteOrder(ORDER_TYPE_BUY, volume, sl, tp);
   else if(action == "SELL")
      orderTicket = (int)ExecuteOrder(ORDER_TYPE_SELL, volume, sl, tp);
   else if(action == "CLOSE")
      orderTicket = ClosePosition(ticket) ? (int)ticket : 0;
   else if(action == "MODIFY")
      orderTicket = ModifyPosition(ticket, sl, tp) ? (int)ticket : 0;
   else
      result = "UNKNOWN_ACTION";
   
   Print("Comando procesado: ", action, " Resultado: ", result);
   FileDelete(CommandFile);
}

//+------------------------------------------------------------------+
double GetDoubleParam(string content, string param)
{
   int pos = StringFind(content, "\"" + param + "\":");
   if(pos == -1)
      return 0;
   
   int start = pos + StringLen(param) + 3;
   string val = "";
   for(int i = start; i < StringLen(content); i++)
   {
      uchar c = StringGetCharacter(content, i);
      if((c >= '0' && c <= '9') || c == '.' || c == '-')
         val += ShortToString(c);
      else if(c == ',' || c == '}')
         break;
   }
   
   return StringToDouble(val);
}

//+------------------------------------------------------------------+
ulong ExecuteOrder(ENUM_ORDER_TYPE type, double volume, double sl, double tp)
{
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) 
                                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = volume;
   request.type = type;
   request.price = price;
   request.sl = NormalizeDouble(sl, _Digits);
   request.tp = NormalizeDouble(tp, _Digits);
   request.deviation = 20;
   request.magic = 123456;
   request.comment = "Kilito Bot";
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_IOC;
   
   bool sent = OrderSend(request, result);
   
   if(sent && result.retcode == TRADE_RETCODE_DONE)
      return result.order;
   
   Print("Error orden: ", result.retcode);
   return 0;
}

//+------------------------------------------------------------------+
bool ClosePosition(long ticket)
{
   if(ticket <= 0)
      return false;
      
   if(!PositionSelectByTicket(ticket))
      return false;
      
   ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   ENUM_ORDER_TYPE type = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) 
                                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = PositionGetDouble(POSITION_VOLUME);
   request.type = type;
   request.price = price;
   request.deviation = 20;
   request.position = (int)ticket;
   request.comment = "Kilito Close";
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_IOC;
   
   return OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE;
}

//+------------------------------------------------------------------+
bool ModifyPosition(long ticket, double sl, double tp)
{
   if(ticket <= 0)
      return false;
      
   if(!PositionSelectByTicket(ticket))
      return false;
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = (int)ticket;
   request.sl = NormalizeDouble(sl, _Digits);
   request.tp = NormalizeDouble(tp, _Digits);
   
   return OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE;
}

//+------------------------------------------------------------------+
void FileDelete(string filename)
{
   // MQL5 no tiene delete, escribir archivo vacío
   int h = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h != INVALID_HANDLE)
      FileClose(h);
}

//+------------------------------------------------------------------+
void WriteData()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);

   double rsi_buf[1], ema50_buf[1], ema200_buf[1], atr_buf[1];

   if(CopyBuffer(rsi_handle, 0, 0, 1, rsi_buf) < 1 ||
      CopyBuffer(ema50_handle, 0, 0, 1, ema50_buf) < 1 ||
      CopyBuffer(ema200_handle, 0, 0, 1, ema200_buf) < 1 ||
      CopyBuffer(atr_handle, 0, 0, 1, atr_buf) < 1)
      return;

   double rsi = rsi_buf[0];
   double ema50 = ema50_buf[0];
   double ema200 = ema200_buf[0];
   double atr = atr_buf[0];

   MqlRates rates[];
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, CandlesToSend, rates);
   if(copied < 200)
      return;

   int handle = FileOpen(OutputFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;

   string ts = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

   FileWriteString(handle, "{\n");
   FileWriteString(handle, "  \"symbol\": \"" + _Symbol + "\",\n");
   FileWriteString(handle, "  \"bid\": " + DoubleToString(bid, 2) + ",\n");
   FileWriteString(handle, "  \"ask\": " + DoubleToString(ask, 2) + ",\n");
   FileWriteString(handle, "  \"spread\": " + IntegerToString(spread) + ",\n");
   FileWriteString(handle, "  \"rsi14\": " + DoubleToString(rsi, 1) + ",\n");
   FileWriteString(handle, "  \"ema50\": " + DoubleToString(ema50, 2) + ",\n");
   FileWriteString(handle, "  \"ema200\": " + DoubleToString(ema200, 2) + ",\n");
   FileWriteString(handle, "  \"atr14\": " + DoubleToString(atr, 2) + ",\n");
   FileWriteString(handle, "  \"timestamp\": \"" + ts + "\",\n");
   FileWriteString(handle, "  \"last_command\": \"" + TimeToString(lastCommandTime, TIME_DATE|TIME_SECONDS) + "\",\n");
   
   FileWriteString(handle, "  \"velas\": [\n");
   for(int i = copied - 1; i >= 0; i--)
   {
      string comma = (i > 0) ? "," : "";
      FileWriteString(handle, "    {\"t\":\"" + TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS) + "\",");
      FileWriteString(handle, "\"o\":" + DoubleToString(rates[i].open, 2) + ",");
      FileWriteString(handle, "\"h\":" + DoubleToString(rates[i].high, 2) + ",");
      FileWriteString(handle, "\"l\":" + DoubleToString(rates[i].low, 2) + ",");
      FileWriteString(handle, "\"c\":" + DoubleToString(rates[i].close, 2) + "}" + comma + "\n");
   }
   FileWriteString(handle, "  ]\n");
   FileWriteString(handle, "}\n");

   FileClose(handle);
}