"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function Dialog({ open, onClose, title, children }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-0 shadow-[var(--shadow-dialog)] backdrop:bg-black/50 backdrop:backdrop-blur-sm"
    >
      <div className="flex items-center justify-between border-b border-[var(--md-outline-variant)] px-6 py-4">
        <h2 className="text-lg font-semibold text-[var(--md-on-surface)]">{title}</h2>
        <button
          onClick={onClose}
          className="rounded-lg p-1 text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-variant)]"
          style={{ minHeight: 48, minWidth: 48 }}
        >
          <X size={20} />
        </button>
      </div>
      <div className="px-6 py-4">{children}</div>
    </dialog>
  );
}
