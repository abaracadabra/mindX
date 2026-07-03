// ─── ScenarioCard.tsx ─────────────────────────────────────────────────────────
// Full-featured input card for a single compound interest scenario.
// Each field has an inline info popover with contextual explanation.

import React, { useCallback } from 'react';
import type { ScenarioParams, CompoundFrequency } from '../../types';
import { ScenarioResult } from '../../types';
import { fmt, FREQ_LABELS, FREQ_N, doublingYears } from '../../engine/compound.engine';
import {
  Popover, InfoTrigger,
  PopoverHeader, PopoverBody,
  PopoverFormula, PopoverHighlight,
} from '../popover/Popover';

// ── Colors per scenario ───────────────────────────────────────────────────────
const COLORS = {
  A: { accent: '#4a8cff', dim: 'rgba(74,140,255,0.12)', border: 'rgba(74,140,255,0.3)', label: 'Scenario A' },
  B: { accent: '#27c98a', dim: 'rgba(39,201,138,0.12)', border: 'rgba(39,201,138,0.3)', label: 'Scenario B' },
};

const FREQ_OPTIONS: CompoundFrequency[] = ['daily', 'monthly', 'quarterly', 'annually'];

// ── Reusable input row ────────────────────────────────────────────────────────
interface FieldRowProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  format: (v: number) => string;
  accentColor: string;
  popoverTitle: string;
  popoverContent: React.ReactNode;
}

const FieldRow: React.FC<FieldRowProps> = ({
  label, value, min, max, step, onChange, format,
  accentColor, popoverTitle, popoverContent,
}) => {
  const handleSlider = (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange(parseFloat(e.target.value));
  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseFloat(e.target.value);
    if (!isNaN(v)) onChange(Math.max(min, Math.min(max, v)));
  };

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Label row */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        justifyContent: 'space-between', marginBottom: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ fontSize: 11, color: '#7a7f8e', letterSpacing: '0.04em' }}>{label}</span>
          <Popover
            trigger={<InfoTrigger color="#555" size={12} label={`About ${label}`} />}
            placement="bottom"
            width={300}
          >
            <PopoverHeader title={popoverTitle} />
            <PopoverBody>{popoverContent}</PopoverBody>
          </Popover>
        </div>
        {/* Editable value display */}
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={handleInput}
          style={{
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 6,
            color: accentColor,
            fontFamily: 'monospace',
            fontSize: 12,
            fontWeight: 500,
            padding: '2px 8px',
            width: 80,
            textAlign: 'right',
            outline: 'none',
          }}
        />
      </div>

      {/* Slider */}
      <div style={{ position: 'relative' }}>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={handleSlider}
          style={{
            width: '100%',
            accentColor,
            cursor: 'pointer',
            height: 4,
          }}
        />
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          fontSize: 9.5, color: '#444', fontFamily: 'monospace',
          marginTop: 2,
        }}>
          <span>{format(min)}</span>
          <span>{format(max)}</span>
        </div>
      </div>
    </div>
  );
};

// ── Stat pill ─────────────────────────────────────────────────────────────────
const StatPill: React.FC<{
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  color?: string;
}> = ({ label, value, sub, accent, color = '#f0ede8' }) => (
  <div style={{ textAlign: 'center' }}>
    <div style={{ fontSize: 10, color: '#7a7f8e', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 3 }}>
      {label}
    </div>
    <div style={{ fontFamily: 'monospace', fontSize: 15, fontWeight: 500, color: accent ? '#27c98a' : color }}>
      {value}
    </div>
    {sub && (
      <div style={{ fontSize: 9.5, color: '#555', fontFamily: 'monospace', marginTop: 1 }}>{sub}</div>
    )}
  </div>
);

// ── Main ScenarioCard ─────────────────────────────────────────────────────────
interface ScenarioCardProps {
  result: ScenarioResult;
  onUpdate: (patch: Partial<ScenarioParams>) => void;
}

