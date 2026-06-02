/* ============================================================
   TechChoice — Shared components & SVG charts
   exports to window
   ============================================================ */
const { useState, useEffect, useRef, useMemo } = React;

/* ---------------- Icons (stroke, inherit currentColor) ---------------- */
function Icon({ name, size = 18, style }) {
  const s = { width: size, height: size, display: "block", flexShrink: 0, ...style };
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };
  const paths = {
    search: <><circle cx="11" cy="11" r="7" {...p} /><path d="M21 21l-4.3-4.3" {...p} /></>,
    trophy: <><path d="M7 4h10v4a5 5 0 0 1-10 0V4Z" {...p} /><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3M9 18h6M10 18l.5-3h3l.5 3M8 21h8" {...p} /></>,
    sun: <><circle cx="12" cy="12" r="4" {...p} /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" {...p} /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" {...p} />,
    user: <><circle cx="12" cy="8" r="4" {...p} /><path d="M5 21a7 7 0 0 1 14 0" {...p} /></>,
    chevron: <path d="m6 9 6 6 6-6" {...p} />,
    logout: <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H3" {...p} /></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16" {...p} />,
    close: <path d="M6 6l12 12M18 6 6 18" {...p} />,
    gauge: <><path d="M12 13l4-3" {...p} /><path d="M4.5 18a9 9 0 1 1 15 0" {...p} /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" {...p} /><rect x="14" y="3" width="7" height="7" rx="1.5" {...p} /><rect x="3" y="14" width="7" height="7" rx="1.5" {...p} /><rect x="14" y="14" width="7" height="7" rx="1.5" {...p} /></>,
    broadcast: <><circle cx="12" cy="12" r="2" {...p} /><path d="M8.5 8.5a5 5 0 0 0 0 7M15.5 8.5a5 5 0 0 1 0 7M6 6a9 9 0 0 0 0 12M18 6a9 9 0 0 1 0 12" {...p} /></>,
    tag: <><path d="M3 12V5a2 2 0 0 1 2-2h7l9 9-9 9-9-9Z" {...p} /><circle cx="7.5" cy="7.5" r="1.2" fill="currentColor" stroke="none" /></>,
    box: <><path d="M21 8 12 3 3 8l9 5 9-5Z" {...p} /><path d="M3 8v8l9 5 9-5V8M12 13v8" {...p} /></>,
    heart: <path d="M19 14c1.5-1.5 3-3.3 3-5.6A3.9 3.9 0 0 0 12 5 3.9 3.9 0 0 0 2 8.4c0 2.3 1.5 4.1 3 5.6l7 7 7-7Z" {...p} />,
    flow: <><circle cx="5" cy="6" r="2.4" {...p} /><circle cx="5" cy="18" r="2.4" {...p} /><circle cx="19" cy="12" r="2.4" {...p} /><path d="M7.4 6H13a3.5 3.5 0 0 1 3.5 3.5M7.4 18H13a3.5 3.5 0 0 0 3.5-3.5" {...p} /></>,
    activity: <path d="M3 12h4l2 7 4-16 2 9h6" {...p} />,
    shield: <path d="M12 3 4 6v6c0 5 3.5 7.5 8 9 4.5-1.5 8-4 8-9V6l-8-3Z" {...p} />,
    bell: <><path d="M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8" {...p} /><path d="M10.3 21a2 2 0 0 0 3.4 0" {...p} /></>,
    arrowUp: <path d="M12 19V5M5 12l7-7 7 7" {...p} />,
    arrowDown: <path d="M12 5v14M5 12l7 7 7-7" {...p} />,
    check: <path d="M20 6 9 17l-5-5" {...p} />,
    play: <path d="M7 4v16l13-8-13-8Z" {...p} fill="currentColor" stroke="none" />,
    plus: <path d="M12 5v14M5 12h14" {...p} />,
    edit: <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" {...p} />,
    trash: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" {...p} />,
    filter: <path d="M3 5h18l-7 8v6l-4-2v-4L3 5Z" {...p} />,
    spec: <><rect x="4" y="3" width="16" height="18" rx="2" {...p} /><path d="M8 8h8M8 12h8M8 16h5" {...p} /></>,
    clock: <><circle cx="12" cy="12" r="9" {...p} /><path d="M12 7v5l3 2" {...p} /></>,
    refresh: <path d="M4 12a8 8 0 0 1 13.7-5.6L20 8M20 4v4h-4M20 12a8 8 0 0 1-13.7 5.6L4 16m0 4v-4h4" {...p} />,
    server: <><rect x="3" y="4" width="18" height="7" rx="2" {...p} /><rect x="3" y="13" width="18" height="7" rx="2" {...p} /><path d="M7 7.5h.01M7 16.5h.01" {...p} /></>,
    spark: <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2" {...p} />,
    external: <path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" {...p} />,
  };
  return <svg viewBox="0 0 24 24" style={s} aria-hidden="true">{paths[name]}</svg>;
}

