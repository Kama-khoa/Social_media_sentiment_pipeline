interface Props {
  label: string;
}

const CONFIG: Record<string, { text: string; cls: string }> = {
  high: { text: "Tranh cãi cao", cls: "bg-rose-500/20 text-rose-400 border border-rose-500/30" },
  medium: { text: "Trung bình", cls: "bg-amber-500/20 text-amber-400 border border-amber-500/30" },
  low: { text: "Nhất quán", cls: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" },
  cao: { text: "Tranh cãi cao", cls: "bg-rose-500/20 text-rose-400 border border-rose-500/30" },
  "trung bình": { text: "Trung bình", cls: "bg-amber-500/20 text-amber-400 border border-amber-500/30" },
  thấp: { text: "Nhất quán", cls: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" },
};

export function ControversyBadgeDark({ label }: Props) {
  const cfg = CONFIG[label] ?? { text: label, cls: "bg-slate-700 text-slate-400 border border-slate-600" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.text}
    </span>
  );
}
