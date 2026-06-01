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
    score: parseFloat((a.positive_pct - a.negative_pct).toFixed(1)),
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis
          dataKey="aspect"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
        />
        <Radar
          name="Sentiment"
          dataKey="score"
          stroke="#06b6d4"
          fill="#06b6d4"
          fillOpacity={0.15}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 6,
            color: "#e2e8f0",
            fontSize: 12,
          }}
          formatter={(value: number) => [`${value > 0 ? "+" : ""}${value}%`, "Điểm cảm xúc"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