/* ---------------- Sentiment bar ---------------- */
function SentimentBar({ pos, neg, neu, height = 10 }) {
  const n = neu != null ? neu : Math.max(0, 100 - pos - neg);
  return (
    <div style={{ display: "flex", height, borderRadius: 99, overflow: "hidden", background: "var(--surface-3)" }}>
      <div style={{ width: pos + "%", background: "var(--pos)", transition: "width .6s ease" }} />
      <div style={{ width: n + "%", background: "var(--neu)", transition: "width .6s ease" }} />
      <div style={{ width: neg + "%", background: "var(--neg)", transition: "width .6s ease" }} />
    </div>
  );
}

/* ---------------- Radar chart (6 aspects) ---------------- */
function RadarChart({ aspects, size = 320 }) {
  const cx = size / 2, cy = size / 2, R = size * 0.36;
  const n = aspects.length;
  const angle = i => (Math.PI * 2 * i) / n - Math.PI / 2;
  const point = (i, r) => [cx + Math.cos(angle(i)) * R * r, cy + Math.sin(angle(i)) * R * r];
  const rings = [0.25, 0.5, 0.75, 1];
  const poly = (vals) => vals.map((v, i) => point(i, v).join(",")).join(" ");
  const posVals = aspects.map(a => a.positive_pct / 100);
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: "100%", height: "auto", maxWidth: size, margin: "0 auto", display: "block" }}>
      {rings.map((r, i) => (
        <polygon key={i} points={poly(aspects.map(() => r))} fill="none" stroke="var(--border)" strokeWidth="1" />
      ))}
      {aspects.map((_, i) => {
        const [x, y] = point(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--border)" strokeWidth="1" />;
      })}
      <polygon points={poly(posVals)}
        fill="var(--primary)" fillOpacity="0.18" stroke="var(--primary)" strokeWidth="2.2"
        style={{ transformOrigin: "center", animation: "radarPop .7s cubic-bezier(.2,.8,.2,1)" }} />
      {posVals.map((v, i) => { const [x, y] = point(i, v); return <circle key={i} cx={x} cy={y} r="3.5" fill="var(--primary)" />; })}
      {aspects.map((a, i) => {
        const [x, y] = point(i, 1.2);
        return <text key={i} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
          style={{ fontSize: 11, fontWeight: 600, fill: "var(--text-2)", fontFamily: "var(--font-ui)" }}>{a.aspect_label}</text>;
      })}
    </svg>
  );
}

/* ---------------- Area/line chart ---------------- */
function AreaChart({ series, height = 240, color = "var(--primary)", markers = [], yLabel = "" }) {
  const ref = useRef(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(e => setW(e[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  const padL = 38, padR = 14, padT = 16, padB = 28;
  const vals = series.map(s => s.value);
  const min = Math.min(...vals) * 0.92, max = Math.max(...vals) * 1.04;
  const X = i => padL + (i / (series.length - 1)) * (w - padL - padR);
  const Y = v => padT + (1 - (v - min) / (max - min)) * (height - padT - padB);
  const line = series.map((s, i) => `${i === 0 ? "M" : "L"}${X(i)},${Y(s.value)}`).join(" ");
  const area = `${line} L${X(series.length - 1)},${height - padB} L${X(0)},${height - padB} Z`;
  const id = useMemo(() => "g" + Math.random().toString(36).slice(2, 7), []);
  return (
    <div ref={ref} style={{ width: "100%" }}>
      <svg viewBox={`0 0 ${w} ${height}`} style={{ width: "100%", height }}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.28" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((t, i) => {
          const y = padT + t * (height - padT - padB);
          const v = max - t * (max - min);
          return (<g key={i}>
            <line x1={padL} y1={y} x2={w - padR} y2={y} stroke="var(--border)" strokeWidth="1" strokeDasharray="3 4" />
            <text x={padL - 8} y={y + 3} textAnchor="end" style={{ fontSize: 10, fill: "var(--text-3)", fontFamily: "var(--font-num)" }}>{(v * 100).toFixed(0)}</text>
          </g>);
        })}
        <path d={area} fill={`url(#${id})`} />
        <path d={line} fill="none" stroke={color} strokeWidth="2.6" strokeLinecap="round" />
        {markers.map((m, i) => {
          const x = X(m.index);
          return (<g key={i}>
            <line x1={x} y1={padT} x2={x} y2={height - padB} stroke={m.dir === "POSITIVE" ? "var(--pos)" : "var(--neg)"} strokeWidth="1.4" strokeDasharray="4 3" opacity="0.7" />
            <circle cx={x} cy={Y(series[m.index].value)} r="5" fill={m.dir === "POSITIVE" ? "var(--pos)" : "var(--neg)"} stroke="var(--surface)" strokeWidth="2" />
          </g>);
        })}
        {series.map((s, i) => (
          <text key={i} x={X(i)} y={height - 9} textAnchor="middle" style={{ fontSize: 10, fill: "var(--text-3)", fontFamily: "var(--font-num)" }}>{s.label}</text>
        ))}
      </svg>
    </div>
  );
}

/* ---------------- Mini bar chart ---------------- */
function BarChart({ data, height = 200, color = "var(--primary)" }) {
  const max = Math.max(...data.map(d => d.value)) * 1.1;
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height, paddingTop: 10 }}>
      {data.map((d, i) => {
        const full = (d.value / max) * (height - 44);
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6, height: "100%", justifyContent: "flex-end" }}>
            <span className="num" style={{ fontSize: 11, fontWeight: 700, color: "var(--text-2)" }}>{d.value}</span>
            <div title={d.label} style={{
              width: "100%", maxWidth: 38, height: full,
              background: `linear-gradient(180deg, ${color}, color-mix(in oklab, ${color} 55%, transparent))`,
              borderRadius: "8px 8px 4px 4px",
            }} />
            <span style={{ fontSize: 10, color: "var(--text-3)", fontWeight: 600 }}>{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------------- Sparkline ---------------- */
function Sparkline({ data, color = "var(--primary)", width = 120, height = 40 }) {
  const min = Math.min(...data), max = Math.max(...data);
  const X = i => (i / (data.length - 1)) * width;
  const Y = v => height - 3 - ((v - min) / (max - min || 1)) * (height - 6);
  const line = data.map((v, i) => `${i === 0 ? "M" : "L"}${X(i)},${Y(v)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width, height }}>
      <path d={`${line} L${width},${height} L0,${height} Z`} fill={color} fillOpacity="0.14" />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ---------------- Donut ---------------- */
function Donut({ pos, neg, neu, size = 130 }) {
  const r = size / 2 - 12, c = 2 * Math.PI * r, cx = size / 2;
  const segs = [{ v: pos, col: "var(--pos)" }, { v: neu, col: "var(--neu)" }, { v: neg, col: "var(--neg)" }];
  let off = 0;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: size, height: size }}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--surface-3)" strokeWidth="14" />
      {segs.map((s, i) => {
        const dash = (s.v / 100) * c;
        const el = <circle key={i} cx={cx} cy={cx} r={r} fill="none" stroke={s.col} strokeWidth="14"
          strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={-off} strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`} style={{ transition: "stroke-dasharray .8s ease" }} />;
        off += dash; return el;
      })}
      <text x={cx} y={cx - 2} textAnchor="middle" className="num" style={{ fontSize: 22, fontWeight: 700, fill: "var(--text)" }}>{pos}%</text>
      <text x={cx} y={cx + 16} textAnchor="middle" style={{ fontSize: 10, fill: "var(--text-3)", fontWeight: 600 }}>tích cực</text>
    </svg>
  );
}

