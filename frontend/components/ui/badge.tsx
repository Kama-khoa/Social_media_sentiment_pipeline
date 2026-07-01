import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "secondary" | "success" | "warning" | "destructive" | "brand" | "outline";

const variantClasses: Record<BadgeVariant, string> = {
  default: "chip",
  secondary: "chip",
  success: "chip pos",
  warning: "chip neu",
  destructive: "chip neg",
  brand: "chip brand",
  outline: "chip bg-transparent",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(variantClasses[variant], className)}
      {...props}
    />
  );
}
