import type { ReactNode } from "react";

type Tone = "neutral" | "ok" | "warn" | "alert";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "border-line bg-surface-elevated",
  ok: "border-[#bfe5d8] bg-greenbg",
  warn: "border-[#ecd3ac] bg-amberbg",
  alert: "border-[#e8b4b4] bg-rosebg",
};

export interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  tone?: Tone;
  badge?: ReactNode;
}

/** Metric tile (RAG workbench .metric style): mono value, uppercase label. */
export default function KpiCard({ label, value, sub, tone = "neutral", badge }: KpiCardProps) {
  return (
    <div className={`rounded-md border p-4 ${TONE_CLASSES[tone]}`}>
      <div className="flex items-start justify-between gap-2">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">
          {label}
        </p>
        {badge}
      </div>
      <p className="mt-2 font-mono text-xl font-semibold text-ink">{value}</p>
      {sub && <p className="mt-1 text-[11px] text-muted">{sub}</p>}
    </div>
  );
}
