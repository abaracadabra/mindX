// ─── Compound Interest Calculator — Type Definitions ─────────────────────────

export type CompoundFrequency = 'daily' | 'monthly' | 'quarterly' | 'annually';

export interface ScenarioParams {
  id: 'A' | 'B';
  principal: number;       // initial lump-sum deposit ($)
  annualRate: number;      // annual interest rate (%)
  years: number;           // investment horizon
  monthlyContrib: number;  // recurring monthly contribution ($)
  frequency: CompoundFrequency;
}

export interface DataPoint {
  year: number;
  balance: number;         // total portfolio value
  invested: number;        // cumulative money put in
  interest: number;        // interest earned = balance - invested
  growthPct: number;       // (balance / invested - 1) * 100
}

export interface ScenarioResult {
  params: ScenarioParams;
  series: DataPoint[];
  final: DataPoint;
  doublingYears: number;   // Rule of 72
  inflationAdjusted?: number; // optional real-value at 3% inflation
}

export interface ComparisonResult {
  a: ScenarioResult;
  b: ScenarioResult;
  leader: 'A' | 'B' | 'tie';
  absoluteDiff: number;
  relativeDiff: number;    // %
  maxYears: number;
}

export type ChartMode = 'grouped' | 'line' | 'area' | 'interest-only';
export type ExplainerTab =
  | 'overview'
  | 'formula'
  | 'principal'
  | 'rate'
  | 'time'
  | 'frequency'
  | 'vs-simple'
  | 'rule72';
