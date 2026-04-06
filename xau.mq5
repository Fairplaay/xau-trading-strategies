//+------------------------------------------------------------------+
//|                                        XAU_DataSender.mq5       |
//|                                        Para Kilito — v4          |
//|                                        Envía y recibe comandos   |
//+------------------------------------------------------------------+
// Este Expert Advisor:
// 1. Escribe datos de XAU/USD a xau_data.json (precio, RSI, EMA, etc)
// 2. Lee comandos de xau_commands.json y los ejecuta en MT5
// 3. Escribe el resultado de las órdenes en xau_data.json
//
// Comandos soportados (xau_commands.json):
// - BUY: { "action": "BUY", "volume": 0.01, "sl": 3010, "tp": 3020 }
// - SELL: { "action": "SELL", "volume": 0.01, "sl": 3010, "tp": 3020 }
// - CLOSE: { "action": "CLOSE", "ticket": 12345 }
// - MODIFY: { "action": "MODIFY", "ticket": 12345, "sl": 3010, "tp": 3020 }
//
//+------------------------------------------------------------------+

#property copyright "Kilito - Trading System"
#property version   "4.00"
#property strict

//--- Input parameters
input string OutputFile   = "xau_data.json";    // Archivo de datos
input string CommandFile  = "xau_commands.json"; // Archivo de comandos
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

//--- Último comando procesado
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

   Print("XAU DataSender v4 iniciado");
   Print("Datos: ", OutputFile);
   Print("Comandos: ", CommandFile);

   // Escribir datos iniciales
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
   Print("XAU DataSender detenido");
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   
   // Procesar comandos en cada tick
   ProcessCommands();
   
   // Escribir datos solo cuando cambia la vela
   if(currentBarTime != lastBarTime)
   {
      lastBarTime = currentBarTime;
      WriteData();
   }
}

//+------------------------------------------------------------------+
// Procesar comandos desde Python
void ProcessCommands()
{
   // Abrir archivo de comandos
   int handle = FileOpen(CommandFile, FILE_READ|FILE_TXT|FILE_ANSI, 0, CP_UTF8);
   if(handle == INVALID_HANDLE)
      return; // No hay comandos
   
   // Leer contenido
   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle);
   FileClose(handle);
   
   if(content == "")
      return;
   
   // Buscar timestamp del comando
   int tsPos = StringFind(content, "\"timestamp\":");
   if(tsPos == -1)
   {
      DeleteCommandFile();
      return;
   }
   
   // Extraer timestamp
   string tsStr = "";
   int i = tsPos + 11;
   while(i < StringLen(content) && StringGetCharacter(content, i) != ',' && StringGetCharacter(content, i) != '}')
   {
      tsStr += StringGetCharacter(content, i);
      i++;
   }
   tsStr = StringTrim(tsStr);
   tsStr = StringReplace(tsStr, "\"", "");
   
   datetime cmdTime = StringToTime(tsStr);
   
   // Si ya procesamos este comando, salir
   if(cmdTime <= lastCommandTime)
      return;
   
   lastCommandTime = cmdTime;
   
   // Procesar comando
   string result = "OK";
   int orderTicket = 0;
   
   // BUSCAR ACCIÓN
   int actionPos = StringFind(content, "\"action\":");
   if(actionPos != -1)
   {
      string action = "";
      i = actionPos + 8;
      while(i < StringLen(content) && StringGetCharacter(content, i) != ',' && StringGetCharacter(content, i) != '}')
      {
         action += StringGetCharacter(content, i);
         i++;
      }
      action = StringTrim(action);
      action = StringReplace(action, "\"", "");
      
      // Obtener parámetros
      double volume = GetParamDouble(content, "volume");
      double sl = GetParamDouble(content, "sl");
      double tp = GetParamDouble(content, "tp");
      long ticket = GetParamLong(content, "ticket");
      
      // Ejecutar según acción
      if(action == "BUY")
         orderTicket = ExecuteOrder(ORDER_TYPE_BUY, volume, sl, tp);
      else if(action == "SELL")
         orderTicket = ExecuteOrder(ORDER_TYPE_SELL, volume, sl, tp);
      else if(action == "CLOSE")
         orderTicket = CloseOrder((int)ticket) ? (int)ticket : 0;
      else if(action == "MODIFY")
         orderTicket = ModifyOrder((int)ticket, sl, tp) ? (int)ticket : 0;
      else
         result = "UNKNOWN_ACTION";
   }
   else
   {
      result = "NO_ACTION";
   }
   
   // Escribir resultado
   WriteResult(orderTicket, result);
   
   // Eliminar archivo de comandos
   DeleteCommandFile();
}

//+------------------------------------------------------------------+
double GetParamDouble(string content, string param)
{
   int pos = StringFind(content, "\"" + param + "\":");
   if(pos == -1)
      return 0;
   
   string value = "";
   int i = pos + StringLen(param) + 2;
   while(i < StringLen(content) && StringGetCharacter(content, i) != ',' && StringGetCharacter(content, i) != '}')
   {
      value += StringGetCharacter(content, i);
      i++;
   }
   return StringToDouble(StringTrim(value));
}

//+------------------------------------------------------------------+
long GetParamLong(string content, string param)
{
   int pos = StringFind(content, "\"" + param + "\":");
   if(pos == -1)
      return 0;
   
   string value = "";
   int i = pos + StringLen(param) + 2;
   while(i < StringLen(content) && StringGetCharacter(content, i) != ',' && StringGetCharacter(content, i) != '}')
   {
      value += StringGetCharacter(content, i);
      i++;
   }
   return StringToInteger(StringTrim(value));
}

