import { Badge } from "@/components/ui/badge";

interface StatusBadgeProps {
  active: boolean;
  activeLabel?: string;
  inactiveLabel?: string;
}

export function StatusBadge({ active, activeLabel = "Đang hoạt động", inactiveLabel = "Đã tắt" }: StatusBadgeProps) {
  return <Badge variant={active ? "success" : "secondary"}>{active ? activeLabel : inactiveLabel}</Badge>;
}
