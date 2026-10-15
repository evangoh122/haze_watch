export interface ScqaBlock {
  situation: string;
  complication: string;
  question: string;
  answer: string;
}

const ORDER: Array<{ key: keyof ScqaBlock; letter: string; label: string }> = [
  { key: "situation", letter: "S", label: "Situation" },
  { key: "complication", letter: "C", label: "Complication" },
  { key: "question", letter: "Q", label: "Question" },
  { key: "answer", letter: "A", label: "Answer" },
];

/** SCQA executive narrative: Situation -> Complication -> Question -> Answer. */
export default function ScqaNarrative({ block }: { block: ScqaBlock }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {ORDER.map(({ key, letter, label }) => (
        <div key={key} className="rounded-lg border border-border bg-surface-elevated p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-700 text-sm font-semibold text-white">
              {letter}
            </span>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-secondary">{label}</h3>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-secondary">{block[key]}</p>
        </div>
      ))}
    </div>
  );
}
