interface Props {
  name: string;
  color: string;
  size?: number;
  src?: string;
}

export function Avatar({ name, color, size = 40, src }: Props) {
  const initials = name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div
      aria-label={name}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: src ? `center/cover url(${src})` : color,
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.4,
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {!src && initials}
    </div>
  );
}
