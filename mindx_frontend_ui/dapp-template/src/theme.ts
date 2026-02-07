/**
 * Theme tokens – mirror styled.css for production TSX.
 * Use in styled-components or inline styles for financial/production builds.
 */

export const theme = {
  bg: '#0a0a0a',
  panel: 'rgba(15, 15, 25, 0.95)',
  text: '#ffffff',
  muted: '#b0b0b0',
  accent: '#00a8ff',
  border: 'rgba(0, 168, 255, 0.3)',
  radius: 8,
  font: "'Share Tech Mono', 'Consolas', monospace",
} as const;

export type Theme = typeof theme;