/* ---------------- KPI card ---------------- */
function KpiCard({ icon, label, value, sub, trend, accent = "var(--primary)", spark }) {
  return (
    <div className="card fade-up" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ width: 40, height: 40, borderRadius: 12, display: "grid", placeItems: "center",
          background: "color-mix(in oklab, " + accent + " 14%, transparent)", color: accent }}>
          <Icon name={icon} size={20} />
        </div>
        {trend != null && (
          <span className="chip" style={{ background: trend >= 0 ? "var(--pos-soft)" : "var(--neg-soft)", color: trend >= 0 ? "var(--pos)" : "var(--neg)", border: "none" }}>
            <Icon name={trend >= 0 ? "arrowUp" : "arrowDown"} size={12} />{Math.abs(trend)}%
          </span>
        )}
      </div>
      <div>
        <div className="num" style={{ fontSize: 28, fontWeight: 700, lineHeight: 1.1 }}>{value}</div>
        <div className="muted" style={{ fontSize: 13, marginTop: 4, fontWeight: 500 }}>{label}</div>
        {sub && <div className="faint" style={{ fontSize: 12, marginTop: 2 }}>{sub}</div>}
      </div>
      {spark && <Sparkline data={spark} width={200} height={34} />}
    </div>
  );
}

/* ---------------- Score ring ---------------- */
function ScoreRing({ score, size = 92 }) {
  const r = size / 2 - 7, c = 2 * Math.PI * r, cx = size / 2;
  const pct = score; const dash = pct * c;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: size, height: size }}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--surface-3)" strokeWidth="7" />
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--primary)" strokeWidth="7" strokeLinecap="round"
        strokeDasharray={`${dash} ${c - dash}`} transform={`rotate(-90 ${cx} ${cx})`} style={{ transition: "stroke-dasharray 1s ease" }} />
      <text x={cx} y={cx + 1} textAnchor="middle" className="num" style={{ fontSize: 19, fontWeight: 700, fill: "var(--text)" }}>{(score * 100).toFixed(0)}</text>
      <text x={cx} y={cx + 15} textAnchor="middle" style={{ fontSize: 8.5, fill: "var(--text-3)", fontWeight: 600 }}>BAYES</text>
    </svg>
  );
}

function controversyChip(label) {
  const map = { low: ["Ít tranh cãi", "pos"], medium: ["Tranh cãi vừa", "neu"], high: ["Nhiều tranh cãi", "neg"] };
  const [t, cls] = map[label] || ["—", ""];
  return <span className={"chip " + cls}>{t}</span>;
}

Object.assign(window, { Icon, SentimentBar, RadarChart, AreaChart, BarChart, Sparkline, Donut, KpiCard, ScoreRing, controversyChip });
