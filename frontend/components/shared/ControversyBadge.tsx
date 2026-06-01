interface Props {
  label: "high" | "medium" | "low";
}

const config = {
  high: { dot: "bg-rose-500", text: "text-rose-600", bg: "bg-rose-50", border: "border-rose-200", label: "Cao" },
  medium: { dot: "bg-amber-500", text: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200", label: "Trung bình" },
  low: { dot: "bg-emerald-500", text: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", label: "Thấp" },
};

export function ControversyBadge({ label }: Props) {
  const c = config[label];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.border} ${c.text} border`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}
