/**
 * Chart visualization registry.
 * Every chart mode declares its data requirements honestly.
 * Modes that require unavailable data show an explanation, never fake rendering.
 */

export type ChartCategory =
  | "native"
  | "derived-price"
  | "volume-orderflow"
  | "options"
  | "quant-risk"
  | "forecast";

export type DataRequirement =
  | "ohlcv"
  | "orderbook"
  | "tick-data"
  | "options-chain"
  | "multi-asset"
  | "prediction-model";

export interface ChartDefinition {
  id: string;
  name: string;
  category: ChartCategory;
  requiredData: DataRequirement[];
  description: string;
  implemented: boolean;
  unavailableReason?: string;
}

export const CHART_REGISTRY: ChartDefinition[] = [
  // NATIVE PRICE (7)
  { id: "candlestick", name: "Candlestick", category: "native", requiredData: ["ohlcv"], description: "Standard OHLC candlestick chart", implemented: true },
  { id: "hollow-candlestick", name: "Hollow Candlestick", category: "native", requiredData: ["ohlcv"], description: "Hollow body for up candles, filled for down", implemented: true },
  { id: "ohlc-bar", name: "OHLC Bar", category: "native", requiredData: ["ohlcv"], description: "Traditional bar chart with OHLC ticks", implemented: true },
  { id: "line", name: "Line", category: "native", requiredData: ["ohlcv"], description: "Closing price line chart", implemented: true },
  { id: "area", name: "Area", category: "native", requiredData: ["ohlcv"], description: "Filled area under closing price", implemented: true },
  { id: "baseline", name: "Baseline", category: "native", requiredData: ["ohlcv"], description: "Above/below baseline coloring", implemented: true },
  { id: "volume", name: "Volume Bars", category: "native", requiredData: ["ohlcv"], description: "Volume histogram bars", implemented: true },

  // DERIVED PRICE (10)
  { id: "heikin-ashi", name: "Heikin-Ashi", category: "derived-price", requiredData: ["ohlcv"], description: "Smoothed trend candles", implemented: true },
  { id: "renko", name: "Renko", category: "derived-price", requiredData: ["ohlcv"], description: "Fixed brick-size price movement", implemented: true },
  { id: "kagi", name: "Kagi", category: "derived-price", requiredData: ["ohlcv"], description: "Directional reversal chart", implemented: true },
  { id: "point-figure", name: "Point & Figure", category: "derived-price", requiredData: ["ohlcv"], description: "X/O price movement without time axis", implemented: true },
  { id: "range-bar", name: "Range Bars", category: "derived-price", requiredData: ["ohlcv"], description: "Fixed price range per bar", implemented: true },
  { id: "three-line-break", name: "Three-Line Break", category: "derived-price", requiredData: ["ohlcv"], description: "Filters insignificant moves", implemented: true },
  { id: "equivolume", name: "Equivolume", category: "derived-price", requiredData: ["ohlcv"], description: "Bar width proportional to volume", implemented: true },
  { id: "relative-strength", name: "Relative Performance", category: "derived-price", requiredData: ["ohlcv"], description: "Performance vs benchmark", implemented: true },
  { id: "spread", name: "Spread Chart", category: "derived-price", requiredData: ["ohlcv"], description: "Price differential analysis", implemented: true },
  { id: "mountain", name: "Mountain", category: "derived-price", requiredData: ["ohlcv"], description: "Gradient-filled close price", implemented: true },

  // VOLUME / ORDER FLOW (10)
  { id: "vwap", name: "VWAP", category: "volume-orderflow", requiredData: ["ohlcv"], description: "Volume-weighted average price overlay", implemented: true },
  { id: "anchored-vwap", name: "Anchored VWAP", category: "volume-orderflow", requiredData: ["ohlcv"], description: "VWAP from a selected anchor point", implemented: true },
  { id: "volume-profile", name: "Volume Profile", category: "volume-orderflow", requiredData: ["ohlcv"], description: "Volume distributed across price levels", implemented: true },
  { id: "market-profile", name: "Market Profile / TPO", category: "volume-orderflow", requiredData: ["ohlcv"], description: "Time-price opportunity distribution", implemented: true },
  { id: "cvd", name: "Cumulative Volume Delta", category: "volume-orderflow", requiredData: ["ohlcv"], description: "Estimated buying vs selling pressure from OHLCV", implemented: true },
  { id: "orderbook-depth", name: "Order Book Depth", category: "volume-orderflow", requiredData: ["orderbook"], description: "Bid/ask liquidity depth", implemented: false, unavailableReason: "Requires real-time Level 2 order book data feed" },
  { id: "bid-ask-spread", name: "Bid-Ask Spread", category: "volume-orderflow", requiredData: ["orderbook"], description: "Spread over time", implemented: false, unavailableReason: "Requires real-time bid/ask tick data" },
  { id: "footprint", name: "Footprint Chart", category: "volume-orderflow", requiredData: ["tick-data"], description: "Volume at each price level within a bar", implemented: false, unavailableReason: "Requires tick-level trade data" },
  { id: "tick", name: "Tick Chart", category: "volume-orderflow", requiredData: ["ohlcv"], description: "Individual price ticks", implemented: true },
  { id: "orderflow-imbalance", name: "Order-Flow Imbalance", category: "volume-orderflow", requiredData: ["tick-data"], description: "Aggressive buy/sell imbalance", implemented: false, unavailableReason: "Requires tick-level trade data with aggressor flag" },

  // OPTIONS (10)
  { id: "open-interest", name: "Open Interest", category: "options", requiredData: ["options-chain"], description: "Real exchange open interest data", implemented: false, unavailableReason: "Requires real exchange OI data feed — cannot be manufactured from OHLCV" },
  { id: "change-in-oi", name: "Change in OI", category: "options", requiredData: ["options-chain"], description: "Day-over-day open interest change", implemented: false, unavailableReason: "Requires real options chain data with daily OI snapshots" },
  { id: "oi-price", name: "OI + Price", category: "options", requiredData: ["options-chain"], description: "Price with real OI overlay", implemented: false, unavailableReason: "Requires real exchange OI data feed" },
  { id: "put-call-ratio", name: "Put-Call Ratio", category: "options", requiredData: ["options-chain"], description: "Real put-call ratio from options chain", implemented: false, unavailableReason: "Requires real options chain data — cannot be estimated from price" },
  { id: "max-pain", name: "Max Pain", category: "options", requiredData: ["options-chain"], description: "Strike with maximum option seller profit", implemented: false, unavailableReason: "Requires real options chain with OI per strike" },
  { id: "iv-smile", name: "IV Smile / Skew", category: "options", requiredData: ["options-chain"], description: "Implied volatility across strikes", implemented: false, unavailableReason: "Requires real options chain with IV per strike" },
  { id: "iv-surface", name: "IV Surface", category: "options", requiredData: ["options-chain"], description: "3D implied volatility surface", implemented: false, unavailableReason: "Requires real options chain across strikes and expiries" },
  { id: "greeks-matrix", name: "Greeks Matrix", category: "options", requiredData: ["options-chain"], description: "Delta, Gamma, Theta, Vega surface", implemented: false, unavailableReason: "Requires real options chain with computed Greeks" },
  { id: "vol-term-structure", name: "Volatility Term Structure", category: "options", requiredData: ["options-chain"], description: "IV across expiry dates", implemented: false, unavailableReason: "Requires real options chain across expiries" },
  { id: "volatility-cone", name: "Volatility Cone", category: "quant-risk", requiredData: ["ohlcv"], description: "Historical volatility percentiles across windows", implemented: true },

  // QUANT / RISK (9)
  { id: "correlation-heatmap", name: "Correlation Heatmap", category: "quant-risk", requiredData: ["multi-asset"], description: "Cross-asset correlation matrix", implemented: false, unavailableReason: "Requires multi-asset price data loaded simultaneously" },
  { id: "rolling-correlation", name: "Rolling Correlation", category: "quant-risk", requiredData: ["multi-asset"], description: "Time-varying correlation with benchmark", implemented: false, unavailableReason: "Requires benchmark data loaded simultaneously" },
  { id: "covariance-heatmap", name: "Covariance Heatmap", category: "quant-risk", requiredData: ["multi-asset"], description: "Cross-asset covariance matrix", implemented: false, unavailableReason: "Requires multi-asset price data loaded simultaneously" },
  { id: "returns-distribution", name: "Return Distribution", category: "quant-risk", requiredData: ["ohlcv"], description: "Histogram of daily returns", implemented: true },
  { id: "histogram-returns", name: "Returns Histogram", category: "quant-risk", requiredData: ["ohlcv"], description: "Frequency distribution of returns", implemented: true },
  { id: "rolling-volatility", name: "Rolling Volatility", category: "quant-risk", requiredData: ["ohlcv"], description: "21-day annualized volatility", implemented: true },
  { id: "drawdown", name: "Drawdown", category: "quant-risk", requiredData: ["ohlcv"], description: "Peak-to-trough loss percentage", implemented: true },
  { id: "rolling-sharpe", name: "Rolling Sharpe", category: "quant-risk", requiredData: ["ohlcv"], description: "63-day rolling Sharpe ratio", implemented: true },
  { id: "rolling-beta", name: "Rolling Beta / Factor Exposure", category: "quant-risk", requiredData: ["ohlcv"], description: "Rolling market sensitivity", implemented: true },

  // FORECAST (3)
  { id: "fibonacci", name: "Fibonacci Retracement", category: "forecast", requiredData: ["ohlcv"], description: "Key retracement levels from swing high/low", implemented: true },
  { id: "pivot-points", name: "Pivot Points", category: "forecast", requiredData: ["ohlcv"], description: "Classic pivot support/resistance levels", implemented: true },
  { id: "ichimoku-standalone", name: "Ichimoku Cloud", category: "forecast", requiredData: ["ohlcv"], description: "Full Ichimoku Kinko Hyo system", implemented: true },
];

export const IMPLEMENTED_CHARTS = CHART_REGISTRY.filter((c) => c.implemented);
export const UNAVAILABLE_CHARTS = CHART_REGISTRY.filter((c) => !c.implemented);

export function getChartDefinition(id: string): ChartDefinition | undefined {
  return CHART_REGISTRY.find((c) => c.id === id);
}

export function getChartsByCategory(category: ChartCategory): ChartDefinition[] {
  return CHART_REGISTRY.filter((c) => c.category === category);
}
