"use client";

interface SentimentBarProps {
  positivePct: number;
  negativePct: number;
  neutralPct?: number;
  height?: number;
}

export function SentimentBar({ positivePct, negativePct, neutralPct, height = 6 }: SentimentBarProps) {
  const positive = Math.max(0, positivePct);
  const negative = Math.max(0, negativePct);
  const neutral = Math.max(0, neutralPct ?? 100 - positive - negative);
  const total = positive + neutral + negative;
  const width = (value: number) => total > 0 ? `${value / total * 100}%` : "0%";

  return (
    <div
      className="flex w-full overflow-hidden rounded-full bg-[var(--surface-3)]"
      style={{ height }}
      role="img"
      aria-label={`Cảm xúc: ${positive.toFixed(1)}% tích cực, ${neutral.toFixed(1)}% trung lập, ${negative.toFixed(1)}% tiêu cực`}
    >
      {positive > 0 && (
        <div
          style={{ width: width(positive), background: "var(--pos)", transition: "width .6s ease" }}
          title={`Tích cực: ${positive.toFixed(1)}%`}
        />
      )}
      {neutral > 0 && (
        <div
          style={{ width: width(neutral), background: "var(--neu)", transition: "width .6s ease" }}
          title={`Trung lập: ${neutral.toFixed(1)}%`}
        />
      )}
      {negative > 0 && (
        <div
          style={{ width: width(negative), background: "var(--neg)", transition: "width .6s ease" }}
          title={`Tiêu cực: ${negative.toFixed(1)}%`}
        />
      )}
    </div>
  );
}
