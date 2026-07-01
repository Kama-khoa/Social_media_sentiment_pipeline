import { Icon, type IconName } from "@/components/shared/Icon";

export function bayesScore100(score: number) {
  return Math.max(0, Math.min(100, (score + 1) * 50));
}

export function hasEnoughBayesData(statementCount?: number) {
  return statementCount === undefined || statementCount >= 5;
}

export function ScoreRing({ score, size = 92, statementCount }: { score: number; size?: number; statementCount?: number }) {
  const radius = size / 2 - 7;
  const circumference = 2 * Math.PI * radius;
  const enoughData = hasEnoughBayesData(statementCount);
  const score100 = enoughData ? bayesScore100(score) : 0;
  const dash = score100 / 100 * circumference;
  const center = size / 2;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: size, height: size }}>
      <circle cx={center} cy={center} r={radius} fill="none" stroke="var(--surface-3)" strokeWidth="7" />
      <circle cx={center} cy={center} r={radius} fill="none" stroke="var(--primary)" strokeWidth="7" strokeLinecap="round" strokeDasharray={`${dash} ${circumference - dash}`} transform={`rotate(-90 ${center} ${center})`} style={{ transition: "stroke-dasharray 1s ease" }} />
      <text x={center} y={center + 1} textAnchor="middle" className="num" style={{ fontSize: enoughData ? 19 : 13, fontWeight: 700, fill: "var(--text)" }}>{enoughData ? score100.toFixed(0) : "N/A"}</text>
      <text x={center} y={center + 15} textAnchor="middle" style={{ fontSize: 7.5, fill: "var(--text-3)", fontWeight: 600 }}>BAYES</text>
    </svg>
  );
}

export function Donut({ positive, negative, neutral, size = 150 }: { positive: number; negative: number; neutral: number; size?: number }) {
  const radius = size / 2 - 12;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;
  const segments = [
    { value: Math.max(0, positive), color: "var(--pos)" },
    { value: Math.max(0, neutral), color: "var(--neu)" },
    { value: Math.max(0, negative), color: "var(--neg)" },
  ];
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  let offset = 0;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: size, height: size }}>
      <circle cx={center} cy={center} r={radius} fill="none" stroke="var(--surface-3)" strokeWidth="14" />
      {segments.map(({ value, color }) => {
        const dash = (total > 0 ? value / total : 0) * circumference;
        const currentOffset = offset;
        offset += dash;
        return <circle key={color} cx={center} cy={center} r={radius} fill="none" stroke={color} strokeWidth="14" strokeDasharray={`${dash} ${circumference - dash}`} strokeDashoffset={-currentOffset} strokeLinecap="round" transform={`rotate(-90 ${center} ${center})`} style={{ transition: "stroke-dasharray .8s ease" }} />;
      })}
      <text x={center} y={center - 2} textAnchor="middle" className="num" style={{ fontSize: 22, fontWeight: 700, fill: "var(--text)" }}>{positive.toFixed(0)}%</text>
      <text x={center} y={center + 16} textAnchor="middle" style={{ fontSize: 10, fill: "var(--text-3)", fontWeight: 600 }}>hài lòng</text>
    </svg>
  );
}

export function Sparkline({ data, color = "var(--primary)", width = 200, height = 34 }: { data: number[]; color?: string; width?: number; height?: number }) {
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const x = (index: number) => index / Math.max(1, data.length - 1) * width;
  const y = (value: number) => height - 3 - (value - min) / (max - min || 1) * (height - 6);
  const line = data.map((value, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(value)}`).join(" ");
  return <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height }}><path d={`${line} L${width},${height} L0,${height} Z`} fill={color} fillOpacity=".14" /><path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

export function KpiCard({ icon, label, value, sub, trend, spark, accent = "var(--primary)" }: { icon: IconName; label: string; value: string | number; sub?: string; trend?: number; spark?: number[]; accent?: string }) {
  return (
    <div className="card fade-up flex flex-col gap-3.5 p-5 justify-between">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl" style={{ background: `color-mix(in oklab, ${accent} 14%, transparent)`, color: accent }}>
          <Icon name={icon} size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[15px] font-extrabold text-[var(--text)] leading-tight">{label}</div>
        </div>
        {trend !== undefined && <span className={`chip shrink-0 ${trend >= 0 ? "pos" : "neg"}`}><Icon name={trend >= 0 ? "arrowUp" : "arrowDown"} size={12} />{Math.abs(trend)}%</span>}
      </div>
      <div>
        <div className="num text-[28px] font-bold leading-none">{value}</div>
        {sub && <div className="faint mt-1.5 text-xs font-semibold">{sub}</div>}
      </div>
      {spark && <Sparkline data={spark} color={accent} />}
    </div>
  );
}

export function BarChart({ data, height = 210, color = "var(--primary)" }: { data: Array<{ label: string; value: number }>; height?: number; color?: string }) {
  if (!data.length) return <div className="faint grid h-48 place-items-center text-sm">Chưa có dữ liệu biểu đồ.</div>;
  const max = Math.max(...data.map((item) => item.value), 0) * 1.1 || 1;
  return <div className="flex items-end gap-2 pt-2" style={{ height }}>{data.map((item, index) => <div key={`${item.label}-${index}`} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5"><span className="num text-[11px] font-bold text-[var(--text-2)]">{item.value}</span><div className="w-full max-w-[38px] origin-bottom rounded-t-lg rounded-b-sm" style={{ height: Math.max(0, item.value) / max * (height - 44), animation: "growBar .6s ease both", background: `linear-gradient(180deg, ${color}, color-mix(in oklab, ${color} 55%, transparent))` }} /><span className="text-[10px] font-semibold text-[var(--text-3)]">{item.label}</span></div>)}</div>;
}
