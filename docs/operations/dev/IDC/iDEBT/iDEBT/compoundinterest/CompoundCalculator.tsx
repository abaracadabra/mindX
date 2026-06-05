// ─── CompoundCalculator.tsx ───────────────────────────────────────────────────
// Root orchestrator. Composes all sub-components.
// Drop this into any React/Next.js/Vite/dApp codebase.
//
// Required peer dependencies:
//   react, react-dom, recharts
// Optional (for chart):
//   recharts ^2.x
//
// Usage:
//   import { CompoundCalculator } from './compound-calculator';
//   <CompoundCalculator />
//
// Or with custom initial params:
//   <CompoundCalculator
//     initialA={{ principal: 10000, annualRate: 8, years: 20, monthlyContrib: 300, frequency: 'monthly', id: 'A' }}
//     initialB={{ principal: 5000,  annualRate: 7, years: 10, monthlyContrib: 100, frequency: 'monthly', id: 'B' }}
//   />

import React, { useState } from 'react';
import type { ScenarioParams } from '../types';
import { useCompound } from '../hooks/useCompound';
import { ScenarioCard } from './scenario/ScenarioCard';
import { CompoundChart } from './chart/CompoundChart';
import { DeltaSummary } from './delta/DeltaSummary';
import { ExplainerPanel } from './explainer/ExplainerPanel';

// ── Layout toggle ─────────────────────────────────────────────────────────────
type PanelTab = 'calculator' | 'learn';

interface CompoundCalculatorProps {
  initialA?: Partial<ScenarioParams>;
  initialB?: Partial<ScenarioParams>;
  className?: string;
}

export const CompoundCalculator: React.FC<CompoundCalculatorProps> = ({
  className,
}) => {
  const calc = useCompound();
  const [activeTab, setActiveTab] = useState<PanelTab>('calculator');

  return (
    <div
      className={className}
      style={{
        fontFamily: "'DM Sans', 'Segoe UI', system-ui, sans-serif",
        background: '#0d0f14',
        color: '#f0ede8',
        minHeight: '100vh',
        fontSize: 14,
      }}
    >
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header style={{
        padding: '40px 40px 32px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 20,
      }}>
        <div>
          <h1 style={{
            fontFamily: "'DM Serif Display', Georgia, serif",
            fontSize: 'clamp(26px, 4vw, 42px)',
            fontWeight: 400,
            letterSpacing: '-0.02em',
            lineHeight: 1.1,
            margin: 0,
          }}>
            Compound{' '}
            <em style={{ color: '#e8c46a', fontStyle: 'italic' }}>Interest</em>
          </h1>
          <p style={{ margin: '6px 0 0', fontSize: 12, color: '#7a7f8e', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Two-scenario calculator · monthly compounding by default
          </p>
        </div>

        {/* Tab switcher */}
        <div style={{
          display: 'flex',
          background: '#13161e',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 9,
          overflow: 'hidden',
        }}>
          {(['calculator', 'learn'] as PanelTab[]).map(tab => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              style={{
                background: activeTab === tab ? 'rgba(74,140,255,0.1)' : 'transparent',
                border: 'none',
                color: activeTab === tab ? '#4a8cff' : '#7a7f8e',
                cursor: 'pointer',
                fontFamily: 'inherit',
                fontSize: 12,
                letterSpacing: '0.04em',
                padding: '9px 18px',
                textTransform: 'capitalize',
                transition: 'all 0.15s',
              }}
            >
              {tab === 'calculator' ? 'Calculator' : 'Learn'}
            </button>
          ))}
        </div>
      </header>

      {/* ── Body ────────────────────────────────────────────────────────────── */}
      <main style={{ padding: '32px 40px 60px', maxWidth: 1200, margin: '0 auto' }}>

        {activeTab === 'calculator' ? (
          <>
            {/* Scenario cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
              gap: 16,
              marginBottom: 20,
            }}>
              <ScenarioCard
                result={calc.comparison.a}
                onUpdate={calc.updateA}
              />
              <ScenarioCard
                result={calc.comparison.b}
                onUpdate={calc.updateB}
              />
            </div>

            {/* Delta summary */}
            <div style={{ marginBottom: 20 }}>
              <DeltaSummary
                comparison={calc.comparison}
                onReset={calc.resetAll}
              />
            </div>

            {/* Chart */}
            <CompoundChart
              labels={calc.labels}
              datasets={calc.datasets}
              chartMode={calc.chartMode}
              onModeChange={calc.setChartMode}
            />

            {/* Footer formula note */}
            <p style={{
              marginTop: 16,
              fontSize: 11,
              color: '#444',
              fontFamily: 'monospace',
              textAlign: 'center',
            }}>
              A = P(1 + r/n)^(nt) + PMT × [(1 + r/n)^(nt) − 1] / (r/n) ·
              nominal values · inflation adjustment assumes 3% annual CPI
            </p>
          </>
        ) : (
          <ExplainerPanel />
        )}
      </main>
    </div>
  );
};

export default CompoundCalculator;
