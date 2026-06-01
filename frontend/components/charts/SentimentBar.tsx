"use client";

interface SentimentBarProps {
  positivePct: number;
  negativePct: number;
  height?: number;
}

export function SentimentBar({ positivePct, negativePct, height = 6 }: SentimentBarProps) {
  const neutralPct = Math.max(0, 100 - positivePct - negativePct);
  return (
    <div className="flex rounded-full overflow-hidden w-full" style={{ height }}>
      {positivePct > 0 && (
        <div
          className="bg-emerald-500"
          style={{ width: `${positivePct}%` }}
          title={`Tích cực: ${positivePct.toFixed(1)}%`}
        />
      )}
      {neutralPct > 0 && (
        <div
          className="bg-slate-600"
          style={{ width: `${neutralPct}%` }}
          title={`Trung lập: ${neutralPct.toFixed(1)}%`}
        />
      )}
      {negativePct > 0 && (
        <div
          className="bg-rose-500"
          style={{ width: `${negativePct}%` }}
          title={`Tiêu cực: ${negativePct.toFixed(1)}%`}
        />
      )}
    </div>
  );
}
