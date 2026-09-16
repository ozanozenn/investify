"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "@/components/theme-provider";
import { InfoTooltip } from "@/components/ui/info-tooltip";

export interface YearValue {
  year: number;
  value: number | null;
}

/** Small histogram-style chart for annual figures (Revenue/EBITDA/Net
 * Income/FCF — roadmap section 3.14 "Financial Performance"), built on
 * TradingView Lightweight Charts (the roadmap's named preference, section
 * "Chart" — free/open-source, Apache-2.0). A full price candlestick chart
 * is deferred to Phase 2 (docs/PHASE_1_SCOPE.md); this component uses the
 * same library for the yearly bar series the Phase 1 screen actually
 * needs. */
export function MiniBarChart({
  label,
  data,
  colorVar = "--accent",
  currency,
  help,
}: {
  label: string;
  data: YearValue[];
  colorVar?: string;
  currency?: string;
  help?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    let disposed = false;
    let chart: import("lightweight-charts").IChartApi | undefined;

    async function render() {
      if (!containerRef.current) return;
      const { createChart, ColorType } = await import("lightweight-charts");
      if (disposed || !containerRef.current) return;

      const styles = getComputedStyle(document.documentElement);
      const color = styles.getPropertyValue(colorVar).trim() || "#2563eb";
      const foreground = styles.getPropertyValue("--foreground").trim();
      const muted = styles.getPropertyValue("--muted").trim();

      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height: 140,
        layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: muted, fontSize: 11 },
        grid: { horzLines: { visible: false }, vertLines: { visible: false } },
        rightPriceScale: { visible: false },
        timeScale: { visible: true, borderVisible: false },
        crosshair: { horzLine: { visible: false }, vertLine: { visible: false } },
        handleScroll: false,
        handleScale: false,
      });

      const series = chart.addHistogramSeries({ color, priceFormat: { type: "volume" } });
      series.setData(
        data
          .filter((d) => d.value !== null)
          .map((d) => ({ time: `${d.year}-01-01`, value: d.value as number }))
      );
      chart.timeScale().fitContent();
      void foreground;
    }

    render();
    const handleResize = () => {
      if (chart && containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);
    return () => {
      disposed = true;
      window.removeEventListener("resize", handleResize);
      chart?.remove();
    };
  }, [data, colorVar, theme]);

  const hasData = data.some((d) => d.value !== null);

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="flex items-center gap-1 text-xs font-medium text-muted">
          {label}
          {help && <InfoTooltip text={help} />}
        </span>
        {currency && <span className="text-[10px] text-muted">{currency}</span>}
      </div>
      {hasData ? (
        <div ref={containerRef} className="w-full" />
      ) : (
        <div className="flex h-[140px] items-center justify-center text-xs text-muted">Veri yok</div>
      )}
    </div>
  );
}
