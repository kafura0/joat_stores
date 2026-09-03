"use client";

import { useEffect } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";
import { useUIStore } from "@/stores/uiStore";

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
};

const styles = {
  success:
    "bg-[var(--md-success-container)] text-[var(--md-success)] border-[var(--md-success)]/20",
  error:
    "bg-[var(--md-error-container)] text-[var(--md-error)] border-[var(--md-error)]/20",
  info:
    "bg-[var(--md-tertiary-container)] text-[var(--md-tertiary)] border-[var(--md-tertiary)]/20",
};

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

function Toast({
  toast,
  onDismiss,
}: {
  toast: { id: string; type: "success" | "error" | "info"; message: string };
  onDismiss: () => void;
}) {
  const Icon = icons[toast.type];

  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      className={`glass-panel flex items-center gap-3 rounded-xl border px-4 py-3 shadow-[var(--shadow-elevated)] backdrop-blur-md ${styles[toast.type]}`}
    >
      <Icon size={20} />
      <span className="text-sm font-medium">{toast.message}</span>
      <button
        onClick={onDismiss}
        className="ml-2 rounded-lg p-1 opacity-60 hover:opacity-100"
      >
        <X size={16} />
      </button>
    </div>
  );
}
