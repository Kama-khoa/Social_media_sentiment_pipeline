"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ open, title, onClose, children }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <Card className="relative max-h-[90vh] w-full max-w-md overflow-y-auto shadow-[var(--shadow-lg)] [animation:pop_.15s_ease_both]">
        <div className="sticky top-0 flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-6 pb-4 pt-5">
          <h2 className="text-base font-bold text-[var(--text)]">{title}</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 text-[var(--text-3)]"
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
