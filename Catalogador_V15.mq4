//+------------------------------------------------------------------+
//|  Catalogador_V15.mq4                                             |
//|  Script que varre o historico e cataloga sinais V15 com WIN/LOSS |
//|  Gera CSV em MQL4\Files\Catalogador_V15\Catalogo_{SYM}_{TF}m.csv|
//+------------------------------------------------------------------+
#property copyright   "BOTDINVELAS"
#property version     "1.0"
#property strict
#property show_inputs

// =======================================================================
// INPUTS - Periodo e horario de catalogacao
// =======================================================================
input int    Catalog_Days   = 7;   // Dias para tras a catalogar
input int    Hour_Start     = 0;   // Hora inicio (0-23)
input int    Hour_End       = 23;  // Hora fim (0-23)
input int    Minute_End     = 59;  // Minuto fim

// =======================================================================
// INPUTS - Score V15 (identicos ao indicador BOTDINVELAS_V15.mq4)
// =======================================================================

//--- Score minimo V15
input int    V15_Score_Min_M5  = 68;   // Score minimo M5
input int    V15_Score_Min_M15 = 65;   // Score minimo M15
input int    V15_Gap_Min       = 15;   // Diferenca minima call_score - put_score
input int    Min_Components    = 3;    // Minimo de componentes com score > 0

//--- RSI
input int    RSI_Period        = 14;   // Periodo RSI
input int    RSI_Oversold      = 30;   // RSI <= este = oversold -> 25pts CALL
input int    RSI_Overbought    = 70;   // RSI >= este = overbought -> 25pts PUT
input bool   RSI_Enable        = true; // Habilitar componente RSI

//--- Bollinger Bands
input int    BB_Period         = 20;   // Periodo Bollinger Bands
input double BB_StdDev         = 2.0;  // Multiplicador desvio padrao
input double BB_Proximity      = 0.25; // Fracao da largura considerada "proximo"
input bool   BB_Enable         = true; // Habilitar componente BB

//--- Wick (sombra)
input double Wick_Min_Ratio    = 0.45; // Razao minima sombra/range da vela
input int    Wick_Score_Max    = 25;   // Pontuacao maxima do wick
input int    Wick_Score_Factor = 35;   // Fator de conversao ratio -> pts
input bool   Wick_Enable       = true; // Habilitar componente Wick

//--- Impulso + Contexto
input int    Impulse_Lookback   = 5;      // Janela de impulso (velas)
input int    Context_Lookback   = 12;     // Janela de contexto (velas)
input double Trend_Threshold    = 0.0008; // Limiar para detectar tendencia
input double Impulse_Threshold  = 0.0006; // Limiar minimo do impulso
input int    Impulse_Multiplier = 8000;   // Fator impulso -> pontos
input bool   Impulse_Enable     = true;   // Habilitar componente Impulso

//--- Canal Keltner
input int    Keltner_Period     = 20;   // Periodo EMA/ATR Keltner
input double Keltner_Shift_Mult = 1.5;  // Multiplicador ATR Keltner
input bool   Keltner_Enable     = true; // Habilitar bonus Keltner

//--- Padroes de vela
input bool   Engulf_Enable      = true; // Habilitar bonus Engolfo/Pinca

//--- Filtros de regime
input bool   Enable_Regime_Filter = true; // Habilitar filtros de regime
input int    Max_Regime_Failures  = 1;    // Maximo de filtros falhando (3-de-4)

input double ATR_Min_Ratio_M5  = 0.000020; // ATR/close minimo M5
input double ATR_Min_Ratio_M15 = 0.000060; // ATR/close minimo M15
input int    ATR_Period        = 14;        // Periodo ATR

input double ADX_Min_M5        = 9.0;  // ADX minimo M5
input double ADX_Min_M15       = 11.0; // ADX minimo M15
input int    ADX_Period        = 14;   // Periodo ADX

input double BBW_Min_M5        = 0.00050; // Largura BB minima M5
input double BBW_Min_M15       = 0.00110; // Largura BB minima M15

