import type { TraceStep } from "../../lib/types";

/** Collapsible, auditable calculation trace (workbench metric-table style). */
export default function CalculationTrace({ trace }: { trace: TraceStep[] }) {
  return (
    <details className="rounded-md border border-line bg-surface-elevated">
      <summary className="cursor-pointer px-4 py-3 text-[13px] font-medium text-ink">
        Calculation trace ({trace.length} steps)
      </summary>
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-line">
            <th className="px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
              Step
            </th>
            <th className="px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
              Formula
            </th>
            <th className="px-4 py-2 text-right font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
              Value
            </th>
          </tr>
        </thead>
        <tbody>
          {trace.map((step) => (
            <tr key={step.label} className="border-b border-[#eef1f5]">
              <td className="px-4 py-2 text-[13px] text-[#33445b]">{step.label}</td>
              <td className="px-4 py-2 font-mono text-[11px] text-muted">{step.formula}</td>
              <td className="whitespace-nowrap px-4 py-2 text-right font-mono text-[13px] text-ink">
                {step.value.toFixed(2)} {step.unit}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
