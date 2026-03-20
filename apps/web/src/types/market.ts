/**
 * Market data types - Complete TypeScript types for all market entities
 * Based on prompt.txt SECTION 8: WEBSOCKET ARCHITECTURE
 */

export interface TickData {
  symbol: string;
  price: number;
  volume: number;
  changePct: number;
  timestamp: number;
  high52Week: number;
  low52Week: number;
  marketCap: string;
  pe: number;
  vwap: number;
}

export interface PredictionData {
  symbol: string;
  model: string;
  direction: 1 | -1 | 0;
  confidence: number;
  predictedPrice: number;
  lower80: number;
  upper80: number;
  lower95: number;
  upper95: number;
  timestamp: number;
}

export interface AlertEvent {
  id: string;
  alertId: string;
  message: string;
  severity: 1 | 2 | 3 | 4 | 5;
  symbol: string;
  type: 'price' | 'technical' | 'ml' | 'sentiment' | 'anomaly' | 'news';
  triggeredAt: number;
}

export interface AnomalyEvent {
  symbol: string;
  anomalyType: string;
  severity: 1 | 2 | 3 | 4 | 5;
  description: string;
  timestamp: number;
}

export interface RegimeData {
  symbol: string;
  oldRegime: 'bull' | 'bear' | 'sideways';
  newRegime: 'bull' | 'bear' | 'sideways';
  confidence: number;
  timestamp: number;
}

export interface PortfolioUpdate {
  pnl: number;
  pnlPct: number;
  positions: Array<{
    symbol: string;
    quantity: number;
    avgCost: number;
    currentPrice: number;
    pnl: number;
  }>;
  timestamp: number;
}

export interface WebSocketMessage {
  type: 'tick' | 'prediction_update' | 'alert_triggered' | 'regime_change' | 'anomaly_detected' | 'portfolio_update' | 'heartbeat' | 'subscribe' | 'unsubscribe' | 'pong';
  symbol?: string;
  price?: number;
  volume?: number;
  change_pct?: number;
  timestamp?: number;
  high_52week?: number;
  low_52week?: number;
  market_cap?: string;
  pe?: number;
  vwap?: number;
  model?: string;
  direction?: 1 | -1 | 0;
  confidence?: number;
  predicted_price?: number;
  lower_80?: number;
  upper_80?: number;
  lower_95?: number;
  upper_95?: number;
  alert_id?: string;
  message?: string;
  severity?: 1 | 2 | 3 | 4 | 5;
  triggered_at?: number;
  anomaly_type?: string;
  description?: string;
  pnl?: number;
  pnl_pct?: number;
  positions?: Array<{
    symbol: string;
    quantity: number;
    avgCost: number;
    currentPrice: number;
    pnl: number;
  }>;
  symbols?: string[];
}

export interface HeatmapData {
  symbol: string;
  name: string;
  sector: string;
  marketCap: number;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  prediction?: PredictionData;
}

export interface StatCardData {
  label: string;
  value: number | string;
  change?: number;
  changePct?: number;
  icon?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';
