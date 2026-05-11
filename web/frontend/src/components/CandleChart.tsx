"use client";

import { useEffect, useRef } from "react";
import { createChart, IChartApi, CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts";
import { ChartData } from "@/lib/api";

export default function CandleChart({ data, isMinute = false }: { data: ChartData; isMinute?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.candles.length === 0) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { color: "#030712" }, textColor: "#9ca3af" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      width: containerRef.current.clientWidth,
      height: 400,
      localization: {
        timeFormatter: isMinute
          ? (ts: number) => {
              const d = new Date(ts * 1000);
              return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
            }
          : undefined,
      },
      timeScale: {
        tickMarkFormatter: isMinute
          ? (ts: number) => {
              const d = new Date(ts * 1000);
              return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
            }
          : undefined,
      },
    });
    chartRef.current = chart;

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#ef4444", downColor: "#3b82f6",
      borderUpColor: "#ef4444", borderDownColor: "#3b82f6",
      wickUpColor: "#ef4444", wickDownColor: "#3b82f6",
    });
    candle.setData(data.candles as any);

    if (data.indicators?.ema5?.length > 0) {
      const ema5 = chart.addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1 });
      ema5.setData(data.indicators.ema5 as any);
    }
    if (data.indicators?.ema20?.length > 0) {
      const ema20 = chart.addSeries(LineSeries, { color: "#8b5cf6", lineWidth: 1 });
      ema20.setData(data.indicators.ema20 as any);
    }
    if (data.indicators?.ema60?.length > 0) {
      const ema60 = chart.addSeries(LineSeries, { color: "#06b6d4", lineWidth: 1 });
      ema60.setData(data.indicators.ema60 as any);
    }
    if (data.indicators?.bb_upper?.length > 0) {
      const bbu = chart.addSeries(LineSeries, { color: "#6b7280", lineWidth: 1, lineStyle: 2 });
      bbu.setData(data.indicators.bb_upper as any);
      const bbl = chart.addSeries(LineSeries, { color: "#6b7280", lineWidth: 1, lineStyle: 2 });
      bbl.setData(data.indicators.bb_lower as any);
    }

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.resize(containerRef.current.clientWidth, 400);
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data]);

  return <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />;
}
