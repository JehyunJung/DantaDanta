import { apiFetch, AccountSummary, Order } from "@/lib/api";

function fmt(n: number) {
  return n.toLocaleString("ko-KR");
}

export default async function Dashboard() {
  const [account, orders] = await Promise.all([
    apiFetch<AccountSummary>("/api/account").catch(() => null),
    apiFetch<Order[]>("/api/orders?limit=5").catch(() => []),
  ]);

  const pnl = account ? account.total_eval - account.cash : 0;
  const pnlRate = account && account.cash > 0 ? ((pnl / account.cash) * 100).toFixed(2) : "0.00";
  const isPos = pnl >= 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">대시보드</h1>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card label="예수금" value={account ? `${fmt(account.cash)}원` : "-"} />
        <Card label="총매수금액" value={account ? `${fmt(account.total_purchase)}원` : "-"} />
        <Card label="총평가금액" value={account ? `${fmt(account.total_eval)}원` : "-"} />
        <Card label="평가손익" value={account ? `${isPos ? "+" : ""}${fmt(pnl)}원` : "-"} color={isPos ? "text-red-400" : "text-blue-400"} />
        <Card label="수익률" value={account ? `${isPos ? "+" : ""}${pnlRate}%` : "-"} color={isPos ? "text-red-400" : "text-blue-400"} />
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-3">최근 주문</h2>
        {orders.length === 0 ? (
          <p className="text-gray-500 text-sm">주문 내역이 없습니다.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2 px-3">일시</th>
                <th className="text-left py-2 px-3">종목</th>
                <th className="text-left py-2 px-3">구분</th>
                <th className="text-right py-2 px-3">수량</th>
                <th className="text-right py-2 px-3">단가</th>
                <th className="text-left py-2 px-3">사유</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b border-gray-800/50">
                  <td className="py-2 px-3 text-gray-400">{new Date(o.created_at).toLocaleString("ko-KR")}</td>
                  <td className="py-2 px-3">{o.name || o.symbol}</td>
                  <td className={`py-2 px-3 font-medium ${o.side === "buy" ? "text-red-400" : "text-blue-400"}`}>{o.side === "buy" ? "매수" : "매도"}</td>
                  <td className="py-2 px-3 text-right">{fmt(o.qty)}주</td>
                  <td className="py-2 px-3 text-right">{o.price > 0 ? `${fmt(o.price)}원` : "시장가"}</td>
                  <td className="py-2 px-3 text-gray-400 text-xs">{o.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Card({ label, value, color = "text-white" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
    </div>
  );
}
