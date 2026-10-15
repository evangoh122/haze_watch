import { useEffect, useState } from "react";
import { getForecasts, type ForecastResponse } from "../lib/dataApi";

const HORIZONS = [24, 48, 72];

function scoreBand(score: number): { label: string; text: string; bar: string } {
  if (score >= 0.6) return { label: "HIGH", text: "text-rose", bar: "bg-rose" };
  if (score >= 0.35) return { label: "ELEVATED", text: "text-amber", bar: "bg-amber" };
  return { label: "LOW", text: "text-green", bar: "bg-green" };
}

/** Fire forecast dashboard: baseline hazard scores by horizon (labeled baseline). */
export default function FireForecast() {
  const [horizon, setHorizon] = useState(24);
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    getForecasts(horizon, 25)
      .then(setData)
      .catch(() => setError("Forecast dataset not available. Run the ingestion pipeline first."));
  }, [horizon]);

  return (
    <div className="space-y-5">
      <div>
        <p className="eyebrow">Monitor / Fire forecast</p>
        <h1 className="mt-1 text-xl font-semibold text-ink">Fire hazard baseline</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">
          Deterministic persistence/recency baseline over the concession portfolio. This is a
          labeled floor for future ML models - not a calibrated probability and not a validated
          forecast.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-surface-elevated px-4 py-3">
        <span className="eyebrow">Forecast horizon</span>
        <div className="flex gap-2">
          {HORIZONS.map((hours) => (
            <button
              key={hours}
              onClick={() => setHorizon(hours)}
              className={`rounded border px-3 py-1.5 font-mono text-xs ${
                horizon === hours
                  ? "border-accent-fill bg-accent-fill text-accent-ink"
                  : "border-border bg-surface-elevated text-muted hover:border-amber hover:text-amber"
              }`}
            >
              {hours} H
            </button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <span className="rounded-full bg-paper px-2 py-1 font-mono text-[9px] font-semibold text-muted">
            MODEL: {data?.model_name ?? "—"}
          </span>
          <span className="rounded-full bg-paper px-2 py-1 font-mono text-[9px] font-semibold text-muted">
            V: {data?.model_version ?? "—"}
          </span>
          <span className="rounded-full bg-amberbg px-2 py-1 font-mono text-[9px] font-semibold text-amber">
            {data?.data_type?.toUpperCase() ?? "BASELINE"}
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded border-l-[3px] border-amber bg-amberbg p-4 text-sm text-[#8b4f12]">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="space-y-2 lg:col-span-2">
          <p className="eyebrow">Highest hazard scores · {horizon}h</p>
          {(data?.rows ?? []).slice(0, 8).map((row) => {
            const band = scoreBand(row.hazard_score);
            return (
              <div key={row.polygon_id} className="rounded-md border border-line bg-surface-elevated px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] text-ink">{row.polygon_id}</span>
                  <span className={`font-mono text-[10px] font-semibold ${band.text}`}>{band.label}</span>
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-[6px] flex-1 rounded-full bg-paper">
                    <div
                      className={`h-[6px] rounded-full ${band.bar}`}
                      style={{ width: `${Math.round(row.hazard_score * 100)}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-ink">{row.hazard_score.toFixed(2)}</span>
                </div>
                <p className="mt-1 font-mono text-[9px] text-muted">
                  detections 30d: {row.detections_30d} · area: {row.area_ha ? `${Math.round(row.area_ha).toLocaleString()} ha` : "n/a"}
                </p>
              </div>
            );
          })}
          {!data && !error && <p className="text-xs text-muted">Loading…</p>}
        </div>

        <div className="lg:col-span-3">
          <table className="w-full border-collapse">
            <caption className="mb-2 text-left font-mono text-[10px] font-semibold uppercase tracking-[0.09em] text-muted">
              Portfolio hazard ranking ({horizon}h horizon)
            </caption>
            <thead>
              <tr className="border-b border-line">
                <th className="pb-2 text-left font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Polygon
                </th>
                <th className="pb-2 text-right font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Score
                </th>
                <th className="pb-2 text-right font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Detections
                </th>
                <th className="pb-2 text-right font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Area
                </th>
                <th className="pb-2 text-right font-mono text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Type
                </th>
              </tr>
            </thead>
            <tbody>
              {(data?.rows ?? []).map((row) => {
                const band = scoreBand(row.hazard_score);
                return (
                  <tr key={`${row.polygon_id}-${row.horizon_hours}`} className="border-b border-[#eef1f5]">
                    <td className="py-2 font-mono text-xs text-ink">{row.polygon_id}</td>
                    <td className={`py-2 text-right font-mono text-xs ${band.text}`}>
                      {row.hazard_score.toFixed(2)}
                    </td>
                    <td className="py-2 text-right font-mono text-xs text-ink">{row.detections_30d}</td>
                    <td className="py-2 text-right font-mono text-xs text-[#33445b]">
                      {row.area_ha ? `${Math.round(row.area_ha).toLocaleString()} ha` : "—"}
                    </td>
                    <td className="py-2 text-right">
                      <span className="rounded-full bg-amberbg px-2 py-[2px] font-mono text-[9px] font-semibold text-amber">
                        BASELINE
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="mt-4 rounded border-l-[3px] border-amber bg-amberbg p-3 text-xs leading-relaxed text-[#8b4f12]">
            {data?.disclaimer ??
              "Baseline hazard score (0-1), not a calibrated probability, not a validated fire forecast, and not a probability of default."}
          </div>
          <p className="mt-2 font-mono text-[10px] text-muted">
            Formula: score = 0.6 × recency + 0.4 × intensity, where recency =
            exp(-days_since_last_hotspot / 7) and intensity = min(hotspots_30d / 10, 1). Model
            performance claims require Phase 2 spatial backtesting - none are made today.
          </p>
        </div>
      </div>
    </div>
  );
}
