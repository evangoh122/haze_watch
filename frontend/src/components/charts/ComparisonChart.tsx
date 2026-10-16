import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface ComparisonRow {
  label: string;
  baseline: number | null;
  stressed: number | null;
}

/** Baseline vs scenario comparison chart answering one question per metric set. */
export default function ComparisonChart({
  data,
  unit,
  title,
}: {
  data: ComparisonRow[];
  unit: string;
  title?: string;
}) {
  return (
    <div className="rounded-md border border-line bg-surface-elevated p-4">
      {title && (
        <h3 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-[0.09em] text-muted">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#dce3eb" />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6f7b8e" }} />
          <YAxis tick={{ fontSize: 11, fill: "#6f7b8e" }} unit={unit} />
          <Tooltip
            formatter={(value) =>
              value === null || value === undefined ? "n.m." : `${Number(value).toFixed(2)}`
            }
          />
          <Legend />
          <Bar dataKey="baseline" name="Baseline" fill="#16856b" radius={[3, 3, 0, 0]} />
          <Bar dataKey="stressed" name="Scenario" fill="#c27821" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
