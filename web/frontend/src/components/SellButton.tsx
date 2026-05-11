"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

interface Props {
  symbol: string;
  qty: number;
}

export default function SellButton({ symbol, qty }: Props) {
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function sell() {
    if (!confirm(`${symbol} ${qty}주 전량 매도하시겠습니까?`)) return;
    setLoading(true);
    try {
      await apiFetch("/api/orders/sell", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, qty, price: 0 }),
      });
      setDone(true);
    } catch {
      alert("매도 실패");
    } finally {
      setLoading(false);
    }
  }

  if (done) return <span className="text-xs text-gray-500">매도완료</span>;

  return (
    <button
      onClick={sell}
      disabled={loading}
      className="px-3 py-1 text-xs rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-50 transition-colors"
    >
      {loading ? "..." : "매도"}
    </button>
  );
}
