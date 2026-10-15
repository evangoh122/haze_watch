export interface ScenarioSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (value: number) => void;
  hint?: string;
}

/** Assumption slider (workbench form-field style: mono label, explicit unit). */
export default function ScenarioSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
  hint,
}: ScenarioSliderProps) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-muted">
          {label}
        </span>
        <span className="font-mono text-[13px] font-semibold text-ink">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1 w-full accent-[#c27821]"
        aria-label={label}
      />
      {hint && <p className="mt-[2px] text-[10px] text-[#8a96a8]">{hint}</p>}
    </label>
  );
}
