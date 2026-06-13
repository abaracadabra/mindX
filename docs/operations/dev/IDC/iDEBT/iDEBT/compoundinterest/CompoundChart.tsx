// ─── CompoundChart.tsx ────────────────────────────────────────────────────────
// Chart component using Recharts. Supports grouped bars, area lines,
// pure lines, and interest-only view.

import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  Area,
  Line,
  XAxis, YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { ChartMode } from '../../types';
import type { ChartDataset } from '../../hooks/useCompound';
import { fmt } from '../../engine/compound.engine';

// ── Palette ───────────────────────────────────────────────────────────────────
const PALETTE = {
  aBal:  { solid: '#4a8cff', dim: 'rgba(74,140,255,0.35)' },
  aInv:  { solid: '#4a8cff', dim: 'rgba(74,140,255,0.12)' },
  bBal:  { solid: '#27c98a', dim: 'rgba(39,201,138,0.35)' },
  bInv:  { solid: '#27c98a', dim: 'rgba(39,201,138,0.12)' },
};

const CHART_MODES: { id: ChartMode; label: string }[] = [
  { id: 'area',          label: 'Area' },
  { id: 'line',          label: 'Line' },
  { id: 'grouped',       label: 'Bars' },
  { id: 'interest-only', label: 'Interest' },
];

// ── Custom tooltip ────────────────────────────────────────────────────────────
const CustomTooltip: React.FC<any> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#0d0f14',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 10,
      padding: '10px 14px',
      minWidth: 180,
    }}>
      <div style={{
        fontFamily: 'monospace', fontSize: 10,
        color: '#7a7f8e', letterSpacing: '0.08em',
        marginBottom: 8, textTransform: 'uppercase',
      }}>
        {label}
      </div>
      {payload.map((entry: any) => (
        <div key={entry.name} style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', gap: 16, marginBottom: 3,
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{
              width: 8, height: 8, borderRadius: 2,
              background: entry.color || entry.fill, flexShrink: 0,
            }} />
            <span style={{ fontSize: 11, color: '#7a7f8e', fontFamily: 'monospace' }}>
              {entry.name}
            </span>
          </span>
          <span style={{ fontSize: 12, fontFamily: 'monospace', color: '#f0ede8', fontWeight: 500 }}>
            {entry.value != null ? fmt.currency(entry.value) : '—'}
          </span>
        </div>
      ))}
    </div>
  );
};

// ── Build recharts data from aligned datasets ─────────────────────────────────
function buildChartData(labels: string[], datasets: ChartDataset[]): Record<string, any>[] {
  return labels.map((label, i) => {
    const row: Record<string, any> = { label };
    datasets.forEach(ds => {
      row[ds.label] = ds.data[i];
    });
    return row;
  });
}

// ── Main chart component ──────────────────────────────────────────────────────
interface CompoundChartProps {
  labels: string[];
  datasets: ChartDataset[];
  chartMode: ChartMode;
  onModeChange: (mode: ChartMode) => void;
}

