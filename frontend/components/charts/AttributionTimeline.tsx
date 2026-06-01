"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { CausalEventSummary } from "@/lib/types";

interface TimelinePoint {
  date: string;
  score: number;
}

interface Props {
  events: CausalEventSummary[];
}

function buildTimelineFromEvents(events: CausalEventSummary[]): TimelinePoint[] {
  if (!events.length) return [];
  const sorted = [...events].sort((a, b) => a.change_point_date.localeCompare(b.change_point_date));
  return sorted.map((e, i) => ({
    date: e.change_point_date,
    score: e.sentiment_direction === "POSITIVE" ? 0.3 + i * 0.1 : -0.3 - i * 0.1,
  }));
}

export function AttributionTimeline({ events }: Props) {
  const data = buildTimelineFromEvents(events);
  if (!data.length) return null;

  const changeDates = events.map((e) => ({
    date: e.change_point_date,
    direction: e.sentiment_direction,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#64748b", fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: "#334155" }}
        />
        <YAxis
          tick={{ fill: "#64748b", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          domain={[-1, 1]}
          tickFormatter={(v) => (v > 0 ? `+${v}` : `${v}`)}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 6,
            color: "#e2e8f0",
            fontSize: 12,
          }}
        />
        {changeDates.map((cp) => (
          <ReferenceLine
            key={cp.date}
            x={cp.date}
            stroke={cp.direction === "POSITIVE" ? "#10b981" : "#f43f5e"}
            strokeDasharray="4 2"
            strokeWidth={1.5}
          />
        ))}
        <Line
          type="monotone"
          dataKey="score"
          stroke="#06b6d4"
          strokeWidth={2}
          dot={{ fill: "#06b6d4", r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
