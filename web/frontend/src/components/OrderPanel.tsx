"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

interface Props {
  defaultSymbol?: string;
  defaultQty?: number;
  defaultSide?: "buy" | "sell";
}

export default function OrderPanel({ defaultSymbol = "", defaultQty = 1, defaultSide = "buy" }: Props) {
  const [side, setSide] = useState<"buy" | "sell">(defaultSide);
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [qty, setQty] = useState(defaultQty);
  const [price, setPrice] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit() {
    if (!symbol || qty <= 0) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await apiFetch<{ order_no: string }>(`/api/orders/${side}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: symbol.toUpperCase(), qty, price }),
      });
      setResult(`✅ ${side === "buy" ? "매수" : "매도"} 완료 — 주문번호 ${res.order_no}`);
    } catch (e: unknown) {
      setResult(`❌ 실패: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
      <h2 className="text-lg font-semibold">수동 주문</h2>

      {/* 매수/매도 탭 */}
      <div className="flex rounded-lg overflow-hidden border border-gray-700 w-fit">
        <button
          onClick={() => setSide("buy")}
          className={`px-6 py-2 text-sm font-medium transition-colors ${side === "buy" ? "bg-red-600 text-white" : "text-gray-400 hover:text-white"}`}
        >매수</button>
        <button
          onClick={() => setSide("sell")}
          className={`px-6 py-2 text-sm font-medium transition-colors ${side === "sell" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}
        >매도</button>
      </div>

      {/* 입력 폼 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-gray-400">종목코드</label>
          <input
            value={symbol}
            onChange={e => setSymbol(e.target.value.toUpperCase())}
            placeholder="005930"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-400">수량</label>
          <input
            type="number"
            value={qty}
            onChange={e => setQty(Number(e.target.value))}
            min={1}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-400">지정가 (0 = 시장가)</label>
          <input
            type="number"
            value={price}
            onChange={e => setPrice(Number(e.target.value))}
            min={0}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          />
        </div>
      </div>

      <button
        onClick={submit}
        disabled={loading || !symbol || qty <= 0}
        className={`w-full py-2 rounded-lg font-medium text-sm transition-colors disabled:opacity-50 ${
          side === "buy" ? "bg-red-600 hover:bg-red-500" : "bg-blue-600 hover:bg-blue-500"
        }`}
      >
        {loading ? "처리 중..." : side === "buy" ? "매수 주문" : "매도 주문"}
      </button>

      {result && (
        <p className="text-sm text-gray-300">{result}</p>
      )}
    </div>
  );
}
