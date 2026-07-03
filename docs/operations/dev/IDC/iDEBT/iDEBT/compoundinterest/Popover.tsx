// ─── Popover.tsx ──────────────────────────────────────────────────────────────
// Accessible, self-contained popover — no third-party dependencies.
// Closes on Escape, outside-click, and focus-out.

import React, {
  useState, useRef, useEffect, useCallback, ReactNode, CSSProperties
} from 'react';

export type PopoverPlacement = 'top' | 'bottom' | 'left' | 'right';

interface PopoverProps {
  trigger: ReactNode;
  children: ReactNode;
  placement?: PopoverPlacement;
  width?: number;
  className?: string;
}

const PLACEMENT_STYLES: Record<PopoverPlacement, CSSProperties> = {
  bottom: { top: 'calc(100% + 8px)', left: '50%', transform: 'translateX(-50%)' },
  top:    { bottom: 'calc(100% + 8px)', left: '50%', transform: 'translateX(-50%)' },
  right:  { left: 'calc(100% + 8px)', top: '50%', transform: 'translateY(-50%)' },
  left:   { right: 'calc(100% + 8px)', top: '50%', transform: 'translateY(-50%)' },
};

export const Popover: React.FC<PopoverProps> = ({
  trigger,
  children,
  placement = 'bottom',
  width = 320,
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen(o => !o), []);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const keyHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, [open, close]);

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          display: 'inline-flex',
          alignItems: 'center',
        }}
      >
        {trigger}
      </button>

      {open && (
        <div
          role="dialog"
          style={{
            position: 'absolute',
            zIndex: 1000,
            width,
            background: '#13161e',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: 12,
            boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            ...PLACEMENT_STYLES[placement],
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};

// ── Info trigger button (? icon) ──────────────────────────────────────────────
interface InfoTriggerProps {
  color?: string;
  size?: number;
  label?: string;
}

export const InfoTrigger: React.FC<InfoTriggerProps> = ({
  color = '#7a7f8e',
  size = 14,
  label = 'More info',
}) => (
  <span
    aria-label={label}
    style={{
      width: size,
      height: size,
      borderRadius: '50%',
      border: `1px solid ${color}`,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: size * 0.65,
      color,
      fontFamily: 'monospace',
      fontWeight: 500,
      flexShrink: 0,
      lineHeight: 1,
      userSelect: 'none',
    }}
  >
    ?
  </span>
);

// ── Popover body helpers ──────────────────────────────────────────────────────
export const PopoverHeader: React.FC<{ title: string; subtitle?: string }> = ({
  title, subtitle
}) => (
  <div style={{
    padding: '16px 18px 12px',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
  }}>
    <div style={{ fontSize: 13, fontWeight: 500, color: '#f0ede8', marginBottom: subtitle ? 3 : 0 }}>
      {title}
    </div>
    {subtitle && (
      <div style={{ fontSize: 11, color: '#7a7f8e', fontFamily: 'monospace', letterSpacing: '0.04em' }}>
        {subtitle}
      </div>
    )}
  </div>
);

export const PopoverBody: React.FC<{ children: ReactNode }> = ({ children }) => (
  <div style={{ padding: '14px 18px 16px', fontSize: 12.5, color: '#a8adb8', lineHeight: 1.7 }}>
    {children}
  </div>
);

export const PopoverFormula: React.FC<{ children: ReactNode }> = ({ children }) => (
  <div style={{
    margin: '10px 0',
    background: '#0d0f14',
    border: '1px solid rgba(255,255,255,0.07)',
    borderRadius: 8,
    padding: '10px 14px',
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#e8c46a',
    letterSpacing: '0.03em',
    lineHeight: 1.8,
  }}>
    {children}
  </div>
);

export const PopoverHighlight: React.FC<{ children: ReactNode; color?: string }> = ({
  children, color = '#4a8cff'
}) => (
  <span style={{ color, fontWeight: 500 }}>{children}</span>
);
