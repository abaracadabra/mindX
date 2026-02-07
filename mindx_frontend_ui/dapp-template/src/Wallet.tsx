/**
 * Wallet connect UI – production TSX.
 * Replace dapp.js wallet logic when migrating to React.
 */

import React from 'react';
import { theme } from './theme';

export interface WalletProps {
  status: string;
  onConnect: () => void;
  connecting?: boolean;
}

export function Wallet({ status, onConnect, connecting }: WalletProps): React.ReactElement {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
      <span style={{ color: theme.muted, fontSize: '0.875rem' }}>{status}</span>
      <button
        type="button"
        onClick={onConnect}
        disabled={connecting}
        style={{
          fontFamily: theme.font,
          padding: '0.5rem 1rem',
          background: theme.accent,
          color: '#000',
          border: 'none',
          borderRadius: theme.radius,
          cursor: connecting ? 'wait' : 'pointer',
        }}
      >
        {connecting ? 'Connecting…' : 'Connect wallet'}
      </button>
    </div>
  );
}
