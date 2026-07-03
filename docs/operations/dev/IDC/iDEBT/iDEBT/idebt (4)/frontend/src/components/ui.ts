// Shared styling primitives. Tiny inline-style system to avoid pulling in
// a UI kit; consistent visual tokens across the four components.

export const tokens = {
  bg:        "#0a0a0a",
  bgPanel:   "#121212",
  bgField:   "#1a1a1a",
  border:    "#222",
  borderHi:  "#333",
  text:      "#e5e5e5",
  textDim:   "#888",
  accent:    "#4ade80",
  warn:      "#fbbf24",
  danger:    "#f87171",
  crisis:    "#ef4444",
  radius:    6
};

export const panel: React.CSSProperties = {
  background: tokens.bgPanel,
  border: `1px solid ${tokens.border}`,
  borderRadius: tokens.radius,
  padding: 20
};

export const field: React.CSSProperties = {
  background: tokens.bgField,
  border: `1px solid ${tokens.border}`,
  borderRadius: tokens.radius,
  padding: "8px 10px",
  color: tokens.text,
  fontFamily: "inherit",
  fontSize: 13,
  width: "100%"
};

export const button: React.CSSProperties = {
  background: tokens.text,
  color: tokens.bg,
  border: "none",
  borderRadius: tokens.radius,
  padding: "10px 16px",
  fontFamily: "inherit",
  fontWeight: 600,
  cursor: "pointer"
};

export const buttonSecondary: React.CSSProperties = {
  ...button,
  background: "transparent",
  color: tokens.text,
  border: `1px solid ${tokens.borderHi}`
};

export function label(text: string): React.CSSProperties {
  return { display: "block", fontSize: 11, textTransform: "uppercase", letterSpacing: 1, color: tokens.textDim, marginBottom: 6 };
}

export function regimeColor(regime: number): string {
  switch (regime) {
    case 0: return tokens.accent; // Calm
    case 1: return "#a3e635";     // Elevated
    case 2: return tokens.warn;   // Distress
    case 3: return tokens.danger; // Crisis
    case 4: return tokens.crisis; // Default
    default: return tokens.textDim;
  }
}

export const REGIME_NAMES = ["Calm", "Elevated", "Distress", "Crisis", "Default"] as const;
