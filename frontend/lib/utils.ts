export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function calculateControversyLabel(positivePct: number, negativePct: number): "high" | "medium" | "low" {
  if (negativePct > 25) return "high";
  if (negativePct >= 10) return "medium";
  return "low";
}

