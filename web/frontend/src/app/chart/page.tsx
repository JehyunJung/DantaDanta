"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch, ChartData, UniverseItem } from "@/lib/api";
import { useFavorites } from "@/lib/useFavorites";
import CandleChart from "@/components/CandleChart";

const PERIODS = [
  { value: "1",  label: "1분" },
  { value: "5",  label: "5분" },
  { value: "15", label: "15분" },
  { value: "30", label: "30분" },
  { value: "60", label: "60분" },
  { value: "D",  label: "일" },
  { value: "W",  label: "주" },
  { value: "M",  label: "월" },
  { value: "Y",  label: "연" },
];

const LEGEND = [
  { color: "bg-yellow-400", label: "EMA5 (단기 이동평균)" },
  { color: "bg-purple-400", label: "EMA20 (중기 이동평균)" },
  { color: "bg-cyan-400",   label: "EMA60 (장기 이동평균)" },
  { color: "bg-gray-400",   label: "볼린저밴드 (±2σ)" },
];

export default function ChartPage() {
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState(searchParams.get("symbol") ?? "005930");
  const [market, setMarket] = useState(searchParams.get("market") ?? "KRX");
  const [period, setPeriod] = useState("D");
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(false);
  const [universe, setUniverse] = useState<UniverseItem[]>([]);

  const { favorites, toggle, isFavorite } = useFavorites();

  // 유니버스 로드
  useEffect(() => {
    apiFetch<UniverseItem[]>("/api/universe").then(setUniverse).catch(() => {});
  }, []);

  // 차트 데이터 로드
  useEffect(() => {
    setLoading(true);
    const days = period === "W" ? 365 : period === "M" ? 730 : period === "Y" ? 1825 : 120;
    const marketParam = market !== "KRX" ? `&market=${market}` : "";
    const url = ["1","5","15","30","60"].includes(period)
      ? `/api/chart/${symbol}?period=${period}${marketParam}`
      : `/api/chart/${symbol}?period=${period}&days=${days}${marketParam}`;

    apiFetch<ChartData>(url)
      .then(setChartData)
      .catch(() => setChartData(null))
      .finally(() => setLoading(false));
  }, [symbol, period, market]);

  const isMinute    = ["1","5","15","30","60"].includes(period);
  const hasIndicators = period === "D" || period === "W";
  const rsi = chartData?.indicators?.rsi?.at(-1)?.value;

  const currentItem = universe.find((u) => u.symbol === symbol);
  const currentName = currentItem?.name ?? symbol;

  const selectSymbol = (sym: string, mkt: string) => {
    setSymbol(sym);
    setMarket(mkt);
  };

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">{currentName}</h1>
        <span className="text-sm text-gray-500 font-mono">{symbol}</span>
        {currentItem && (
          <button
            onClick={() => toggle({ symbol, name: currentName, market })}
            className="text-xl leading-none"
            title={isFavorite(symbol) ? "즐겨찾기 해제" : "즐겨찾기 추가"}
          >
            {isFavorite(symbol) ? "★" : "☆"}
          </button>
        )}
      </div>

      {/* 즐겨찾기 목록 */}
      {favorites.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-gray-500">즐겨찾기</p>
          <div className="flex gap-2 flex-wrap">
            {favorites.map((f) => (
              <button
                key={f.symbol}
                onClick={() => selectSymbol(f.symbol, f.market)}
                className={`group flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  symbol === f.symbol
                    ? "bg-green-600 text-white"
                    : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                }`}
              >
                <span>★</span>
                <span>{f.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 전체 종목 검색 */}
      <details className="group">
        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300 select-none list-none flex items-center gap-1">
          <span className="group-open:hidden">▶</span>
          <span className="hidden group-open:inline">▼</span>
          전체 종목 보기 ({universe.length})
        </summary>
        <div className="mt-2 flex gap-1.5 flex-wrap max-h-40 overflow-y-auto pr-1">
          {universe.map((u) => (
            <button
              key={u.symbol}
              onClick={() => selectSymbol(u.symbol, u.market)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs transition-colors ${
                symbol === u.symbol
                  ? "bg-green-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {isFavorite(u.symbol) && <span className="text-yellow-400">★</span>}
              {u.name || u.symbol}
            </button>
          ))}
        </div>
      </details>

      {/* 봉 종류 선택 */}
      <div className="flex gap-1 flex-wrap">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`px-3 py-1 rounded text-xs transition-colors ${
              period === p.value ? "bg-green-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* 범례 (일봉·주봉만) */}
      {hasIndicators && (
        <div className="flex gap-4 flex-wrap">
          {LEGEND.map((l) => (
            <span key={l.label} className="flex items-center gap-1.5 text-xs text-gray-400">
              <span className={`w-4 h-0.5 ${l.color} inline-block rounded`} />
              {l.label}
            </span>
          ))}
        </div>
      )}

      {/* 차트 */}
      {loading ? (
        <div className="h-96 flex items-center justify-center text-gray-500">불러오는 중...</div>
      ) : chartData && chartData.candles.length > 0 ? (
        <CandleChart data={chartData} isMinute={isMinute} />
      ) : (
        <div className="h-96 flex items-center justify-center text-gray-500">
          {isMinute ? "장 시간 외에는 분봉 데이터가 없습니다." : "차트 데이터를 불러올 수 없습니다."}
        </div>
      )}

      {/* RSI */}
      {hasIndicators && rsi !== undefined && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <p className="text-xs text-gray-400 mb-1">RSI (14)</p>
          <p className={`text-xl font-bold ${rsi >= 70 ? "text-red-400" : rsi <= 30 ? "text-blue-400" : "text-white"}`}>
            {rsi.toFixed(1)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {rsi >= 70 ? "과매수 구간" : rsi <= 30 ? "과매도 구간" : "중립"}
          </p>
        </div>
      )}
    </div>
  );
}
