"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch, UniverseItem } from "@/lib/api";
import { useFavorites } from "@/lib/useFavorites";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const MARKETS = [
  { value: "KRX",  label: "국내 (KRX)" },
  { value: "NASD", label: "나스닥 (NASD)" },
  { value: "NYSE", label: "뉴욕 (NYSE)" },
  { value: "AMEX", label: "아멕스 (AMEX)" },
  { value: "SEHK", label: "홍콩 (SEHK)" },
  { value: "TKSE", label: "도쿄 (TKSE)" },
];

const MARKET_BADGE: Record<string, string> = {
  KRX:  "bg-blue-900/50 text-blue-300",
  NASD: "bg-purple-900/50 text-purple-300",
  NYSE: "bg-green-900/50 text-green-300",
  AMEX: "bg-yellow-900/50 text-yellow-300",
  SEHK: "bg-red-900/50 text-red-300",
  TKSE: "bg-orange-900/50 text-orange-300",
};

type SortKey = "symbol" | "name" | "market" | "sector" | "added_at";

export default function UniversePage() {
  const [items, setItems] = useState<UniverseItem[]>([]);
  const { toggle, isFavorite } = useFavorites();
  const [input, setInput] = useState("");
  const [market, setMarket] = useState("KRX");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filterMarket, setFilterMarket] = useState("ALL");
  const [filterSector, setFilterSector] = useState("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("added_at");
  const [sortAsc, setSortAsc] = useState(true);

  const load = () =>
    apiFetch<UniverseItem[]>("/api/universe").then(setItems).catch(() => {});

  useEffect(() => { load(); }, []);

  const sectors = useMemo(() =>
    ["ALL", ...Array.from(new Set(items.map((i) => i.sector).filter(Boolean))).sort()],
    [items]
  );

  const filtered = useMemo(() => {
    let list = [...items];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((i) =>
        i.symbol.toLowerCase().includes(q) || i.name.toLowerCase().includes(q)
      );
    }
    if (filterMarket !== "ALL") list = list.filter((i) => i.market === filterMarket);
    if (filterSector !== "ALL") list = list.filter((i) => i.sector === filterSector);
    list.sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    return list;
  }, [items, search, filterMarket, filterSector, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((v) => !v);
    else { setSortKey(key); setSortAsc(true); }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? <span className="ml-1">{sortAsc ? "↑" : "↓"}</span> : null;

  const add = async () => {
    if (!input.trim()) return;
    setLoading(true); setError("");
    try {
      const r = await fetch(`${BASE}/api/universe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: input.trim(), market }),
      });
      if (!r.ok) throw new Error("추가 실패 (종목코드 확인)");
      setInput("");
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "오류 발생");
    } finally { setLoading(false); }
  };

  const remove = async (symbol: string) => {
    await fetch(`${BASE}/api/universe/${symbol}`, { method: "DELETE" });
    await load();
  };

  const toggleScreen = async (symbol: string) => {
    await fetch(`${BASE}/api/universe/${symbol}/screen`, { method: "PATCH" });
    await load();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">종목 관리</h1>

      {/* 종목 추가 */}
      <div className="flex gap-2 items-center flex-wrap">
        <select
          value={market} onChange={(e) => setMarket(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500"
        >
          {MARKETS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
        </select>
        <input
          type="text" value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder={market === "KRX" ? "종목코드 (예: 005930)" : "티커 (예: AAPL)"}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white w-44 focus:outline-none focus:border-green-500"
        />
        <button onClick={add} disabled={loading}
          className="bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg">
          {loading ? "추가 중..." : "추가"}
        </button>
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </div>

      {/* 검색 + 필터 */}
      <div className="flex gap-2 flex-wrap items-center">
        <input
          type="text" value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="종목명 / 코드 검색"
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white w-48 focus:outline-none focus:border-green-500"
        />
        <select value={filterMarket} onChange={(e) => setFilterMarket(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-green-500">
          <option value="ALL">전체 시장</option>
          {MARKETS.map((m) => <option key={m.value} value={m.value}>{m.value}</option>)}
        </select>
        <select value={filterSector} onChange={(e) => setFilterSector(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-green-500">
          {sectors.map((s) => <option key={s} value={s}>{s === "ALL" ? "전체 섹터" : s}</option>)}
        </select>
        <span className="text-xs text-gray-500 ml-auto">{filtered.length} / {items.length}개</span>
      </div>

      {/* 테이블 */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800 text-left text-xs">
              {[
                { key: "symbol"   as SortKey, label: "종목코드" },
                { key: "name"     as SortKey, label: "종목명" },
                { key: "market"   as SortKey, label: "시장" },
                { key: "sector"   as SortKey, label: "섹터" },
                { key: "added_at" as SortKey, label: "추가일" },
              ].map(({ key, label }) => (
                <th key={key}
                  className="px-4 py-3 cursor-pointer hover:text-white select-none"
                  onClick={() => toggleSort(key)}>
                  {label}<SortIcon k={key} />
                </th>
              ))}
              <th className="px-4 py-3 text-center">스크리닝</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-gray-500 text-center">
                  {items.length === 0 ? "등록된 종목이 없습니다." : "검색 결과가 없습니다."}
                </td>
              </tr>
            ) : filtered.map((item) => (
              <tr key={item.symbol} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => toggle({ symbol: item.symbol, name: item.name, market: item.market })}
                      className={`text-sm leading-none ${isFavorite(item.symbol) ? "text-yellow-400" : "text-gray-600 hover:text-yellow-400"}`}
                    >
                      {isFavorite(item.symbol) ? "★" : "☆"}
                    </button>
                    <Link href={`/chart?symbol=${item.symbol}&market=${item.market}`}
                      className="font-mono text-green-400 hover:text-green-300 hover:underline text-xs">
                      {item.symbol}
                    </Link>
                  </div>
                </td>
                <td className="px-4 py-2.5 font-medium text-white">{item.name || "-"}</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${MARKET_BADGE[item.market] ?? "bg-gray-800 text-gray-400"}`}>
                    {item.market}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-400 text-xs">{item.sector || "-"}</td>
                <td className="px-4 py-2.5 text-gray-500 text-xs">
                  {new Date(item.added_at).toLocaleDateString("ko-KR")}
                </td>
                <td className="px-4 py-2.5 text-center">
                  <button
                    onClick={() => toggleScreen(item.symbol)}
                    className={`relative inline-flex w-9 h-5 rounded-full transition-colors focus:outline-none ${item.screen ? "bg-green-600" : "bg-gray-700"}`}
                  >
                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${item.screen ? "translate-x-4" : "translate-x-0"}`} />
                  </button>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <button onClick={() => remove(item.symbol)}
                    className="text-gray-600 hover:text-red-400 text-xs">삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
