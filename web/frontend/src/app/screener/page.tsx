import { apiFetch, ScreenerItem } from "@/lib/api";

function fmt(n: number) { return n.toLocaleString("ko-KR"); }

export default async function Screener() {
  const items = await apiFetch<ScreenerItem[]>("/api/screener").catch(() => []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">스크리너</h1>
      <p className="text-sm text-gray-400">기술적 지표 기반 매수 매력도 점수 (0~100)</p>

      {items.length === 0 ? (
        <p className="text-gray-500">스크리닝 결과가 없습니다.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.symbol} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center">
                <span className="text-lg font-bold text-green-400">{Math.round(item.score)}</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold">{item.name}</span>
                  <span className="text-xs text-gray-500">{item.symbol}</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: `${item.score}%` }} />
                </div>
              </div>
              <div className="text-right space-y-1">
                <p className="text-sm font-medium">{fmt(item.current_price)}원</p>
                {item.rsi !== null && (
                  <p className={`text-xs ${item.rsi < 30 ? "text-blue-400" : item.rsi > 70 ? "text-red-400" : "text-gray-400"}`}>
                    RSI {item.rsi.toFixed(1)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
