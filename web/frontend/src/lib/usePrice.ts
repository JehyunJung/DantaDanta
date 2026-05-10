"use client";

import { useEffect, useState } from "react";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export interface PriceData {
  symbol: string;
  price: number;
  change: string;
  change_rate: string;
  volume: number;
}

export function usePrice(symbol: string): PriceData | null {
  const [data, setData] = useState<PriceData | null>(null);

  useEffect(() => {
    if (!symbol) return;
    const ws = new WebSocket(`${WS_BASE}/ws/price/${symbol}`);
    ws.onmessage = (e) => setData(JSON.parse(e.data));
    ws.onerror = () => ws.close();
    return () => ws.close();
  }, [symbol]);

  return data;
}
