export type SupportedChartTypes = 
  | "Candlestick"
  | "OHLC"
  | "Area"
  | "Baseline"
  | "Renko"
  | "Kagi"
  | "Point and Figure"
  | "Volume Profile"
  | "Market Profile"
  | "Heikin Ashi";
  
export interface ChartConfig {
    type: SupportedChartTypes;
    data: any[];
}

