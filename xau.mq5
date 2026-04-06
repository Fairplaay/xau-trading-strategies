//+------------------------------------------------------------------+
//| XAU_DataSender.mq5 v6 - Para Kilito                             |
//| Comunica con Python via archivos JSON                            |
//+------------------------------------------------------------------+

#property copyright "Kilito"
#property version   "6.00"
#property strict

//--- Inputs
input string InpDataFile = "xau_data.json";
input string InpCmdFile = "xau_commands.json";
input int    RSI_Period = 14;
input int    EMA50_Period = 50;
input int    EMA200_Period = 200;
input int    ATR_Period = 14;
input int    BarsToSave = 200;

//--- Handles
int handle_rsi = INVALID_HANDLE;
int handle_ema50 = INVALID_HANDLE;
int handle_ema200 = INVALID_HANDLE;
int handle_atr = INVALID_HANDLE;

//--- Time tracking
datetime last_bar_time = 0;
datetime last_cmd_time = 0;

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
   
   Print("XAU DataSender v6 iniciado");
   WriteData();
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(handle_rsi != INVALID_HANDLE) IndicatorRelease(handle_rsi);
   if(handle_ema50 != INVALID_HANDLE) IndicatorRelease(handle_ema50);
   if(handle_ema200 != INVALID_HANDLE) IndicatorRelease(handle_ema200);
   if(handle_atr != INVALID_HANDLE) IndicatorRelease(handle_atr);
   Print("XAU DataSender detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   // Procesar comandos
   ProcessCommand();
   
   // Escribir datos cuando cambia vela
   datetime curr_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(curr_time != last_bar_time)
   {
      last_bar_time = curr_time;
      WriteData();
   }
}

