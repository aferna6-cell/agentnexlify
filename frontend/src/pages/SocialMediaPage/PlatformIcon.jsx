import { PLATFORM_MAP } from "./constants";

export default function PlatformIcon({ platform, size = 22 }) {
  const p = PLATFORM_MAP[platform];
  if (!p) return null;
  return (
    <span
      title={p.label}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        borderRadius: "50%",
        fontSize: size * 0.45,
        fontWeight: 700,
        color: "#fff",
        background: p.color,
        flexShrink: 0,
      }}
    >
      {p.icon}
    </span>
  );
}
