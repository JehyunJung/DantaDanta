import { apiFetch, Position } from "@/lib/api";
import SellButton from "@/components/SellButton";

function fmt(n: number) { return n.toLocaleString("ko-KR"); }

export default async function Positions() {
  const positions = await apiFetch<Position[]>("/api/account/positions").catch(() => []);
  const total = positions.reduce((s, p) => s + p.amount, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">보유 종목</h1>

      {positions.length === 0 ? (
        <p className="text-gray-500">보유 종목이 없습니다.</p>
      ) : (
        <>
          {/* 수익률 바 차트 */}
          <section>
            <h2 className="text-lg font-semibold mb-3">종목별 수익률</h2>
            <div className="space-y-2">
              {[...positions].sort((a, b) => b.pnl_rate - a.pnl_rate).map((p) => {
                const isPos = p.pnl_rate >= 0;
                const width = Math.min(Math.abs(p.pnl_rate) * 5, 100);
                return (
                  <div key={p.symbol} className="flex items-center gap-3 text-sm">
                    <span className="w-28 truncate text-gray-300">{p.name}</span>
                    <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${isPos ? "bg-red-500" : "bg-blue-500"}`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                    <span className={`w-16 text-right font-medium ${isPos ? "text-red-400" : "text-blue-400"}`}>
                      {isPos ? "+" : ""}{p.pnl_rate.toFixed(2)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </section>

          {/* 종목 비중 */}
          <section>
            <h2 className="text-lg font-semibold mb-3">포트폴리오 비중</h2>
            <div className="flex gap-1 h-4 rounded-full overflow-hidden">
              {positions.map((p, i) => {
                const colors = ["bg-green-500","bg-blue-500","bg-yellow-500","bg-purple-500","bg-pink-500","bg-orange-500","bg-teal-500","bg-red-500","bg-indigo-500","bg-cyan-500"];
                return (
                  <div key={p.symbol} title={p.name} className={`${colors[i % colors.length]}`} style={{ width: `${(p.amount / total) * 100}%` }} />
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3 mt-2">
              {positions.map((p, i) => {
                const colors = ["bg-green-500","bg-blue-500","bg-yellow-500","bg-purple-500","bg-pink-500","bg-orange-500","bg-teal-500","bg-red-500","bg-indigo-500","bg-cyan-500"];
                return (
                  <span key={p.symbol} className="flex items-center gap-1 text-xs text-gray-400">
                    <span className={`w-2 h-2 rounded-full ${colors[i % colors.length]}`} />
                    {p.name} {((p.amount / total) * 100).toFixed(1)}%
                  </span>
                );
              })}
            </div>
          </section>

          {/* 상세 테이블 */}
          <section>
            <h2 className="text-lg font-semibold mb-3">보유 종목 상세</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2">종목</th>
                  <th className="text-right py-2">수량</th>
                  <th className="text-right py-2">평균단가</th>
                  <th className="text-right py-2">현재가</th>
                  <th className="text-right py-2">평가금액</th>
                  <th className="text-right py-2">손익</th>
                  <th className="text-right py-2">수익률</th>
                  <th className="py-2"></th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => {
                  const isPos = p.pnl_rate >= 0;
                  return (
                    <tr key={p.symbol} className="border-b border-gray-800/50">
                      <td className="py-2">{p.name}<span className="text-gray-500 text-xs ml-1">{p.symbol}</span></td>
                      <td className="py-2 text-right">{fmt(p.qty)}</td>
                      <td className="py-2 text-right">{fmt(Math.round(p.avg_price))}</td>
                      <td className="py-2 text-right">{fmt(p.current_price)}</td>
                      <td className="py-2 text-right">{fmt(p.amount)}</td>
                      <td className={`py-2 text-right font-medium ${isPos ? "text-red-400" : "text-blue-400"}`}>{isPos ? "+" : ""}{fmt(p.pnl_amount)}</td>
                      <td className={`py-2 text-right font-medium ${isPos ? "text-red-400" : "text-blue-400"}`}>{isPos ? "+" : ""}{p.pnl_rate.toFixed(2)}%</td>
                      <td className="py-2 text-right"><SellButton symbol={p.symbol} qty={p.qty} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}
