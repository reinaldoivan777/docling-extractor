type ProcessingStatusProps = {
  active: boolean;
  completed: boolean;
};

export function ProcessingStatus({ active, completed }: ProcessingStatusProps) {
  const steps = completed
    ? ["Upload", "Conversion", "Serialization", "Chunking"]
    : active
      ? ["Upload", "Conversion", "Serialization", "Chunking"]
      : [];

  if (steps.length === 0) {
    return null;
  }

  return (
    <ol className="processing-steps" aria-label="Processing status">
      {steps.map((step, index) => (
        <li key={step} className={completed || index === 0 ? "is-complete" : index === 1 ? "is-active" : ""}>
          <span>{completed || index === 0 ? "✓" : index === 1 ? "→" : "○"}</span>
          {step}
        </li>
      ))}
    </ol>
  );
}
