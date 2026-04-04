//+------------------------------------------------------------------+
//|                                        XAU_DataSender.mq5         |
//|                                        Para Kilito — v3 con ATR    |
//+------------------------------------------------------------------+
// Este Expert Advisor escribe datos de XAU/USD a un archivo JSON
// que el servidor FastAPI lee directamente.
//
// Incluye: RSI14, EMA50, EMA200, ATR14
//
// Instalación:
// 1. MetaEditor (F4) > Archivo > Nuevo > Expert Advisor > nombre: XAU_DataSender
// 2. Pega este código completo y compila (F7)
// 3. Arrastra el EA al gráfico de XAUUSD M1
//
//+------------------------------------------------------------------+

#property copyright "Kilito - Trading System"
#property version   "3.00"
#property strict

//--- Input parameters
input string OutputFile   = "xau_data.json";  // Nombre del archivo
input int    RSI_Period   = 14;                // Período RSI
input int    EMA50_Period = 50;                // Período EMA 50
input int    EMA200_Period = 200;              // Período EMA 200
input int    ATR_Period   = 14;                // Período ATR
input int    CandlesToSend = 250;              // Cantidad de velas

//--- Variables globales
int rsi_handle;
int ema50_handle;
int ema200_handle;
int atr_handle;
datetime lastBarTime = 0;

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

   Print("XAU DataSender v3 iniciado");
   Print("Archivo: ", OutputFile);
   Print("Simbolo: ", _Symbol);

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
   if(currentBarTime == lastBarTime)
      return;

   lastBarTime = currentBarTime;
   WriteData();
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

   Print("Datos escritos - $" + DoubleToString(bid, 2) + " | RSI: " + DoubleToString(rsi, 1) + " | ATR: " + DoubleToString(atr, 2));
}
//+------------------------------------------------------------------+
