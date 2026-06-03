// Card, Button, and Section primitives + a tiny toast system.
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { create } from "zustand";

export function Card({
  children,
  className = "",
  title,
  subtitle,
  action,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div
      className={`rounded-lg border border-surface-border bg-surface-card ${className}`}
    >
      {(title || action) && (
        <div className="flex items-start justify-between gap-2 border-b border-surface-border px-4 py-3">
          <div>
            {title && (
              <h2 className="text-sm font-semibold text-zinc-200">{title}</h2>
            )}
            {subtitle && <p className="text-xs text-zinc-500">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

type Variant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-signal-neutral/20 text-zinc-100 ring-1 ring-inset ring-signal-neutral/40 hover:bg-signal-neutral/30",
  secondary:
    "bg-surface-card text-zinc-300 ring-1 ring-inset ring-surface-border hover:bg-surface-border",
  ghost: "text-zinc-400 hover:text-zinc-200",
};

export function Button({
  children,
  variant = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

// --- Toasts --------------------------------------------------------------------------

interface Toast {
  id: number;
  message: string;
  tone: "success" | "error";
}

interface ToastState {
  toasts: Toast[];
  push: (message: string, tone?: "success" | "error") => void;
  dismiss: (id: number) => void;
}

let nextId = 1;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (message, tone = "success") => {
    const id = nextId++;
    set((s) => ({ toasts: [...s.toasts, { id, message, tone }] }));
    setTimeout(
      () => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
      4000
    );
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export function Toaster() {
  const { toasts, dismiss } = useToastStore();
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          onClick={() => dismiss(t.id)}
          className={`cursor-pointer rounded-lg border px-4 py-2 text-sm shadow-lg ${
            t.tone === "success"
              ? "border-signal-profit/40 bg-surface-card text-signal-profit"
              : "border-signal-loss/40 bg-surface-card text-signal-loss"
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
