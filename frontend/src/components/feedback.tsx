// LoadingSpinner, ErrorState, EmptyState, Divider, PageHeader — small shared primitives.
import type { ReactNode } from "react";

export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-zinc-500">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-surface-border border-t-signal-neutral" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div className="text-sm text-signal-loss">⚠ {message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded border border-surface-border bg-surface-card px-3 py-1.5 text-sm text-zinc-300 hover:bg-surface-border"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <div className="text-sm font-medium text-zinc-400">{title}</div>
      {children && <div className="text-xs text-zinc-500">{children}</div>}
    </div>
  );
}

export function Divider({ className = "" }: { className?: string }) {
  return <hr className={`border-surface-border ${className}`} />;
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
