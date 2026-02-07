/**
 * Root app – production TSX.
 * Mount this when building with React; index.html loads dapp.js for prototype.
 */

import React, { useState, useCallback } from 'react';
import { Wallet } from './Wallet';
import { theme } from './theme';

export function App(): React.ReactElement {
  const [status, setStatus] = useState<string>('Not connected');
  const [connecting, setConnecting] = useState(false);

  const onConnect = useCallback(async () => {
    if (typeof window.ethereum === 'undefined') {
      setStatus('No wallet (e.g. MetaMask)');
      return;
    }
    setConnecting(true);
    setStatus('Connecting…');
    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const addr = accounts?.[0];
      setStatus(addr ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : 'Not connected');
    } catch {
      setStatus('Connection failed');
    } finally {
      setConnecting(false);
    }
  }, []);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: theme.bg,
        color: theme.text,
        fontFamily: theme.font,
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1rem 1.5rem',
          background: theme.panel,
          borderBottom: `1px solid ${theme.border}`,
        }}
      >
        <h1 style={{ margin: 0, fontSize: '1.25rem', color: theme.accent }}>mindX Dapp</h1>
        <Wallet status={status} onConnect={onConnect} connecting={connecting} />
      </header>
      <main style={{ flex: 1, padding: '1.5rem' }}>
        <section style={{ maxWidth: '64rem', margin: '0 auto' }}>
          <p>Production build: React + TSX. API base from config.</p>
        </section>
      </main>
    </div>
  );
}
