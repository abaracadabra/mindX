// ─── ExplainerPanel.tsx ───────────────────────────────────────────────────────
// Tabbed educational panel explaining every concept in compound interest.
// Each tab can also be used as a standalone popover via the export.

import React, { useState } from 'react';
import type { ExplainerTab } from '../../types';
import {
  PopoverFormula,
  PopoverHighlight,
} from '../popover/Popover';

// ── Tab definitions ───────────────────────────────────────────────────────────
const TABS: { id: ExplainerTab; label: string; short: string }[] = [
  { id: 'overview',   label: 'What is it?',      short: '01' },
  { id: 'formula',    label: 'The formula',       short: '02' },
  { id: 'principal',  label: 'Principal',         short: '03' },
  { id: 'rate',       label: 'Interest rate',     short: '04' },
  { id: 'time',       label: 'Time horizon',      short: '05' },
  { id: 'frequency',  label: 'Compounding freq.', short: '06' },
  { id: 'vs-simple',  label: 'vs Simple interest',short: '07' },
  { id: 'rule72',     label: 'Rule of 72',        short: '08' },
];

// ── Tab content ───────────────────────────────────────────────────────────────
const CONTENT: Record<ExplainerTab, React.FC> = {
  overview: () => (
    <div>
      <p>
        Compound interest is interest calculated on both your{' '}
        <PopoverHighlight color="#4a8cff">initial principal</PopoverHighlight> and the{' '}
        <PopoverHighlight color="#27c98a">accumulated interest</PopoverHighlight> from previous
        periods. It's the difference between arithmetic and exponential growth.
      </p>
      <p style={{ marginTop: 10 }}>
        Each compounding period, the interest earned is <em>folded back</em> into the
        balance — so the next period's interest is calculated on a larger number. Over
        decades, this creates a curve that grows slowly at first, then steeply accelerates.
      </p>
      <p style={{ marginTop: 10 }}>
        Einstein (apocryphally) called it the "eighth wonder of the world." Whether or not
        he said it, the math is real: a single dollar at 7% for 40 years becomes{' '}
        <PopoverHighlight color="#e8c46a">$14.97</PopoverHighlight> — no extra contributions
        required.
      </p>
    </div>
  ),

  formula: () => (
    <div>
      <p>The standard compound interest formula with recurring contributions:</p>
      <PopoverFormula>
        A = P(1 + r/n)^(nt){'\n'}
        {'  '}+ PMT × [(1 + r/n)^(nt) − 1] / (r/n)
      </PopoverFormula>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, marginTop: 8 }}>
        {[
          ['A', 'Final balance'],
          ['P', 'Principal (initial deposit)'],
          ['r', 'Annual interest rate as decimal (e.g. 0.07)'],
          ['n', 'Compounding periods per year (12 for monthly)'],
          ['t', 'Time in years'],
          ['PMT', 'Payment per compounding period'],
        ].map(([sym, desc]) => (
          <tr key={sym} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <td style={{ padding: '5px 8px', color: '#e8c46a', fontFamily: 'monospace', width: 40, verticalAlign: 'top' }}>{sym}</td>
            <td style={{ padding: '5px 8px', color: '#a8adb8' }}>{desc}</td>
          </tr>
        ))}
      </table>
      <p style={{ marginTop: 10 }}>
        The first term is the <PopoverHighlight color="#4a8cff">future value of a lump sum</PopoverHighlight>.
        The second is the <PopoverHighlight color="#27c98a">future value of an ordinary annuity</PopoverHighlight> — your recurring contributions.
      </p>
    </div>
  ),

  principal: () => (
    <div>
      <p>
        The <PopoverHighlight color="#4a8cff">principal</PopoverHighlight> is the starting
        capital — the lump sum you deposit on day one. It's the base that every compounding
        cycle multiplies.
      </p>
      <p style={{ marginTop: 10 }}>
        Because principal compounds from the very first period, an early lump sum is
        disproportionately powerful. Compare:
      </p>
      <PopoverFormula>
        $5,000 @ 7% / 30yr → $38,061{'\n'}
        $10,000 @ 7% / 30yr → $76,123{'\n'}
        Doubling P → doubles the outcome (linear)
      </PopoverFormula>
      <p>
        Principal scales <em>linearly</em> but time scales <em>exponentially</em>. A larger
        principal buys you a higher starting point on the curve, but starting earlier is
        usually worth more than starting bigger.
      </p>
    </div>
  ),

  rate: () => (
    <div>
      <p>
        The <PopoverHighlight color="#4a8cff">annual interest rate</PopoverHighlight> (APY)
        is the percentage gain per year before compounding adjusts it. It's the single
        biggest lever in the formula — small changes compound dramatically.
      </p>
      <PopoverFormula>
        $10,000 @ 5% / 30yr → $43,219{'\n'}
        $10,000 @ 7% / 30yr → $76,123{'\n'}
        $10,000 @ 10%/ 30yr → $174,494
      </PopoverFormula>
      <p style={{ marginTop: 8 }}>
        The difference between 5% and 10% is not 2× — it's{' '}
        <PopoverHighlight color="#e8c46a">4×</PopoverHighlight>. This is why expense ratios,
        management fees, and loan interest rates matter so much: they're a direct tax on
        your compounding rate.
      </p>
      <p style={{ marginTop: 10 }}>
        In DeFi contexts, APY already accounts for compounding frequency, while APR does
        not. Always verify which you're comparing.
      </p>
    </div>
  ),

  time: () => (
    <div>
      <p>
        Time is the <PopoverHighlight color="#27c98a">most powerful variable</PopoverHighlight>{' '}
        in the formula. Because compounding is exponential, the curve accelerates — the
        last decade of a 30-year investment typically generates more wealth than the first
        two combined.
      </p>
      <PopoverFormula>
        $10,000 @ 7%: yr 10 → $19,672{'\n'}
        $10,000 @ 7%: yr 20 → $38,697{'\n'}
        $10,000 @ 7%: yr 30 → $76,123{'\n'}
        Each decade roughly doubles the balance
      </PopoverFormula>
      <p style={{ marginTop: 8 }}>
        Starting 10 years earlier is often worth more than doubling your monthly
        contributions. A 25-year-old who invests $200/mo at 7% will typically outperform
        a 35-year-old contributing $400/mo — with <em>less total money invested</em>.
      </p>
      <p style={{ marginTop: 10 }}>
        Conversely, <PopoverHighlight color="#e05c5c">withdrawing early</PopoverHighlight> doesn't
        just lose the capital — it loses all future compounding on that capital.
      </p>
    </div>
  ),

  frequency: () => (
    <div>
      <p>
        <PopoverHighlight color="#4a8cff">Compounding frequency</PopoverHighlight> determines
        how often earned interest is added to the principal. More frequent compounding means
        a slightly higher effective annual rate (EAR).
      </p>
      <PopoverFormula>
        EAR = (1 + r/n)^n − 1{'\n\n'}
        7% compounded annually  → EAR 7.000%{'\n'}
        7% compounded monthly   → EAR 7.229%{'\n'}
        7% compounded daily     → EAR 7.250%
      </PopoverFormula>
      <p style={{ marginTop: 8 }}>
        The difference between monthly and daily compounding is{' '}
        <PopoverHighlight color="#e8c46a">small in practice</PopoverHighlight> (~0.02% on
        the EAR). The gap between annual and monthly is more meaningful, especially on
        large balances over long periods.
      </p>
      <p style={{ marginTop: 10 }}>
        Most savings accounts, mortgages, and DeFi protocols compound monthly or daily.
        CDs and bonds often compound semi-annually.
      </p>
    </div>
  ),

  'vs-simple': () => (
    <div>
      <p>
        <PopoverHighlight color="#4a8cff">Simple interest</PopoverHighlight> earns returns
        only on the original principal — interest is never re-invested. The formula is
        just <code style={{ color: '#e8c46a', fontFamily: 'monospace' }}>A = P(1 + rt)</code>.
      </p>
      <PopoverFormula>
        Simple:   $10,000 @ 7% / 30yr → $31,000{'\n'}
        Compound: $10,000 @ 7% / 30yr → $76,123{'\n'}
        Compound advantage: +$45,123 (+145%)
      </PopoverFormula>
      <p style={{ marginTop: 8 }}>
        Simple interest growth is a straight line; compound growth is a curve. The longer
        the horizon, the wider the gap. At 10 years the difference is moderate; at 40 years
        it's an order of magnitude.
      </p>
      <p style={{ marginTop: 10 }}>
        <PopoverHighlight color="#e05c5c">Debt compounds too.</PopoverHighlight> Credit cards
        use compound interest against you — which is why carrying a balance at 25% APR
        can be catastrophic over time.
      </p>
    </div>
  ),

  rule72: () => (
    <div>
      <p>
        The <PopoverHighlight color="#e8c46a">Rule of 72</PopoverHighlight> is a mental
        shortcut to estimate how long it takes to double your money:
      </p>
      <PopoverFormula>
        Years to double ≈ 72 / annual rate %{'\n\n'}
        4%  → ~18 years{'\n'}
        6%  → ~12 years{'\n'}
        8%  → ~9 years{'\n'}
        12% → ~6 years{'\n'}
        72% → ~1 year
      </PopoverFormula>
      <p style={{ marginTop: 8 }}>
        It's a rough approximation (accurate within a year for rates between 6–10%)
        derived from the natural log of 2 (ln 2 ≈ 0.693 ≈ 69.3 / r, but 72 divides more
        cleanly by many common rates).
      </p>
      <p style={{ marginTop: 10 }}>
        It also works in reverse: <PopoverHighlight color="#e05c5c">Rule of 72 for
        inflation</PopoverHighlight>. At 3% inflation, purchasing power halves in ~24 years.
        At 7% inflation, it halves in ~10 years.
      </p>
    </div>
  ),
};

