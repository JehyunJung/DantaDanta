const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export interface AccountSummary {
  net_asset: number;
  stocks_eval: number;
  total_purchase: number;
  pnl_amount: number;
  pnl_rate: number;
  holdings_count: number;
}

export interface Position {
  symbol: string;
  name: string;
  qty: number;
  avg_price: number;
  current_price: number;
  pnl_amount: number;
  pnl_rate: number;
  amount: number;
  market: string;
}

export interface Order {
  id: number;
  order_no: string;
  symbol: string;
  name: string;
  side: "buy" | "sell";
  qty: number;
  price: number;
  amount: number;
  reason: string;
  strategy: string;
  created_at: string;
  market: string;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartData {
  symbol: string;
  candles: Candle[];
  indicators: Partial<{
    ema5: { time: string; value: number }[];
    ema20: { time: string; value: number }[];
    ema60: { time: string; value: number }[];
    bb_upper: { time: string; value: number }[];
    bb_lower: { time: string; value: number }[];
    rsi: { time: string; value: number }[];
  }>;
}

export interface UniverseItem {
  symbol: string;
  name: string;
  market: string;
  sector: string;
  screen: boolean;
  added_at: string;
}

export interface ScreenerItem {
  symbol: string;
  name: string;
  score: number;
  current_price: number;
  rsi: number | null;
  news_score: number;
  news_summary: string;
}
