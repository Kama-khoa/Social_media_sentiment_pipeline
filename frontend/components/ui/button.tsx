import * as React from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "default" | "secondary" | "outline" | "ghost" | "destructive" | "success";
type ButtonSize = "default" | "sm" | "lg" | "icon";

const variantClasses: Record<ButtonVariant, string> = {
  default: "bg-[var(--primary)] text-[var(--on-primary)] shadow-[0_6px_16px_-6px_var(--ring)] hover:bg-[var(--primary-hover)] hover:-translate-y-px",
  secondary: "bg-[var(--primary-soft)] text-[var(--primary)] hover:bg-[var(--primary-soft-2)]",
  outline: "border border-[var(--border-strong)] bg-transparent text-[var(--text-2)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]",
  ghost: "text-[var(--text-2)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]",
  destructive: "bg-[var(--neg)] text-white shadow-sm hover:brightness-90",
  success: "bg-[var(--pos)] text-white shadow-sm hover:brightness-90",
};

const sizeClasses: Record<ButtonSize, string> = {
  default: "h-10 px-4 py-2",
  sm: "h-8 rounded-md px-3 text-xs",
  lg: "h-11 rounded-lg px-6",
  icon: "h-9 w-9",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--ring)] disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