export const ScenarioCard: React.FC<ScenarioCardProps> = ({ result, onUpdate }) => {
  const { params, final, doublingYears: dbl, inflationAdjusted } = result;
  const c = COLORS[params.id];

  const set = useCallback(
    (key: keyof ScenarioParams) => (v: number | string) =>
      onUpdate({ [key]: v }),
    [onUpdate]
  );

  return (
    <div style={{
      background: '#13161e',
      border: `1px solid rgba(255,255,255,0.07)`,
      borderRadius: 14,
      overflow: 'hidden',
      position: 'relative',
    }}>
      {/* Top accent line */}
      <div style={{ height: 2, background: c.accent }} />

      {/* Card header */}
      <div style={{
        padding: '16px 20px 14px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#555', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            {c.label}
          </span>
          <div style={{ fontSize: 13, fontWeight: 500, color: '#f0ede8', marginTop: 2 }}>
            {fmt.currency(params.principal)} · {params.annualRate}% · {params.years}yr
          </div>
        </div>
        <div style={{
          background: c.dim,
          border: `1px solid ${c.border}`,
          borderRadius: 100,
          padding: '4px 12px',
          fontSize: 10,
          color: c.accent,
          fontFamily: 'monospace',
          letterSpacing: '0.08em',
        }}>
          {fmt.currency(final.balance)}
        </div>
      </div>

      {/* Inputs */}
      <div style={{ padding: '18px 20px 14px' }}>

        <FieldRow
          label="Initial principal"
          value={params.principal}
          min={0} max={500000} step={500}
          onChange={v => set('principal')(v)}
          format={v => fmt.currencyShort(v)}
          accentColor={c.accent}
          popoverTitle="Principal — initial deposit"
          popoverContent={
            <>
              Your starting lump-sum. It compounds from day one.
              <PopoverFormula>FV_principal = P × (1 + r/n)^(nt)</PopoverFormula>
              <PopoverHighlight color={c.accent}>Tip:</PopoverHighlight> Doubling P doubles
              the final balance — but starting earlier adds years to the exponent, which is
              exponentially more powerful at high rates.
            </>
          }
        />

        <FieldRow
          label="Annual rate (%)"
          value={params.annualRate}
          min={0.1} max={30} step={0.25}
          onChange={v => set('annualRate')(v)}
          format={v => v + '%'}
          accentColor={c.accent}
          popoverTitle="Annual interest rate (APY)"
          popoverContent={
            <>
              The percentage return per year. Every 1% increase compounds dramatically
              over long horizons.
              <PopoverFormula>
                Effective Annual Rate:{'\n'}
                EAR = (1 + r/n)^n − 1
              </PopoverFormula>
              Fees, expense ratios, and taxes reduce your effective rate — track net-of-fee
              returns when comparing vehicles.
              <br /><br />
              Rule of 72: doubles in{' '}
              <PopoverHighlight color="#e8c46a">
                {doublingYears(params.annualRate).toFixed(1)} years
              </PopoverHighlight>{' '}
              at {params.annualRate}%.
            </>
          }
        />

        <FieldRow
          label="Time horizon (years)"
          value={params.years}
          min={1} max={60} step={1}
          onChange={v => set('years')(v)}
          format={v => v + 'yr'}
          accentColor={c.accent}
          popoverTitle="Investment time horizon"
          popoverContent={
            <>
              Time is the strongest lever. Compounding is exponential — each additional year
              applies the rate to a larger base.
              <PopoverFormula>
                {params.annualRate}% for {params.years}yr:{'\n'}
                1× → {Math.pow(1 + params.annualRate / 100, params.years).toFixed(2)}× multiplier
              </PopoverFormula>
              <PopoverHighlight color={c.accent}>The last 10 years</PopoverHighlight> of a long
              investment typically generate more than the first 20 combined.
            </>
          }
        />

        <FieldRow
          label="Monthly contribution ($)"
          value={params.monthlyContrib}
          min={0} max={5000} step={50}
          onChange={v => set('monthlyContrib')(v)}
          format={v => fmt.currencyShort(v)}
          accentColor={c.accent}
          popoverTitle="Recurring monthly contribution"
          popoverContent={
            <>
              Money added every month, modelled as an ordinary annuity paid at the end of
              each period.
              <PopoverFormula>
                FV_annuity = PMT × [(1+r/n)^(nt) − 1] / (r/n)
              </PopoverFormula>
              Increasing contributions linearly scales the annuity term but not the
              compounding exponent — so earlier dollars are worth more than later ones.
            </>
          }
        />

        {/* Compounding frequency */}
        <div style={{ marginBottom: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 8 }}>
            <span style={{ fontSize: 11, color: '#7a7f8e', letterSpacing: '0.04em' }}>
              Compounding frequency
            </span>
            <Popover
              trigger={<InfoTrigger color="#555" size={12} label="About compounding frequency" />}
              placement="bottom"
              width={300}
            >
              <PopoverHeader title="Compounding frequency" subtitle={`n = ${FREQ_N[params.frequency]}/yr`} />
              <PopoverBody>
                How often earned interest is added back to principal. More frequent = higher
                effective annual rate (EAR).
                <PopoverFormula>
                  7% monthly → EAR 7.229%{'\n'}
                  7% daily   → EAR 7.250%{'\n'}
                  Δ ≈ 0.02% — small but real
                </PopoverFormula>
              </PopoverBody>
            </Popover>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
            {FREQ_OPTIONS.map(f => (
              <button
                key={f}
                type="button"
                onClick={() => onUpdate({ frequency: f })}
                style={{
                  background: params.frequency === f ? c.dim : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${params.frequency === f ? c.border : 'rgba(255,255,255,0.07)'}`,
                  borderRadius: 7,
                  color: params.frequency === f ? c.accent : '#7a7f8e',
                  cursor: 'pointer',
                  fontSize: 11,
                  fontFamily: 'monospace',
                  padding: '6px 10px',
                  textAlign: 'left',
                  transition: 'all 0.12s',
                }}
              >
                {FREQ_LABELS[f]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results strip */}
      <div style={{
        padding: '12px 20px 14px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 0,
      }}>
        <StatPill
          label="Invested"
          value={fmt.currencyShort(final.invested)}
        />
        <StatPill
          label="Interest"
          value={fmt.currencyShort(final.interest)}
          accent
        />
        <StatPill
          label="Growth"
          value={fmt.pct(final.growthPct, 0)}
        />
        <StatPill
          label="Real value"
          value={fmt.currencyShort(inflationAdjusted ?? 0)}
          sub="@3% inflation"
          color="#a8adb8"
        />
      </div>
    </div>
  );
};