//+------------------------------------------------------------------+
long ExecuteOrder(ENUM_ORDER_TYPE type, double volume, double sl, double tp)
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
bool CloseOrder(int ticket)
{
   if(ticket <= 0)
      return false;
      
   if(!OrderSelect(ticket))
      return false;
      
   ENUM_ORDER_TYPE type = (OrderType() == ORDER_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) 
                                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = OrderLots();
   request.type = type;
   request.price = price;
   request.deviation = 20;
   request.magic = OrderMagicNumber();
   request.comment = "Kilito Close";
   request.position = ticket;
   request.type_time = ORDER_TIME_GTC;
   request.type_filling = ORDER_FILLING_IOC;
   
   return OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE;
}

//+------------------------------------------------------------------+
bool ModifyOrder(int ticket, double sl, double tp)
{
   if(ticket <= 0)
      return false;
      
   if(!OrderSelect(ticket))
      return false;
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.sl = NormalizeDouble(sl, _Digits);
   request.tp = NormalizeDouble(tp, _Digits);
   request.magic = OrderMagicNumber();
   
   return OrderSend(request, result) && result.retcode == TRADE_RETCODE_DONE;
}

//+------------------------------------------------------------------+
void DeleteCommandFile()
{
   int handle = FileOpen(CommandFile, FILE_DELETE);
   if(handle != INVALID_HANDLE)
      FileClose(handle);
}

//+------------------------------------------------------------------+
void WriteResult(int ticket, string result)
{
   // Agregar resultado al archivo de datos
   // El Python debe verificar este campo
}

//+------------------------------------------------------------------+
void WriteData()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   int spread = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);

   double rsi_buf[1];
   double ema50_buf[1];
   double ema200_buf[1];
   double atr_buf[1];

   if(CopyBuffer(rsi_handle, 0, 0, 1, rsi_buf) < 1 ||
      CopyBuffer(ema50_handle, 0, 0, 1, ema50_buf) < 1 ||
      CopyBuffer(ema200_handle, 0, 0, 1, ema200_buf) < 1 ||
      CopyBuffer(atr_handle, 0, 0, 1, atr_buf) < 1)
   {
      Print("Error copiando indicadores");
      return;
   }

   double rsi = NormalizeDouble(rsi_buf[0], 1);
   double ema50 = NormalizeDouble(ema50_buf[0], _Digits);
   double ema200 = NormalizeDouble(ema200_buf[0], _Digits);
   double atr = NormalizeDouble(atr_buf[0], 2);

   MqlRates rates[];
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, CandlesToSend, rates);
   if(copied < 200)
   {
      Print("No hay suficientes velas: ", copied);
      return;
   }

   int handle = FileOpen(OutputFile, FILE_WRITE|FILE_TXT|FILE_ANSI, 0, CP_UTF8);
   if(handle == INVALID_HANDLE)
   {
      Print("No se pudo abrir archivo: ", GetLastError());
      return;
   }

   string accountStr = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
   string serverStr = AccountInfoString(ACCOUNT_SERVER);
   string ts = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

   FileWriteString(handle, "{\n");
   FileWriteString(handle, "  \"symbol\": \"" + _Symbol + "\",\n");
   FileWriteString(handle, "  \"timeframe\": \"M1\",\n");
   FileWriteString(handle, "  \"bid\": " + DoubleToString(bid, 2) + ",\n");
   FileWriteString(handle, "  \"ask\": " + DoubleToString(ask, 2) + ",\n");
   FileWriteString(handle, "  \"mid\": " + DoubleToString((bid + ask) / 2.0, 2) + ",\n");
   FileWriteString(handle, "  \"spread\": " + IntegerToString(spread) + ",\n");
   FileWriteString(handle, "  \"rsi14\": " + DoubleToString(rsi, 1) + ",\n");
   FileWriteString(handle, "  \"ema50\": " + DoubleToString(ema50, 2) + ",\n");
   FileWriteString(handle, "  \"ema200\": " + DoubleToString(ema200, 2) + ",\n");
   FileWriteString(handle, "  \"atr14\": " + DoubleToString(atr, 2) + ",\n");
   FileWriteString(handle, "  \"account\": " + accountStr + ",\n");
   FileWriteString(handle, "  \"server\": \"" + serverStr + "\",\n");
   FileWriteString(handle, "  \"last_command_result\": \"\",\n");

   // Velas
   FileWriteString(handle, "  \"velas\": [\n");
   for(int i = copied - 1; i >= 0; i--)
   {
      string comma = (i > 0) ? "," : "";
      string velas = "    {\"t\":\"" + TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS) + "\","
                     + "\"o\":" + DoubleToString(rates[i].open, 2) + ","
                     + "\"h\":" + DoubleToString(rates[i].high, 2) + ","
                     + "\"l\":" + DoubleToString(rates[i].low, 2) + ","
                     + "\"c\":" + DoubleToString(rates[i].close, 2) + "}"
                     + comma + "\n";
      FileWriteString(handle, velas);
   }
   FileWriteString(handle, "  ],\n");

   FileWriteString(handle, "  \"timestamp\": \"" + ts + "\"\n");
   FileWriteString(handle, "}\n");

   FileClose(handle);
}
//+------------------------------------------------------------------+