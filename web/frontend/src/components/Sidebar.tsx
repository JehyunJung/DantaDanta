"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "대시보드", icon: "📊" },
  { href: "/positions", label: "보유 종목", icon: "💼" },
  { href: "/chart", label: "차트", icon: "📈" },
  { href: "/orders", label: "주문내역", icon: "📋" },
  { href: "/screener", label: "스크리너", icon: "🔍" },
  { href: "/universe", label: "종목관리", icon: "📝" },
  { href: "/config", label: "설정", icon: "⚙️" },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-48 min-h-screen bg-gray-900 text-gray-100 flex flex-col p-4 gap-1">
      <div className="text-xl font-bold text-green-400 mb-6 px-2">DantaDanta</div>
      {NAV.map((n) => (
        <Link
          key={n.href}
          href={n.href}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
            path === n.href
              ? "bg-green-600 text-white"
              : "hover:bg-gray-800 text-gray-300"
          }`}
        >
          <span>{n.icon}</span>
          {n.label}
        </Link>
      ))}
    </aside>
  );
}
