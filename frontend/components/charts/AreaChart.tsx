"use client";

import { useEffect, useId, useRef, useState } from "react";

export interface AreaChartPoint {
  label: string;
  value: number;
}

export interface AreaChartMarker {
  index: number;
  direction: "POSITIVE" | "NEGATIVE";
}

interface AreaChartProps {
  series: AreaChartPoint[];
  height?: number;
  color?: string;
  markers?: AreaChartMarker[];
}

export function AreaChart({ series, height = 240, color = "var(--primary)", markers = [] }: AreaChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const gradientId = useId().replace(/:/g, "");
  const [width, setWidth] = useState(600);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  if (!series.length) {
    return <div className="faint grid h-48 place-items-center text-sm">Chưa có dữ liệu biểu đồ.</div>;
  }

  const padLeft = 38;
  const padRight = 14;
  const padTop = 16;
  const padBottom = 28;
  const values = series.map((point) => point.value);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const padding = Math.max((rawMax - rawMin) * 0.08, Math.abs(rawMax) * 0.04, 0.01);
  const min = rawMin - padding;
  const max = rawMax + padding;
  const x = (index: number) => padLeft + index / Math.max(1, series.length - 1) * (width - padLeft - padRight);
  const y = (value: number) => padTop + (1 - (value - min) / (max - min)) * (height - padTop - padBottom);
  const line = series.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.value)}`).join(" ");
  const area = `${line} L${x(series.length - 1)},${height - padBottom} L${x(0)},${height - padBottom} Z`;

  return (
    <div ref={containerRef} className="w-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }} role="img" aria-label="Biểu đồ xu hướng theo thời gian">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity=".28" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((position) => {
          const gridY = padTop + position * (height - padTop - padBottom);
          const value = max - position * (max - min);
          return (
            <g key={position}>
              <line x1={padLeft} y1={gridY} x2={width - padRight} y2={gridY} stroke="var(--border)" strokeWidth="1" strokeDasharray="3 4" />
              <text x={padLeft - 8} y={gridY + 3} textAnchor="end" className="num" style={{ fontSize: 10, fill: "var(--text-3)" }}>{(value * 100).toFixed(0)}</text>
            </g>
          );
        })}
        <path d={area} fill={`url(#${gradientId})`} />
        <path d={line} fill="none" stroke={color} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        {markers.filter((marker) => series[marker.index]).map((marker) => {
          const markerX = x(marker.index);
          const markerColor = marker.direction === "POSITIVE" ? "var(--pos)" : "var(--neg)";
          return (
            <g key={`${marker.index}-${marker.direction}`}>
              <line x1={markerX} y1={padTop} x2={markerX} y2={height - padBottom} stroke={markerColor} strokeWidth="1.4" strokeDasharray="4 3" opacity=".7" />
              <circle cx={markerX} cy={y(series[marker.index].value)} r="5" fill={markerColor} stroke="var(--surface)" strokeWidth="2" />
            </g>
          );
        })}
        {series.map((point, index) => <text key={`${point.label}-${index}`} x={x(index)} y={height - 9} textAnchor="middle" className="num" style={{ fontSize: 10, fill: "var(--text-3)" }}>{point.label}</text>)}
      </svg>
    </div>
  );
}
