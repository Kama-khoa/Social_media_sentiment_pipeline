import * as React from "react";
import { cn } from "@/lib/utils";

export interface DropdownOption {
  value: string;
  label: string;
}

export interface DropdownProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  options: DropdownOption[];
  placeholder?: string;
}

export const Dropdown = React.forwardRef<HTMLSelectElement, DropdownProps>(
  ({ className, options, placeholder, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "focusable h-10 w-full appearance-none rounded-[10px] border border-[var(--border-strong)] bg-[var(--surface-2)] px-3 py-2 pr-9 text-sm font-semibold text-[var(--text)] disabled:cursor-not-allowed disabled:opacity-60",
          className,
        )}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-3)]">
        <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
          <path d="m6 9 6 6 6-6" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </svg>
      </span>
    </div>
  ),
);
Dropdown.displayName = "Dropdown";
