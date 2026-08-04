interface Props<T extends string> {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}

/** iOS-style segmented control with a sliding thumb (transform only). */
export function SegmentedControl<T extends string>({ options, value, onChange }: Props<T>) {
  const index = Math.max(0, options.findIndex((o) => o.value === value));
  return (
    <div
      style={{
        position: "relative",
        display: "grid",
        gridTemplateColumns: `repeat(${options.length}, 1fr)`,
        background: "var(--accent-soft)",
        borderRadius: "var(--radius-md)",
        padding: 3,
      }}
    >
      <div
        aria-hidden
        style={{
          position: "absolute",
          top: 3,
          bottom: 3,
          left: 3,
          width: `calc((100% - 6px) / ${options.length})`,
          background: "var(--surface-solid)",
          borderRadius: `calc(var(--radius-md) - 3px)`,
          boxShadow: "var(--shadow-card)",
          transform: `translateX(${index * 100}%)`,
          transition: `transform var(--dur-med) var(--ease-spring)`,
        }}
      />
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          style={{
            position: "relative",
            border: "none",
            background: "transparent",
            fontFamily: "inherit",
            fontSize: 15,
            fontWeight: 600,
            color: o.value === value ? "var(--text)" : "var(--text-secondary)",
            padding: "8px 12px",
            zIndex: 1,
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