export const CompoundChart: React.FC<CompoundChartProps> = ({
  labels,
  datasets,
  chartMode,
  onModeChange,
}) => {
  const data = buildChartData(labels, datasets);

  const yFormatter = (v: number) => fmt.currencyShort(v);

  const commonProps = {
    data,
    margin: { top: 10, right: 10, left: 10, bottom: 0 },
  };

  const axisStyle = {
    tick: { fill: '#7a7f8e', fontSize: 10, fontFamily: 'monospace' },
    axisLine: false as const,
    tickLine: false as const,
  };

  // Render the correct chart type
  const renderSeries = () => {
    if (chartMode === 'grouped' || chartMode === 'interest-only') {
      return datasets.map((ds, i) => {
        const colors = [PALETTE.aBal, PALETTE.aInv, PALETTE.bBal, PALETTE.bInv];
        const c = colors[i % colors.length];
        const isBalance = ds.type === 'balance' || ds.type === 'interest';
        return (
          <Bar
            key={ds.label}
            dataKey={ds.label}
            fill={isBalance ? c.solid : c.dim}
            radius={[3, 3, 0, 0]}
            maxBarSize={28}
          />
        );
      });
    }

    if (chartMode === 'line') {
      return datasets.map((ds, i) => {
        const colors = [PALETTE.aBal.solid, PALETTE.aInv.solid, PALETTE.bBal.solid, PALETTE.bInv.solid];
        const dashes = ['0', '4 4', '0', '4 4'];
        return (
          <Line
            key={ds.label}
            type="monotone"
            dataKey={ds.label}
            stroke={colors[i % colors.length]}
            strokeWidth={ds.type === 'balance' ? 2 : 1}
            strokeDasharray={dashes[i % dashes.length]}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls
          />
        );
      });
    }

    // area (default)
    return datasets.map((ds, i) => {
      const colors = [PALETTE.aBal, PALETTE.aInv, PALETTE.bBal, PALETTE.bInv];
      const c = colors[i % colors.length];
      const isBalance = ds.type === 'balance';
      return (
        <Area
          key={ds.label}
          type="monotone"
          dataKey={ds.label}
          stroke={c.solid}
          strokeWidth={isBalance ? 2 : 1}
          fill={isBalance ? c.dim : c.dim.replace('0.35', '0.06')}
          fillOpacity={1}
          dot={false}
          activeDot={{ r: 4, stroke: c.solid }}
          connectNulls
        />
      );
    });
  };

  return (
    <div style={{
      background: '#13161e',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 14,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 10,
      }}>
        <span style={{
          fontFamily: "'DM Serif Display', Georgia, serif",
          fontSize: 16,
          fontWeight: 400,
          color: '#f0ede8',
          letterSpacing: '-0.01em',
        }}>
          Growth over time
        </span>

        <div style={{ display: 'flex', gap: 0 }}>
          {CHART_MODES.map(m => (
            <button
              key={m.id}
              type="button"
              onClick={() => onModeChange(m.id)}
              style={{
                background: chartMode === m.id ? 'rgba(74,140,255,0.1)' : 'transparent',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRight: 'none',
                color: chartMode === m.id ? '#4a8cff' : '#7a7f8e',
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontSize: 10.5,
                letterSpacing: '0.06em',
                padding: '6px 12px',
                transition: 'all 0.12s',
              }}
              style={{
                background: chartMode === m.id ? 'rgba(74,140,255,0.1)' : 'transparent',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRight: m.id === 'interest-only' ? '1px solid rgba(255,255,255,0.08)' : 'none',
                borderRadius: m.id === 'area' ? '6px 0 0 6px' : m.id === 'interest-only' ? '0 6px 6px 0' : '0',
                color: chartMode === m.id ? '#4a8cff' : '#7a7f8e',
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontSize: 10.5,
                letterSpacing: '0.06em',
                padding: '6px 12px',
                transition: 'all 0.12s',
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div style={{
        padding: '10px 20px 0',
        display: 'flex',
        flexWrap: 'wrap',
        gap: 14,
      }}>
        {datasets.map((ds, i) => {
          const colors = [PALETTE.aBal.solid, PALETTE.aInv.dim.replace('rgba', 'rgb').replace(',0.35)', ')'), PALETTE.bBal.solid, PALETTE.bInv.dim.replace('rgba', 'rgb').replace(',0.35)', ')')];
          return (
            <div key={ds.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{
                width: 10, height: 10, borderRadius: 2,
                background: [PALETTE.aBal.solid, PALETTE.aInv.dim, PALETTE.bBal.solid, PALETTE.bInv.dim][i % 4],
                flexShrink: 0,
              }} />
              <span style={{ fontSize: 10.5, color: '#7a7f8e', fontFamily: 'monospace' }}>
                {ds.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Chart canvas */}
      <div style={{ padding: '8px 4px 16px', height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart {...commonProps}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.04)"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              {...axisStyle}
            />
            <YAxis
              {...axisStyle}
              tickFormatter={yFormatter}
              width={58}
            />
            <Tooltip content={<CustomTooltip />} />
            {renderSeries()}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
