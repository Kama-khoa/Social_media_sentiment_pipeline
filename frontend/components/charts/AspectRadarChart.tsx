"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { AspectSentiment } from "@/lib/types";

interface Props {
  aspects: AspectSentiment[];
}

export function AspectRadarChart({ aspects }: Props) {
  if (!aspects.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        Chưa có dữ liệu phân tích khía cạnh
      </div>
    );
  }

  const data = aspects.map((a) => ({
    aspect: a.aspect_label,
    score: parseFloat(a.positive_pct.toFixed(1)),
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid stroke="var(--border)" />
        <PolarAngleAxis
          dataKey="aspect"
          tick={{ fill: "var(--text-2)", fontSize: 12, fontWeight: 600 }}
        />
        <Radar
          name="Sentiment"
          dataKey="score"
          stroke="var(--primary)"
          fill="var(--primary)"
          fillOpacity={0.18}
          strokeWidth={2}
          style={{ transformOrigin: "center", animation: "radarPop .7s cubic-bezier(.2,.8,.2,1)" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            color: "var(--text)",
            fontSize: 12,
          }}
          formatter={(value: number) => [`${value > 0 ? "+" : ""}${value}%`, "Điểm cảm xúc"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
