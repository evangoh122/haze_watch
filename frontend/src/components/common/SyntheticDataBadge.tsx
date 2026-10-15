export default function SyntheticDataBadge({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className="inline-block rounded-full bg-amberbg px-[7px] py-[2px] align-[1px] font-mono text-[9px] font-semibold tracking-wide text-amber"
      title="Companies, financial statements, lending exposures and policies in this application are entirely fictional."
    >
      {compact ? "SYNTHETIC" : "SYNTHETIC DATA - FICTIONAL"}
    </span>
  );
}
