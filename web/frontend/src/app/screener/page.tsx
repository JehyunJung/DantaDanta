import Link from "next/link";
import { apiFetch, ScreenerItem } from "@/lib/api";

function fmt(n: number) { return n.toLocaleString("ko-KR"); }

export default async function Screener() {
  const items = await apiFetch<ScreenerItem[]>("/api/screener").catch(() => []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">스크리너</h1>
      <p className="text-sm text-gray-400">기술적 지표 + 뉴스 감성 기반 매수 매력도 점수 (0~120)</p>

      {items.length === 0 ? (
        <p className="text-gray-500">스크리닝 결과가 없습니다.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Link
              key={item.symbol}
              href={`/chart?symbol=${item.symbol}`}
              className="flex items-center gap-4 bg-gray-900 border border-gray-800 rounded-xl p-4 hover:border-gray-600 transition-colors"
            >
              <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center shrink-0">
                <span className="text-lg font-bold text-green-400">{Math.round(item.score)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold">{item.name}</span>
                  <span className="text-xs text-gray-500 font-mono">{item.symbol}</span>
                  {item.news_score !== 0 && (
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                      item.news_score > 0.2 ? "bg-red-900/50 text-red-400" :
                      item.news_score < -0.2 ? "bg-blue-900/50 text-blue-400" :
                      "bg-gray-800 text-gray-500"
                    }`}>
                      뉴스 {item.news_score > 0 ? "+" : ""}{(item.news_score * 100).toFixed(0)}
                    </span>
                  )}
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: `${Math.min(item.score, 100)}%` }} />
                </div>
                {item.news_summary && (
                  <p className="text-xs text-gray-500 mt-1 truncate">{item.news_summary}</p>
                )}
              </div>
              <div className="text-right space-y-1 shrink-0">
                <p className="text-sm font-medium">{fmt(item.current_price)}원</p>
                {item.rsi !== null && (
                  <p className={`text-xs ${item.rsi < 30 ? "text-blue-400" : item.rsi > 70 ? "text-red-400" : "text-gray-400"}`}>
                    RSI {item.rsi.toFixed(1)}
                  </p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
