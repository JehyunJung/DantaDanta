import OrderPanel from "@/components/OrderPanel";

export default function TradePage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">수동 주문</h1>
      <OrderPanel />
    </div>
  );
}