//+------------------------------------------------------------------+
void ProcessCommand()
{
   // Abrir archivo de comandos
   int h = FileOpen(InpCmdFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;
   
   // Leer todo el contenido
   string data = "";
   while(!FileIsEnding(h))
      data += FileReadString(h);
   FileClose(h);
   
   if(data == "")
      return;
   
   // Extraer timestamp
   int pos = StringFind(data, "\"timestamp\":");
   if(pos == -1)
   {
      ClearCommandFile();
      return;
   }
   
   // Buscar entre comillas después de "timestamp":
   int p1 = StringFind(data, "\"", pos + 11);
   int p2 = StringFind(data, "\"", p1 + 1);
   if(p1 == -1 || p2 == -1)
   {
      ClearCommandFile();
      return;
   }
   
   string ts = StringSubstr(data, p1 + 1, p2 - p1 - 1);
   datetime cmd_time = StringToTime(ts);
   
   if(cmd_time <= last_cmd_time)
      return;
   
   last_cmd_time = cmd_time;
   
   // Extraer action
   pos = StringFind(data, "\"action\":");
   if(pos == -1)
   {
      ClearCommandFile();
      return;
   }
   
   p1 = StringFind(data, "\"", pos + 8);
   p2 = StringFind(data, "\"", p1 + 1);
   string action = (p1 != -1 && p2 != -1) ? StringSubstr(data, p1 + 1, p2 - p1 - 1) : "";
   
   // Extraer parámetros
   double vol = GetDoubleValue(data, "volume");
   double sl = GetDoubleValue(data, "sl");
   double tp = GetDoubleValue(data, "tp");
   double tk = GetDoubleValue(data, "ticket");
   
   // Ejecutar comando
   string result = "OK";
   int ticket = 0;
   
   if(action == "BUY")
      ticket = (int)Trade(ORDER_TYPE_BUY, vol, sl, tp);
   else if(action == "SELL")
      ticket = (int)Trade(ORDER_TYPE_SELL, vol, sl, tp);
   else if(action == "CLOSE")
      result = ClosePos((int)tk) ? "OK" : "FAIL";
   else if(action == "MODIFY")
      result = ModifySLTP((int)tk, sl, tp) ? "OK" : "FAIL";
   else
      result = "UNKNOWN";
   
   Print("CMD: ", action, " -> ", result);
   ClearCommandFile();
}

//+------------------------------------------------------------------+
double GetDoubleValue(string str, string key)
{
   string k = "\"" + key + "\":";
   int p = StringFind(str, k);
   if(p == -1)
      return 0;
   
   int i = p + StringLen(k);
   while(i < StringLen(str) && str[i] == ' ')
      i++;
   
   string val = "";
   while(i < StringLen(str))
   {
      ushort c = StringGetCharacter(str, i);
      if((c >= '0' && c <= '9') || c == '.' || c == '-')
      {
         val += ShortToString(c);
      }
      else if(c == ',' || c == '}')
         break;
      i++;
   }
   
   return StringToDouble(val);
}

//+------------------------------------------------------------------+
ulong Trade(ENUM_ORDER_TYPE dir, double lot, double sl, double tp)
{
   double price = (dir == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) 
                                           : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   
   req.action = TRADE_ACTION_DEAL;
   req.symbol = _Symbol;
   req.volume = lot;
   req.type = dir;
   req.price = price;
   req.sl = (sl > 0) ? NormalizeDouble(sl, _Digits) : 0;
   req.tp = (tp > 0) ? NormalizeDouble(tp, _Digits) : 0;
   req.deviation = 20;
   req.magic = 123456;
   req.comment = "Kilito";
   req.type_time = ORDER_TIME_GTC;
   req.type_filling = ORDER_FILLING_IOC;
   
   if(OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
      return res.order;
   
   Print("Trade ERROR: ", res.retcode);
   return 0;
}

//+------------------------------------------------------------------+
bool ClosePos(int ticket)
{
   if(ticket <= 0)
      return false;
      
   if(!PositionSelectByTicket(ticket))
      return false;
   
   ENUM_POSITION_TYPE ptype = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   ENUM_ORDER_TYPE otype = (ptype == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   double price = (otype == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) 
                                             : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   
   req.action = TRADE_ACTION_DEAL;
   req.symbol = _Symbol;
   req.volume = PositionGetDouble(POSITION_VOLUME);
   req.type = otype;
   req.price = price;
   req.deviation = 20;
   req.position = ticket;
   req.comment = "Kilito Close";
   req.type_time = ORDER_TIME_GTC;
   req.type_filling = ORDER_FILLING_IOC;
   
   return OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE;
}

//+------------------------------------------------------------------+
bool ModifySLTP(int ticket, double sl, double tp)
{
   if(ticket <= 0)
      return false;
   
   if(!PositionSelectByTicket(ticket))
      return false;
   
   MqlTradeRequest req = {};
   MqlTradeResult res = {};
   
   req.action = TRADE_ACTION_SLTP;
   req.position = ticket;
   req.sl = (sl > 0) ? NormalizeDouble(sl, _Digits) : 0;
   req.tp = (tp > 0) ? NormalizeDouble(tp, _Digits) : 0;
   
   return OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE;
}

//+------------------------------------------------------------------+
void ClearCommandFile()
{
   // Sobrescribir con archivo vacío
   int h = FileOpen(InpCmdFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h != INVALID_HANDLE)
      FileClose(h);
}

//+------------------------------------------------------------------+
void WriteData()
{
   // Obtener precio
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   int spr = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   
   // Obtener indicadores - true para que índice 0 sea el más reciente
   double rsi[], ema50[], ema200[], atr[];
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(ema50, true);
   ArraySetAsSeries(ema200, true);
   ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(handle_rsi, 0, 0, 1, rsi) < 1) return;
   if(CopyBuffer(handle_ema50, 0, 0, 1, ema50) < 1) return;
   if(CopyBuffer(handle_ema200, 0, 0, 1, ema200) < 1) return;
   if(CopyBuffer(handle_atr, 0, 0, 1, atr) < 1) return;
   
   // Obtener velas
   MqlRates rates[];
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, BarsToSave, rates);
   if(copied < 100)
      return;
   
   // Escribir archivo
   int h = FileOpen(InpDataFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;
   
   string ts = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   
   FileWriteString(h, "{\n");
   FileWriteString(h, "  \"symbol\":\"" + _Symbol + "\",\n");
   FileWriteString(h, "  \"bid\":" + DoubleToString(bid, 2) + ",\n");
   FileWriteString(h, "  \"ask\":" + DoubleToString(ask, 2) + ",\n");
   FileWriteString(h, "  \"spread\":" + spr + ",\n");
   FileWriteString(h, "  \"rsi14\":" + DoubleToString(rsi[0], 1) + ",\n");
   FileWriteString(h, "  \"ema50\":" + DoubleToString(ema50[0], 2) + ",\n");
   FileWriteString(h, "  \"ema200\":" + DoubleToString(ema200[0], 2) + ",\n");
   FileWriteString(h, "  \"atr14\":" + DoubleToString(atr[0], 2) + ",\n");
   FileWriteString(h, "  \"timestamp\":\"" + ts + "\",\n");
   FileWriteString(h, "  \"last_cmd\":\"" + TimeToString(last_cmd_time, TIME_DATE|TIME_SECONDS) + "\",\n");
   FileWriteString(h, "  \"velas\":[\n");
   
   for(int i = copied - 1; i >= 0; i--)
   {
      string c = (i > 0) ? "," : "";
      string t = TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS);
      FileWriteString(h, "    {\"t\":\"" + t + "\",\"o\":" + DoubleToString(rates[i].open, 2) +
                ",\"h\":" + DoubleToString(rates[i].high, 2) +
                ",\"l\":" + DoubleToString(rates[i].low, 2) +
                ",\"c\":" + DoubleToString(rates[i].close, 2) + "}" + c + "\n");
   }
   
   FileWriteString(h, "  ]\n");
   FileWriteString(h, "}\n");
   
   FileClose(h);
}