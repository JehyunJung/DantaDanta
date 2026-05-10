import { apiFetch, ChartData } from "@/lib/api";
import CandleChart from "@/components/CandleChart";

const SYMBOLS = [
  { code: "005930", name: "삼성전자" },
  { code: "000660", name: "SK하이닉스" },
  { code: "035420", name: "NAVER" },
  { code: "005380", name: "현대차" },
  { code: "051910", name: "LG화학" },
];

export default async function Chart({
  searchParams,
}: {
  searchParams: Promise<{ symbol?: string }>;
}) {
  const params = await searchParams;
  const symbol = params.symbol ?? "005930";
  const chartData = await apiFetch<ChartData>(`/api/chart/${symbol}?days=120`).catch(() => null);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">차트</h1>

      {/* 종목 선택 탭 */}
      <div className="flex gap-2 flex-wrap">
        {SYMBOLS.map((s) => (
          <a
            key={s.code}
            href={`/chart?symbol=${s.code}`}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              symbol === s.code
                ? "bg-green-600 text-white"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            {s.name}
          </a>
        ))}
      </div>

      {/* 범례 */}
      <div className="flex gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-yellow-400 inline-block" />EMA5</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-purple-400 inline-block" />EMA20</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-cyan-400 inline-block" />EMA60</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-gray-400 inline-block" style={{borderTop:"1px dashed"}} />볼린저밴드</span>
      </div>

      {chartData ? (
        <CandleChart data={chartData} />
      ) : (
        <div className="h-96 flex items-center justify-center text-gray-500">
          차트 데이터를 불러올 수 없습니다.
        </div>
      )}

      {/* RSI 패널 */}
      {chartData && chartData.indicators.rsi.length > 0 && (
        <div>
          <p className="text-sm text-gray-400 mb-1">RSI (14) — 30 이하: 과매도, 70 이상: 과매수</p>
          <p className="text-lg font-bold">
            {chartData.indicators.rsi.at(-1)?.value.toFixed(1) ?? "-"}
          </p>
        </div>
      )}
    </div>
  );
}
