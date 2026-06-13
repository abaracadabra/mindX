// ─── Compound Interest Engine ─────────────────────────────────────────────────
// Pure TypeScript — zero dependencies. Importable in Node.js, browser, or edge.

import type {
  ScenarioParams,
  DataPoint,
  ScenarioResult,
  ComparisonResult,
  CompoundFrequency,
} from '../types';

// ── Compounding periods per year ──────────────────────────────────────────────
export const FREQ_N: Record<CompoundFrequency, number> = {
  daily: 365,
  monthly: 12,
  quarterly: 4,
  annually: 1,
};

export const FREQ_LABELS: Record<CompoundFrequency, string> = {
  daily: 'Daily (365×/yr)',
  monthly: 'Monthly (12×/yr)',
  quarterly: 'Quarterly (4×/yr)',
  annually: 'Annually (1×/yr)',
};

// ── Core formula ──────────────────────────────────────────────────────────────
// A = P(1 + r/n)^(nt)  +  PMT × [(1 + r/n)^(nt) − 1] / (r/n)
//
// Where:
//   P   = principal (initial deposit)
//   r   = annual interest rate as decimal
//   n   = compounding periods per year
//   t   = time in years
//   PMT = monthly contribution (converted to per-period below)
//
// Monthly contributions are converted to per-period contributions by
// scaling with (12 / n), then applied as an ordinary annuity.

export function calcBalance(
  principal: number,
  annualRate: number,
  years: number,
  monthlyContrib: number,
  frequency: CompoundFrequency
): number {
  const n = FREQ_N[frequency];
  const r = annualRate / 100;
  const periodicRate = r / n;
  const totalPeriods = n * years;
  // Contribution per compounding period
  const contribPerPeriod = monthlyContrib * (12 / n);

  const fvPrincipal = principal * Math.pow(1 + periodicRate, totalPeriods);
  const fvContribs =
    periodicRate > 0
      ? contribPerPeriod * ((Math.pow(1 + periodicRate, totalPeriods) - 1) / periodicRate)
      : contribPerPeriod * totalPeriods;

  return fvPrincipal + fvContribs;
}

// ── Simple interest (for comparison) ─────────────────────────────────────────
export function calcSimpleBalance(
  principal: number,
  annualRate: number,
  years: number,
  monthlyContrib: number
): number {
  const r = annualRate / 100;
  const fvPrincipal = principal * (1 + r * years);
  const fvContribs  = monthlyContrib * 12 * years * (1 + r * years / 2); // approx midpoint
  return fvPrincipal + fvContribs;
}

// ── Rule of 72 ────────────────────────────────────────────────────────────────
// Approximate years to double: 72 / rate%
// More accurate Eckart–McHale correction: 69.3/r + 0.35
export function doublingYears(annualRate: number): number {
  if (annualRate <= 0) return Infinity;
  return 72 / annualRate; // classic approximation
}

// ── Inflation-adjusted final value ────────────────────────────────────────────
export function inflationAdjust(
  nominalBalance: number,
  years: number,
  inflationRate = 3
): number {
  return nominalBalance / Math.pow(1 + inflationRate / 100, years);
}

// ── Build year-by-year series ─────────────────────────────────────────────────
export function buildSeries(params: ScenarioParams): DataPoint[] {
  const { principal, annualRate, years, monthlyContrib, frequency } = params;
  const points: DataPoint[] = [];

  for (let y = 0; y <= years; y++) {
    const balance  = Math.round(calcBalance(principal, annualRate, y, monthlyContrib, frequency));
    const invested = Math.round(principal + monthlyContrib * 12 * y);
    const interest = balance - invested;
    const growthPct = invested > 0 ? ((balance / invested) - 1) * 100 : 0;
    points.push({ year: y, balance, invested, interest, growthPct });
  }

  return points;
}

// ── Full scenario evaluation ──────────────────────────────────────────────────
export function evaluateScenario(params: ScenarioParams): ScenarioResult {
  const series = buildSeries(params);
  const final  = series[series.length - 1];

  return {
    params,
    series,
    final,
    doublingYears: doublingYears(params.annualRate),
    inflationAdjusted: inflationAdjust(final.balance, params.years),
  };
}

// ── Compare two scenarios ─────────────────────────────────────────────────────
export function compareScenarios(
  paramsA: ScenarioParams,
  paramsB: ScenarioParams
): ComparisonResult {
  const a = evaluateScenario(paramsA);
  const b = evaluateScenario(paramsB);
  const diff = a.final.balance - b.final.balance;
  const leader = diff > 0 ? 'A' : diff < 0 ? 'B' : 'tie';

  return {
    a,
    b,
    leader,
    absoluteDiff: Math.abs(diff),
    relativeDiff: b.final.balance > 0 ? (Math.abs(diff) / b.final.balance) * 100 : 0,
    maxYears: Math.max(paramsA.years, paramsB.years),
  };
}

// ── Format helpers (no React, safe for Node.js) ───────────────────────────────
export const fmt = {
  currency: (n: number): string =>
    '$' + Math.round(n).toLocaleString('en-US'),

  currencyShort: (n: number): string => {
    const abs = Math.abs(n);
    const sign = n < 0 ? '-' : '';
    if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
    if (abs >= 1_000)     return `${sign}$${(abs / 1_000).toFixed(1)}k`;
    return `${sign}$${Math.round(abs)}`;
  },

  pct: (n: number, decimals = 1): string => `${n.toFixed(decimals)}%`,

  years: (n: number): string => `${n.toFixed(1)} yr${n !== 1 ? 's' : ''}`,
};
