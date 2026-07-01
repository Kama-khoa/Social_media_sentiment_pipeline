import { cn } from "@/lib/utils";

interface SwitchProps {
  checked: boolean;
  onClick?: () => void;
  disabled?: boolean;
  label: string;
  className?: string;
}

export function Switch({ checked, onClick, disabled, label, className }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className={cn("focusable flex h-[23px] w-10 items-center rounded-full p-0.5 transition-colors disabled:cursor-not-allowed disabled:opacity-60", checked ? "justify-end bg-[var(--primary)]" : "justify-start bg-[var(--border-strong)]", className)}
    >
      <span className="h-[19px] w-[19px] rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,.3)] transition-all" />
    </button>
  );
}
