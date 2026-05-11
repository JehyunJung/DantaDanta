import { apiFetch, Order } from "@/lib/api";

function fmt(n: number) { return n.toLocaleString("ko-KR"); }

export default async function Orders() {
  const orders = await apiFetch<Order[]>("/api/orders?limit=100").catch(() => []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">주문 내역</h1>
      {orders.length === 0 ? (
        <p className="text-gray-500">주문 내역이 없습니다.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800">
              <th className="text-left py-2 pr-4">일시</th>
              <th className="text-left py-2 pr-4">종목</th>
              <th className="text-left py-2 pr-4">구분</th>
              <th className="text-right py-2 px-4">수량</th>
              <th className="text-right py-2 px-4">단가</th>
              <th className="text-right py-2 px-4">금액</th>
              <th className="text-left py-2 px-4">전략</th>
              <th className="text-left py-2 pl-4">사유</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                <td className="py-2 pr-4 text-gray-400 text-xs">{new Date(o.created_at).toLocaleString("ko-KR")}</td>
                <td className="py-2 pr-4">{o.name || o.symbol}<span className="text-gray-500 text-xs ml-1">{o.symbol}</span></td>
                <td className={`py-2 pr-4 font-medium ${o.side === "buy" ? "text-red-400" : "text-blue-400"}`}>{o.side === "buy" ? "매수" : "매도"}</td>
                <td className="py-2 px-4 text-right">{fmt(o.qty)}주</td>
                <td className="py-2 px-4 text-right">{fmt(o.price)}원</td>
                <td className="py-2 px-4 text-right">{fmt(o.amount)}원</td>
                <td className="py-2 px-4 text-gray-400 text-xs">{o.strategy}</td>
                <td className="py-2 pl-4 text-gray-400 text-xs">{o.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
