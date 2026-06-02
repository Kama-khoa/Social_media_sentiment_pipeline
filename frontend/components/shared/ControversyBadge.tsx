interface Props {
  label: "high" | "medium" | "low";
}

const config = {
  high: { className: "chip neg", label: "Nhiều tranh cãi" },
  medium: { className: "chip neu", label: "Tranh cãi vừa" },
  low: { className: "chip pos", label: "Ít tranh cãi" },
};

export function ControversyBadge({ label }: Props) {
  const item = config[label];
  return <span className={item.className}>{item.label}</span>;
}