input double Slope_Min_M5      = 0.000050; // Slope EMA minimo M5
input double Slope_Min_M15     = 0.000120; // Slope EMA minimo M15
input int    Slope_EMA_Period  = 21;       // Periodo EMA slope
input int    Slope_Lookback    = 8;        // Janela de lookback slope

//--- Filtros estruturais
input bool   Enable_Structural_Filter = true; // Habilitar filtros estruturais
input int    M5_Extreme_Candles       = 20;   // Janela filtro extremo M5
input double M5_Extreme_Frac          = 0.20; // Fracao extremo M5 (20%)
input int    M15_Structural_Candles   = 5;    // Janela filtro estrutural M15

//--- Cooldown anti-cluster
input int    Cooldown_Bars_M5  = 6; // Barras de cooldown apos sinal confirmado M5
input int    Cooldown_Bars_M15 = 3; // Barras de cooldown apos sinal confirmado M15

//--- Fallback padroes classicos
input int    V15_Fallback_Near_Score = 50;   // Score minimo para fallback M15
input bool   Fallback_Enable         = true; // Habilitar fallback de padroes

// =======================================================================
// VARIAVEIS GLOBAIS
// =======================================================================
int g_tf = 0;

// =======================================================================
// OnStart - Ponto de entrada do script
// =======================================================================
void OnStart()
  {
   g_tf = (int)Period();
   if(g_tf != 5 && g_tf != 15)
     {
      Alert("Catalogador V15: Execute em grafico M5 ou M15!");
      return;
     }

   // Cria pasta Catalogador_V15 se nao existir
   if(!FolderCreate("Catalogador_V15", 0))
     {
      // FolderCreate retorna false se ja existir — nao e erro
      // Print apenas se for falha real (diferente de "ja existe")
     }

   // Calcula barra de inicio (Catalog_Days dias atras)
   datetime dtStart = TimeCurrent() - (datetime)(Catalog_Days * 86400);
   int startBar = iBarShift(NULL, 0, dtStart, false);
   if(startBar < 0) startBar = Bars - 1;
   if(startBar >= Bars - 1) startBar = Bars - 2;

   // Nome do CSV de saida
   string tfStr   = IntegerToString(g_tf);
   string symStr  = Symbol();
   string csvPath = "Catalogador_V15\\Catalogo_" + symStr + "_" + tfStr + "m.csv";

   // Abre o arquivo CSV (sobrescreve sempre)
   int fh = FileOpen(csvPath, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(fh == INVALID_HANDLE)
     {
      Alert("Catalogador V15: Erro ao criar CSV: " + csvPath);
      return;
     }

   // Cabecalho do CSV
   FileWriteString(fh,
      "data,horario,symbol,timeframe,direction,score,pattern,status,"
      "preco_entrada,preco_expiracao,variacao_pips,direcao_vela,resultado,tipo_loss\n");

   // Contadores
   int totalSignals   = 0;
   int totalConfirmed = 0;
   int totalRejected  = 0;
   int totalWin       = 0;
   int totalLoss      = 0;

   // Cooldown: indice da ultima barra com sinal confirmado
   int lastConfirmBar = -9999;

   // Varre da barra mais antiga para a mais recente
   // bar=startBar e a mais antiga, bar=2 e a mais recente com vela seguinte disponivel
   for(int bar = startBar; bar >= 2; bar--)
     {
      // Filtro de horario: Hour >= Hour_Start && (Hour < Hour_End || (Hour == Hour_End && Minute <= Minute_End))
      int bHour   = (int)TimeHour(Time[bar]);
      int bMinute = (int)TimeMinute(Time[bar]);
      bool inWindow = (bHour >= Hour_Start) &&
                      (bHour < Hour_End || (bHour == Hour_End && bMinute <= Minute_End));
      if(!inWindow) continue;

      // Cooldown: pula se ainda dentro do cooldown apos ultimo sinal confirmado
      int cooldown = (g_tf == 5) ? Cooldown_Bars_M5 : Cooldown_Bars_M15;
      if(lastConfirmBar > 0 && (lastConfirmBar - bar) < cooldown) continue;

      // Calcula score V15
      int callScore, putScore, callComp, putComp;
      int rsiPts, bbPts, wickPts, impPts, kelPts, engPts;
      int rsiDir, bbDir, wickDir, impDir, kelDir, engDir;
      CalcV15Score(bar,
                   callScore, putScore, callComp, putComp,
                   rsiPts, rsiDir, bbPts, bbDir,
                   wickPts, wickDir, impPts, impDir,
                   kelPts, kelDir, engPts, engDir);

      // Filtros de regime
      bool atrOk, adxOk, bbwOk, slopeOk;
      int regFails = CalcRegimeFails(bar, atrOk, adxOk, bbwOk, slopeOk);
      bool regimeOk = !Enable_Regime_Filter || (regFails <= Max_Regime_Failures);

      int scoreMin = (g_tf == 5) ? V15_Score_Min_M5 : V15_Score_Min_M15;

      // Determina direcao e padrao do sinal
      int    dir     = 0;
      string pattern = "";
      int    sigScore = 0;

      if(callScore >= scoreMin &&
         (callScore - putScore) >= V15_Gap_Min &&
         callComp >= Min_Components && regimeOk &&
         CheckStructuralFilter(bar, 1))
        {
         dir      = 1;
         pattern  = "ReversalV15_CALL";
         sigScore = callScore;
        }
      else if(putScore >= scoreMin &&
              (putScore - callScore) >= V15_Gap_Min &&
              putComp >= Min_Components && regimeOk &&
              CheckStructuralFilter(bar, -1))
        {
         dir      = -1;
         pattern  = "ReversalV15_PUT";
         sigScore = putScore;
        }
      else if(Fallback_Enable && regimeOk)
        {
         int bestScore = (callScore > putScore) ? callScore : putScore;
         bool fbOk = (g_tf != 15) || (bestScore >= V15_Fallback_Near_Score);
         if(fbOk)
           {
            string fbPat = "";
            int fbDir = CheckFallbackPatterns(bar, fbPat);
            if(fbDir != 0 && CheckStructuralFilter(bar, fbDir))
              {
               dir      = fbDir;
               pattern  = fbPat;
               sigScore = (fbDir == 1) ? callScore : putScore;
              }
           }
        }

      if(dir == 0) continue;

      totalSignals++;

      // Simulacao de confirmacao: Open[bar-1] vs Close[bar]
      bool confirmed = (dir == 1) ? (Open[bar-1] > Close[bar])
                                  : (Open[bar-1] < Close[bar]);

      // Data e horario da vela de sinal
      string dataPart = TimeToString(Time[bar], TIME_DATE);
      string horaPart = TimeToString(Time[bar], TIME_MINUTES);
      // TimeToString TIME_DATE retorna "YYYY.MM.DD", TIME_MINUTES retorna "HH:MM"
      // Separar apenas hora:minuto (TIME_MINUTES inclui data+hora, pegar o horario)
      // Usa TIME_SECONDS para obter apenas o horario depois de separar
      string fullTs = TimeToString(Time[bar], TIME_DATE|TIME_SECONDS);
      string tsParts[];
      int partCnt = StringSplit(fullTs, ' ', tsParts);
      dataPart = (partCnt >= 1) ? tsParts[0] : dataPart;
      horaPart = (partCnt >= 2) ? StringSubstr(tsParts[1], 0, 5) : horaPart;

      string dirStr = (dir == 1) ? "CALL" : "PUT";

      if(!confirmed)
        {
         totalRejected++;
         // Linha REJECTED: campos de resultado vazios
         string line = StringFormat(
            "%s,%s,%s,%dm,%s,%d,%s,REJECTED,,,,,,\n",
            dataPart, horaPart, symStr, g_tf, dirStr, sigScore, pattern);
         FileWriteString(fh, line);
         continue;
        }

      // CONFIRMED - calcula resultado
      totalConfirmed++;
      lastConfirmBar = bar;

      double entryPrice  = Open[bar-1];
      double exitPrice   = Close[bar-1];
      double varPips     = (exitPrice - entryPrice) / Point;

      // Direcao da vela de expiracao
      string velaDir = (Close[bar-1] >= Open[bar-1]) ? "BULLISH" : "BEARISH";

      // Resultado WIN/LOSS
      bool isWin = false;
      if(dir == 1)  isWin = (exitPrice > entryPrice);
      else          isWin = (exitPrice < entryPrice);

      string resultado = isWin ? "WIN" : "LOSS";
      string tipoLoss  = "";

      if(!isWin)
        {
         totalLoss++;
         double absVar = MathAbs(varPips);
         if(absVar < 1.0)
           {
            tipoLoss = "MARGEM";
           }
         else
           {
            // Vela foi na direcao do sinal mas close nao favoreceu?
            bool velaFavoravel = (dir == 1 && Close[bar-1] > Open[bar-1]) ||
                                 (dir == -1 && Close[bar-1] < Open[bar-1]);
            if(velaFavoravel)
               tipoLoss = "TIMING";
            else if(absVar > 3.0)
               tipoLoss = "REVERSAO";
            else
               tipoLoss = "TIMING";
           }
        }
      else
        {
         totalWin++;
        }

      // Formata variacao com sinal
      string varStr = StringFormat("%+.1f", varPips);

      string entryStr = StringFormat("%." + IntegerToString(Digits) + "f", entryPrice);
      string exitStr  = StringFormat("%." + IntegerToString(Digits) + "f", exitPrice);

      string line = StringFormat(
         "%s,%s,%s,%dm,%s,%d,%s,CONFIRMED,%s,%s,%s,%s,%s,%s\n",
         dataPart, horaPart, symStr, g_tf, dirStr, sigScore, pattern,
         entryStr, exitStr, varStr, velaDir, resultado, tipoLoss);
      FileWriteString(fh, line);
     }

   FileClose(fh);

   // Monta resumo para Alert
   double winrate = 0.0;
   if(totalConfirmed > 0)
      winrate = (double)totalWin / (double)totalConfirmed * 100.0;

   string hourStartStr = StringFormat("%02d:00", Hour_Start);
   string hourEndStr   = StringFormat("%02d:%02d", Hour_End, Minute_End);

   string msg = StringFormat(
      "Catalogador V15 — %s M%d\n"
      "Periodo: %d dias | Horario: %s~%s\n"
      "Total sinais: %d | CONFIRMED: %d | REJECTED: %d\n"
      "WIN: %d | LOSS: %d | Winrate: %.1f%%\n"
      "CSV salvo em: %s",
      symStr, g_tf,
      Catalog_Days, hourStartStr, hourEndStr,
      totalSignals, totalConfirmed, totalRejected,
      totalWin, totalLoss, winrate,
      csvPath);

   Alert(msg);
   Print("Catalogador V15: " + msg);
  }

// =======================================================================
// CalcV15Score - Calcula o score composto V15 (identico ao indicador)
// =======================================================================
void CalcV15Score(int bar,
                  int &callScore, int &putScore,
                  int &callComp,  int &putComp,
                  int &rsiPts,  int &rsiDir,
                  int &bbPts,   int &bbDir,
                  int &wickPts, int &wickDir,
                  int &impPts,  int &impDir,
                  int &kelPts,  int &kelDir,
                  int &engPts,  int &engDir)
  {
   callScore = 0; putScore = 0; callComp = 0; putComp = 0;

   CalcRSIScore(bar,    rsiPts,  rsiDir);
   CalcBBScore(bar,     bbPts,   bbDir);
   CalcWickScore(bar,   wickPts, wickDir);
   CalcImpulseScore(bar,impPts,  impDir);
   CalcKeltnerScore(bar,kelPts,  kelDir);
   CalcEngulfScore(bar, engPts,  engDir);

   if(rsiDir ==  1) { callScore += rsiPts;  if(rsiPts  > 0) callComp++; }
   if(rsiDir == -1) { putScore  += rsiPts;  if(rsiPts  > 0) putComp++;  }
   if(bbDir  ==  1) { callScore += bbPts;   if(bbPts   > 0) callComp++; }
   if(bbDir  == -1) { putScore  += bbPts;   if(bbPts   > 0) putComp++;  }
   if(wickDir== 1)  { callScore += wickPts; if(wickPts > 0) callComp++; }
   if(wickDir==-1)  { putScore  += wickPts; if(wickPts > 0) putComp++;  }
   if(impDir == 1)  { callScore += impPts;  if(impPts  > 0) callComp++; }
   if(impDir ==-1)  { putScore  += impPts;  if(impPts  > 0) putComp++;  }
   if(kelDir == 1)  { callScore += kelPts;  if(kelPts  > 0) callComp++; }
   if(kelDir ==-1)  { putScore  += kelPts;  if(kelPts  > 0) putComp++;  }
   if(engDir == 1)  { callScore += engPts;  if(engPts  > 0) callComp++; }
   if(engDir ==-1)  { putScore  += engPts;  if(engPts  > 0) putComp++;  }
  }

// =======================================================================
// FUNCOES DE SCORE V15 (copiadas de BOTDINVELAS_V15.mq4)
// =======================================================================

// Componente 1: RSI (0-25 pts)
void CalcRSIScore(int bar, int &pts, int &dir)
  {
   pts = 0; dir = 0;
   if(!RSI_Enable) return;
   double rsi = iRSI(NULL, 0, RSI_Period, PRICE_CLOSE, bar);
   if(rsi <= RSI_Oversold)              { pts=25; dir= 1; }
   else if(rsi <= RSI_Oversold + 10)   { pts=12; dir= 1; }
   else if(rsi >= RSI_Overbought)       { pts=25; dir=-1; }
   else if(rsi >= RSI_Overbought - 10) { pts=12; dir=-1; }
  }

// Componente 2: Bollinger Bands (0-25 pts)
void CalcBBScore(int bar, int &pts, int &dir)
  {
   pts = 0; dir = 0;
   if(!BB_Enable) return;
   double upper  = iBands(NULL,0,BB_Period,BB_StdDev,0,PRICE_CLOSE,MODE_UPPER,bar);
   double lower  = iBands(NULL,0,BB_Period,BB_StdDev,0,PRICE_CLOSE,MODE_LOWER,bar);
   if(upper==0 && lower==0) return;
   double price     = Close[bar];
   double bandWidth = MathMax(upper - lower, 1e-12);
   double proxThr   = bandWidth * BB_Proximity;
   double distLower = price - lower;
   double distUpper = upper - price;
   if(distLower < 0)
     { pts=25; dir=1; }
   else if(distLower <= proxThr)
     { double f=MathMax(0.0,1.0-distLower/MathMax(proxThr,1e-12)); pts=(int)(f*25); dir=1; }
   else if(distUpper < 0)
     { pts=25; dir=-1; }
   else if(distUpper <= proxThr)
     { double f=MathMax(0.0,1.0-distUpper/MathMax(proxThr,1e-12)); pts=(int)(f*25); dir=-1; }
  }

// Componente 3: Wick / Sombra (0-25 pts)
void CalcWickScore(int bar, int &pts, int &dir)
  {
   pts = 0; dir = 0;
   if(!Wick_Enable) return;
   double o=Open[bar], c=Close[bar], h=High[bar], l=Low[bar];
   double rng        = MathMax(h-l, 1e-12);
   double lowerWick  = MathMin(o,c) - l;
   double upperWick  = h - MathMax(o,c);
   double lowerRatio = lowerWick / rng;
   double upperRatio = upperWick / rng;
   if(lowerRatio >= Wick_Min_Ratio && lowerRatio > upperRatio)
     { pts=(int)MathMin((double)Wick_Score_Max, lowerRatio*Wick_Score_Factor); dir=1;  }
   else if(upperRatio >= Wick_Min_Ratio && upperRatio > lowerRatio)
     { pts=(int)MathMin((double)Wick_Score_Max, upperRatio*Wick_Score_Factor); dir=-1; }
  }

// Componente 4: Impulso + Contexto (0-25 pts)
void CalcImpulseScore(int bar, int &pts, int &dir)
  {
   pts = 0; dir = 0;
   if(!Impulse_Enable) return;
   int totalBars = iBars(NULL, 0);
   if(bar + Impulse_Lookback + Context_Lookback + 5 >= totalBars) return;

   double cNow  = Close[bar];
   double cPast = Close[bar + Impulse_Lookback];
   if(MathAbs(cPast) < 1e-10) return;
   double impulse = (cNow - cPast) / MathAbs(cPast);

   int lb   = Context_Lookback;
   int half = lb / 2;
   if(half == 0) return;
   double sumOld=0.0, sumNew=0.0;
   for(int k=bar+half+1; k<=bar+lb    && k<totalBars; k++) sumOld += Close[k];
   for(int k=bar+1;      k<=bar+half  && k<totalBars; k++) sumNew += Close[k];
   double firstAvg  = sumOld / (lb - half);
   double secondAvg = sumNew / half;
   if(MathAbs(firstAvg) < 1e-10) return;
   double change = (secondAvg - firstAvg) / MathAbs(firstAvg);

   string ctx = "sideways";
   if(change < -Trend_Threshold)    ctx = "downtrend";
   else if(change > Trend_Threshold) ctx = "uptrend";

   if(ctx=="downtrend" && impulse < -Impulse_Threshold)
     { pts=(int)MathMin(25.0, MathAbs(impulse)*Impulse_Multiplier); dir=1;  }
   else if(ctx=="uptrend" && impulse > Impulse_Threshold)
     { pts=(int)MathMin(25.0, MathAbs(impulse)*Impulse_Multiplier); dir=-1; }
  }

// Componente 5: Canal Keltner (0-20 pts)
void CalcKeltnerScore(int bar, int &pts, int &dir)
  {
   pts = 0; dir = 0;
   if(!Keltner_Enable) return;
   double kMid    = iMA(NULL, 0, Keltner_Period, 0, MODE_EMA, PRICE_TYPICAL, bar);
   double kOffset = iATR(NULL, 0, Keltner_Period, bar) * Keltner_Shift_Mult;
   if(kMid==0 || kOffset==0) return;
   double kUpper    = kMid + kOffset;
   double kLower    = kMid - kOffset;
   double price     = Close[bar];
   double bandWidth = MathMax(kUpper-kLower, 1e-12);
   double prox      = bandWidth * 0.25;
   double distLower = price - kLower;
   double distUpper = kUpper - price;
   if(distLower < 0)
     { pts=20; dir=1; }
   else if(distLower <= prox)
     { double f=MathMax(0.0,1.0-distLower/MathMax(prox,1e-12)); pts=(int)(f*20); dir=1; }
   else if(distUpper < 0)
     { pts=20; dir=-1; }
   else if(distUpper <= prox)
     { double f=MathMax(0.0,1.0-distUpper/MathMax(prox,1e-12)); pts=(int)(f*20); dir=-1; }
  }

// Componente 6: Engolfo e Pinca (0-20 pts)
void CalcEngulfScore(int bar, int &pts, int &dir)
  {
   pts = 0; dir = 0;
   if(!Engulf_Enable) return;
   if(bar+1 >= iBars(NULL, 0)) return;
   if(IsEngulfingBullish(bar))      { pts=20; dir=1;  }
   else if(IsEngulfingBearish(bar)) { pts=20; dir=-1; }
   else if(IsTweezerBottom(bar))    { pts=12; dir=1;  }
   else if(IsTweezerTop(bar))       { pts=12; dir=-1; }
  }

// =======================================================================
// FILTROS DE REGIME
// =======================================================================

int CalcRegimeFails(int bar, bool &atrOk, bool &adxOk, bool &bbwOk, bool &slopeOk)
  {
   atrOk   = CheckATRFilter(bar);
   adxOk   = CheckADXFilter(bar);
   bbwOk   = CheckBBWidthFilter(bar);
   slopeOk = CheckSlopeFilter(bar);
   int f = 0;
   if(!atrOk)   f++;
   if(!adxOk)   f++;
   if(!bbwOk)   f++;
   if(!slopeOk) f++;
   return(f);
  }

bool CheckATRFilter(int bar)
  {
   double atr = iATR(NULL, 0, ATR_Period, bar);
   if(atr <= 0) return(false);
   double sumC = 0.0;
   int total = iBars(NULL, 0);
   for(int k=bar; k<bar+ATR_Period && k<total; k++) sumC += Close[k];
   double meanClose = sumC / ATR_Period;
   if(meanClose < 1e-10) return(false);
   double atrMin = (g_tf==5) ? ATR_Min_Ratio_M5 : ATR_Min_Ratio_M15;
   return(atr / meanClose >= atrMin);
  }

bool CheckADXFilter(int bar)
  {
   double adx    = iADX(NULL, 0, ADX_Period, PRICE_CLOSE, MODE_MAIN, bar);
   double adxMin = (g_tf==5) ? ADX_Min_M5 : ADX_Min_M15;
   return(adx >= adxMin);
  }

bool CheckBBWidthFilter(int bar)
  {
   double upper  = iBands(NULL,0,BB_Period,BB_StdDev,0,PRICE_CLOSE,MODE_UPPER,bar);
   double lower  = iBands(NULL,0,BB_Period,BB_StdDev,0,PRICE_CLOSE,MODE_LOWER,bar);
   double middle = iBands(NULL,0,BB_Period,BB_StdDev,0,PRICE_CLOSE,MODE_MAIN, bar);
   if(middle < 1e-10) return(false);
   double bbwMin = (g_tf==5) ? BBW_Min_M5 : BBW_Min_M15;
   return((upper-lower)/middle >= bbwMin);
  }

bool CheckSlopeFilter(int bar)
  {
   double ema1 = iMA(NULL,0,Slope_EMA_Period,0,MODE_EMA,PRICE_CLOSE,bar);
   double ema2 = iMA(NULL,0,Slope_EMA_Period,0,MODE_EMA,PRICE_CLOSE,bar+Slope_Lookback);
   if(ema1==0 || ema2==0) return(false);
   double slope    = MathAbs(ema1-ema2) / MathMax(Close[bar], 1e-10);
   double slopeMin = (g_tf==5) ? Slope_Min_M5 : Slope_Min_M15;
   return(slope >= slopeMin);
  }

// =======================================================================
// FILTROS ESTRUTURAIS
// =======================================================================

bool CheckStructuralFilter(int bar, int dir)
  {
   if(!Enable_Structural_Filter) return(true);
   if(g_tf == 5)  return(CheckM5ExtremeFilter(bar, dir));
   if(g_tf == 15) return(CheckM15StructuralFilter(bar, dir));
   return(true);
  }

bool CheckM5ExtremeFilter(int bar, int dir)
  {
   int total = iBars(NULL, 0);
   if(bar + M5_Extreme_Candles + 1 >= total) return(true);
   double rHigh=-DBL_MAX, rLow=DBL_MAX;
   for(int k=bar; k<=bar+M5_Extreme_Candles; k++)
     {
      if(High[k] > rHigh) rHigh = High[k];
      if(Low[k]  < rLow)  rLow  = Low[k];
     }
   double rng = rHigh - rLow;
   if(rng < 1e-10) return(true);
   double thr = rng * M5_Extreme_Frac;
   double c   = Close[bar];
   if(dir ==  1) return(c <= rLow  + thr);
   if(dir == -1) return(c >= rHigh - thr);
   return(true);
  }

bool CheckM15StructuralFilter(int bar, int dir)
  {
   int total = iBars(NULL, 0);
   if(bar + M15_Structural_Candles >= total) return(true);
   double hi=-DBL_MAX, lo=DBL_MAX;
   for(int k=bar; k<=bar+M15_Structural_Candles-1; k++)
     {
      if(Close[k] > hi) hi = Close[k];
      if(Close[k] < lo) lo = Close[k];
     }
   double rng = hi - lo;
   if(rng < 1e-10) return(true);
   double third = rng / 3.0;
   double c     = Close[bar];
   if(dir ==  1) return(c <= lo + third);
   if(dir == -1) return(c >= hi - third);
   return(true);
  }

// =======================================================================
// DETECCAO DE PADROES DE VELA
// =======================================================================

bool IsEngulfingBullish(int bar)
  {
   if(bar+1 >= iBars(NULL,0)) return(false);
   double o0=Open[bar+1], c0=Close[bar+1];
   double o1=Open[bar],   c1=Close[bar];
   if(!(c0<o0)) return(false);
   if(!(c1>o1)) return(false);
   if(!(o1<=c0 && c1>=o0)) return(false);
   return(MathAbs(c1-o1) > MathAbs(c0-o0)*0.9);
  }

bool IsEngulfingBearish(int bar)
  {
   if(bar+1 >= iBars(NULL,0)) return(false);
   double o0=Open[bar+1], c0=Close[bar+1];
   double o1=Open[bar],   c1=Close[bar];
   if(!(c0>o0)) return(false);
   if(!(c1<o1)) return(false);
   if(!(o1>=c0 && c1<=o0)) return(false);
   return(MathAbs(c1-o1) > MathAbs(c0-o0)*0.9);
  }

bool IsTweezerBottom(int bar)
  {
   if(bar+1 >= iBars(NULL,0)) return(false);
   double l0=Low[bar+1], l1=Low[bar];
   double avg=(l0+l1)/2.0;
   if(avg<1e-10) return(false);
   if(MathAbs(l0-l1)/avg > 0.001) return(false);
   return(Close[bar+1]<Open[bar+1] && Close[bar]>Open[bar]);
  }

bool IsTweezerTop(int bar)
  {
   if(bar+1 >= iBars(NULL,0)) return(false);
   double h0=High[bar+1], h1=High[bar];
   double avg=(h0+h1)/2.0;
   if(avg<1e-10) return(false);
   if(MathAbs(h0-h1)/avg > 0.001) return(false);
   return(Close[bar+1]>Open[bar+1] && Close[bar]<Open[bar]);
  }

bool IsHaramiBearish(int bar)
  {
   if(bar+1 >= iBars(NULL,0)) return(false);
   double o0=Open[bar+1],c0=Close[bar+1];
   double o1=Open[bar],  c1=Close[bar];
   if(!(c0>o0 && c1<o1)) return(false);
   double hi0=MathMax(o0,c0), lo0=MathMin(o0,c0);
   double hi1=MathMax(o1,c1), lo1=MathMin(o1,c1);
   if(!(hi1<=hi0 && lo1>=lo0)) return(false);
   return(MathAbs(c1-o1) < 0.8*MathAbs(c0-o0));
  }

bool IsHaramiBullish(int bar)
  {
   if(bar+1 >= iBars(NULL,0)) return(false);
   double o0=Open[bar+1],c0=Close[bar+1];
   double o1=Open[bar],  c1=Close[bar];
   if(!(c0<o0 && c1>o1)) return(false);
   double hi0=MathMax(o0,c0), lo0=MathMin(o0,c0);
   double hi1=MathMax(o1,c1), lo1=MathMin(o1,c1);
   if(!(hi1<=hi0 && lo1>=lo0)) return(false);
   return(MathAbs(c1-o1) < 0.8*MathAbs(c0-o0));
  }

bool IsHammer(int bar)
  {
   double o=Open[bar],c=Close[bar],h=High[bar],l=Low[bar];
   double body  = MathAbs(c-o);
   double rng   = MathMax(h-l, 1e-12);
   double upper = h - MathMax(o,c);
   double lower = MathMin(o,c) - l;
   if(body/rng > 0.35)                   return(false);
   if(lower < 2.0*MathMax(body,1e-12))  return(false);
   if(upper > 0.8*MathMax(body,1e-12))  return(false);
   return(true);
  }

int CheckFallbackPatterns(int bar, string &patName)
  {
   patName = "";
   if(IsHaramiBearish(bar))    { patName="HaramiBearish";  return(-1); }
   if(IsEngulfingBearish(bar)) { patName="EngolfoBearish"; return(-1); }
   if(IsTweezerTop(bar))       { patName="TweezerTop";     return(-1); }
   if(IsHaramiBullish(bar))    { patName="HaramiBullish";  return( 1); }
   if(IsEngulfingBullish(bar)) { patName="EngolfoBullish"; return( 1); }
   if(IsTweezerBottom(bar))    { patName="TweezerBottom";  return( 1); }
   if(IsHammer(bar))           { patName="Hammer";         return( 1); }
   return(0);
  }
