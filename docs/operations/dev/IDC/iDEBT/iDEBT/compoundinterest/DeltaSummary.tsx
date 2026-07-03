// ─── DeltaSummary.tsx ─────────────────────────────────────────────────────────
// Comparison summary strip between Scenario A and B.

import React from 'react';
import type { ComparisonResult } from '../../types';
import { fmt } from '../../engine/compound.engine';
import {
  Popover, InfoTrigger,
  PopoverHeader, PopoverBody, PopoverFormula,
} from '../popover/Popover';

interface DeltaSummaryProps {
  comparison: ComparisonResult;
  onReset: () => void;
}

export const DeltaSummary: React.FC<DeltaSummaryProps> = ({ comparison, onReset }) => {
  const { a, b, leader, absoluteDiff, relativeDiff, maxYears } = comparison;
  const leaderColor = leader === 'A' ? '#4a8cff' : '#27c98a';
  const leaderLabel = leader === 'tie' ? 'Tied' : `Scenario ${leader} leads`;

  // Milestones: first year each scenario crosses $50k, $100k, $500k
  const getMilestone = (
    series: typeof a.series,
    threshold: number
  ): string => {
    const pt = series.find(p => p.balance >= threshold);
    return pt ? `Yr ${pt.year}` : '—';
  };

  const milestones = [50_000, 100_000, 250_000, 500_000];

  return (
    <div style={{
      background: '#13161e',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 14,
      overflow: 'hidden',
    }}>
      {/* Leader bar */}
      <div style={{
        padding: '14px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: leaderColor }} />
          <div>
            <div style={{ fontSize: 12, color: '#7a7f8e', marginBottom: 1 }}>
              After {maxYears} years
            </div>
            <div style={{ fontSize: 13, fontWeight: 500, color: '#f0ede8' }}>
              {leaderLabel} by{' '}
              <span style={{ color: leaderColor, fontFamily: 'monospace' }}>
                {fmt.currency(absoluteDiff)}
              </span>
              {' '}
              <span style={{ color: '#555', fontSize: 11, fontFamily: 'monospace' }}>
                ({fmt.pct(relativeDiff, 1)} difference)
              </span>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onReset}
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 7,
            color: '#7a7f8e',
            cursor: 'pointer',
            fontFamily: 'monospace',
            fontSize: 10,
            letterSpacing: '0.06em',
            padding: '6px 12px',
          }}
        >
          Reset defaults
        </button>
      </div>

      {/* Quick stats row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: 0,
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        {[
          {
            label: 'A total return',
            value: fmt.pct(a.final.growthPct, 0),
            color: '#4a8cff',
            tip: 'Total return on investment — (balance / invested − 1) × 100.',
          },
          {
            label: 'B total return',
            value: fmt.pct(b.final.growthPct, 0),
            color: '#27c98a',
            tip: 'Total return on investment — (balance / invested − 1) × 100.',
          },
          {
            label: 'A doubles in',
            value: fmt.years(a.doublingYears),
            color: '#e8c46a',
            tip: `Rule of 72: 72 / ${a.params.annualRate}% ≈ ${a.doublingYears.toFixed(1)} years to double.`,
          },
          {
            label: 'B doubles in',
            value: fmt.years(b.doublingYears),
            color: '#e8c46a',
            tip: `Rule of 72: 72 / ${b.params.annualRate}% ≈ ${b.doublingYears.toFixed(1)} years to double.`,
          },
          {
            label: 'A real value',
            value: fmt.currencyShort(a.inflationAdjusted ?? 0),
            color: '#a8adb8',
            tip: `Purchasing power at 3% annual inflation over ${a.params.years} years.`,
          },
          {
            label: 'B real value',
            value: fmt.currencyShort(b.inflationAdjusted ?? 0),
            color: '#a8adb8',
            tip: `Purchasing power at 3% annual inflation over ${b.params.years} years.`,
          },
        ].map((item, i, arr) => (
          <div
            key={item.label}
            style={{
              padding: '12px 16px',
              borderRight: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
              <span style={{ fontSize: 10, color: '#7a7f8e', letterSpacing: '0.04em' }}>
                {item.label}
              </span>
              <Popover
                trigger={<InfoTrigger color="#444" size={11} />}
                placement="bottom"
                width={240}
              >
                <PopoverHeader title={item.label} />
                <PopoverBody>{item.tip}</PopoverBody>
              </Popover>
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: 15, fontWeight: 500, color: item.color }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* Milestone table */}
      <div style={{ padding: '14px 20px' }}>
        <div style={{
          fontSize: 10, color: '#555', fontFamily: 'monospace',
          letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          Balance milestones
          <Popover
            trigger={<InfoTrigger color="#444" size={11} />}
            placement="top"
            width={260}
          >
            <PopoverHeader title="Milestone years" />
            <PopoverBody>
              The first year each scenario crosses a given balance threshold.
              Shows how compounding accelerates over time — early milestones
              are far apart, later ones arrive faster.
            </PopoverBody>
          </Popover>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', color: '#555', fontFamily: 'monospace', fontWeight: 400, paddingBottom: 6 }}>Target</th>
              <th style={{ textAlign: 'center', color: '#4a8cff', fontFamily: 'monospace', fontWeight: 400, paddingBottom: 6 }}>Scenario A</th>
              <th style={{ textAlign: 'center', color: '#27c98a', fontFamily: 'monospace', fontWeight: 400, paddingBottom: 6 }}>Scenario B</th>
            </tr>
          </thead>
          <tbody>
            {milestones.map(threshold => (
              <tr
                key={threshold}
                style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
              >
                <td style={{ padding: '6px 0', color: '#7a7f8e', fontFamily: 'monospace' }}>
                  {fmt.currency(threshold)}
                </td>
                <td style={{ textAlign: 'center', color: '#4a8cff', fontFamily: 'monospace' }}>
                  {getMilestone(a.series, threshold)}
                </td>
                <td style={{ textAlign: 'center', color: '#27c98a', fontFamily: 'monospace' }}>
                  {getMilestone(b.series, threshold)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
