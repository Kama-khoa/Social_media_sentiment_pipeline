"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface ModalProps {
  open: boolean;
  title: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  size?: "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
}

const sizeClasses = {
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "3xl": "max-w-3xl",
  "4xl": "max-w-4xl",
};

export function Modal({ open, title, onClose, children, size = "md" }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <Card className={`relative max-h-[90vh] w-full ${sizeClasses[size]} overflow-y-auto shadow-[var(--shadow-lg)] [animation:pop_.15s_ease_both]`}>
        <div className="sticky top-0 flex items-start justify-between border-b border-[var(--border)] bg-[var(--surface)] px-6 pb-4 pt-5">
          <div className="flex-1 min-w-0 pr-4">
            {typeof title === "string" ? (
              <h2 className="text-base font-bold text-[var(--text)]">{title}</h2>
            ) : (
              title
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 text-[var(--text-3)] shrink-0"
            aria-label="Đóng hộp thoại"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </Card>
    </div>
  );
}
