"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Config {
  budget_limit: number;
  max_position_ratio: number;
  swing_sl_rate: number;
  swing_tp_rate: number;
  news_enabled: boolean;
  news_threshold: number;
  scalping_enabled: boolean;
  scalp_sl_rate: number;
  scalp_tp_rate: number;
  scalp_max_hold: number;
  scalp_max_pos: number;
  scalp_invest: number;
}

export default function ConfigPage() {
  const [cfg, setCfg] = useState<Config | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<Config>("/api/config").then(setCfg).catch(() => {});
  }, []);

  async function patch(update: Partial<Config>) {
    setCfg(prev => prev ? { ...prev, ...update } : prev);
    setSaving(true);
    setSaved(false);
    try {
      const result = await apiFetch<Config>("/api/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(update),
      });
      setCfg(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  if (!cfg) return <div className="text-gray-400 p-4">로딩 중...</div>;

  const aggressiveness = Math.round(
    ((cfg.swing_tp_rate / 10) * 0.5 + (1 - cfg.swing_sl_rate / 10) * 0.5) * 100
  );

  return (
    <div className="max-w-2xl space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">설정</h1>
        <span className="text-sm text-gray-500">
          {saving && "저장 중..."}
          {saved && <span className="text-green-400">✓ 저장됨</span>}
          {!saving && !saved && "변경 시 자동 저장"}
        </span>
      </div>

      {/* 예산 */}
      <Section title="예산" desc="자동매매에 사용할 총 투자 한도">
        <Row label="총 투자 한도" unit="원" min={100000} max={50000000} step={100000}
          value={cfg.budget_limit}
          onChange={v => patch({ budget_limit: v })} />
        <Row label="종목당 최대 비율" unit="%" min={5} max={100} step={5}
          value={Math.round(cfg.max_position_ratio * 100)}
          onChange={v => patch({ max_position_ratio: v / 100 })} />
        <div className="text-xs text-gray-500 pt-1">
          종목당 최대 투자금 = {Math.round(cfg.budget_limit * cfg.max_position_ratio).toLocaleString()}원
        </div>
      </Section>

      {/* 투자 성향 */}
      <Section title="투자 성향" desc="30분 사이클 스윙 트레이딩 기준">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-sm text-gray-400">방어적</span>
          <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${aggressiveness}%`,
                background: `hsl(${120 - aggressiveness}, 80%, 50%)`,
              }}
            />
          </div>
          <span className="text-sm text-gray-400">공격적</span>
        </div>
        <Row label="손절" unit="%" min={1} max={20} step={0.5}
          value={cfg.swing_sl_rate}
          onChange={v => patch({ swing_sl_rate: v })} />
        <Row label="익절" unit="%" min={1} max={50} step={0.5}
          value={cfg.swing_tp_rate}
          onChange={v => patch({ swing_tp_rate: v })} />
      </Section>

      {/* 뉴스 분석 */}
      <Section
        title="뉴스 감성 분석"
        desc="매수 전 뉴스 감성 점수로 필터링"
        toggle={{ value: cfg.news_enabled, onChange: v => patch({ news_enabled: v }) }}
      >
        <div className={cfg.news_enabled ? "" : "opacity-40 pointer-events-none"}>
          <Row label="최소 감성 점수" unit="" min={-1} max={0} step={0.05}
            value={cfg.news_threshold}
            onChange={v => patch({ news_threshold: v })} />
          <div className="text-xs text-gray-500 mt-1">
            {cfg.news_threshold} 미만이면 매수 보류 (−1=매우부정 / 0=중립)
          </div>
        </div>
      </Section>

      {/* 스캘핑 */}
      <Section
        title="스캘핑"
        desc="분봉 BB+RSI 단기 자동매매 (장중에만 동작)"
        toggle={{ value: cfg.scalping_enabled, onChange: v => patch({ scalping_enabled: v }) }}
      >
        <div className={cfg.scalping_enabled ? "space-y-3" : "space-y-3 opacity-40 pointer-events-none"}>
          <Row label="손절" unit="%" min={0.1} max={5} step={0.1}
            value={cfg.scalp_sl_rate}
            onChange={v => patch({ scalp_sl_rate: v })} />
          <Row label="익절" unit="%" min={0.1} max={10} step={0.1}
            value={cfg.scalp_tp_rate}
            onChange={v => patch({ scalp_tp_rate: v })} />
          <Row label="최대 보유 시간" unit="분" min={5} max={120} step={5}
            value={cfg.scalp_max_hold}
            onChange={v => patch({ scalp_max_hold: v })} />
          <Row label="동시 최대 종목" unit="개" min={1} max={10} step={1}
            value={cfg.scalp_max_pos}
            onChange={v => patch({ scalp_max_pos: v })} />
          <Row label="종목당 투자금" unit="원" min={100000} max={5000000} step={100000}
            value={cfg.scalp_invest}
            onChange={v => patch({ scalp_invest: v })} />
        </div>
      </Section>
    </div>
  );
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
        value ? "bg-green-500" : "bg-gray-600"
      }`}
    >
      <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${
        value ? "translate-x-6" : "translate-x-1"
      }`} />
    </button>
  );
}

function Section({
  title, desc, toggle, children,
}: {
  title: string;
  desc: string;
  toggle?: { value: boolean; onChange: (v: boolean) => void };
  children: React.ReactNode;
}) {
  return (
    <section className="bg-gray-900 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-base font-semibold text-white">{title}</div>
          <div className="text-xs text-gray-400 mt-0.5">{desc}</div>
        </div>
        {toggle && <Toggle value={toggle.value} onChange={toggle.onChange} />}
      </div>
      {children}
    </section>
  );
}

function Row({
  label, unit, min, max, step, value, onChange,
}: {
  label: string; unit: string; min: number; max: number; step: number;
  value: number; onChange: (v: number) => void;
}) {
  const display = unit === "원"
    ? Number(value).toLocaleString() + " 원"
    : unit === ""
    ? value.toFixed(2)
    : `${value} ${unit}`;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-300 w-32 shrink-0">{label}</span>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="flex-1 accent-green-500 h-1.5"
      />
      <span className="text-sm text-white w-28 text-right tabular-nums shrink-0">{display}</span>
    </div>
  );
}