// ── ExplainerPanel component ──────────────────────────────────────────────────
interface ExplainerPanelProps {
  initialTab?: ExplainerTab;
  embedded?: boolean; // true = no outer card (for use inside modals/panels)
}

export const ExplainerPanel: React.FC<ExplainerPanelProps> = ({
  initialTab = 'overview',
  embedded = false,
}) => {
  const [active, setActive] = useState<ExplainerTab>(initialTab);
  const Content = CONTENT[active];

  return (
    <div style={{
      background: embedded ? 'transparent' : '#13161e',
      border: embedded ? 'none' : '1px solid rgba(255,255,255,0.07)',
      borderRadius: embedded ? 0 : 14,
      overflow: 'hidden',
    }}>
      {/* Tab strip */}
      <div style={{
        display: 'flex',
        overflowX: 'auto',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        scrollbarWidth: 'none',
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActive(t.id)}
            style={{
              flexShrink: 0,
              background: active === t.id ? 'rgba(74,140,255,0.08)' : 'transparent',
              border: 'none',
              borderBottom: active === t.id
                ? '2px solid #4a8cff'
                : '2px solid transparent',
              color: active === t.id ? '#f0ede8' : '#7a7f8e',
              cursor: 'pointer',
              padding: '10px 14px',
              fontSize: 11.5,
              fontFamily: 'inherit',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s',
            }}
          >
            <span style={{
              fontFamily: 'monospace',
              fontSize: 9,
              color: active === t.id ? '#4a8cff' : '#444',
              marginRight: 5,
              letterSpacing: '0.05em',
            }}>
              {t.short}
            </span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab body */}
      <div style={{ padding: '18px 20px 20px' }}>
        <Content />
      </div>
    </div>
  );
};

// ── Standalone tab popover (per-field usage) ──────────────────────────────────
export { CONTENT as ExplainerContent, TABS as ExplainerTabs };
