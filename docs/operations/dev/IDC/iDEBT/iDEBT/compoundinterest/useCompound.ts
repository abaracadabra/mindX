// ─── useCompound Hook ─────────────────────────────────────────────────────────
// Manages both scenarios, runs comparison, and exposes chart-ready data.

import { useState, useMemo, useCallback } from 'react';
import type { ScenarioParams, ComparisonResult, ChartMode, CompoundFrequency } from '../types';
import { compareScenarios, evaluateScenario, FREQ_N } from '../engine/compound.engine';

const DEFAULT_A: ScenarioParams = {
  id: 'A',
  principal: 5000,
  annualRate: 7,
  years: 30,
  monthlyContrib: 200,
  frequency: 'monthly',
};

const DEFAULT_B: ScenarioParams = {
  id: 'B',
  principal: 5000,
  annualRate: 7,
  years: 10,
  monthlyContrib: 100,
  frequency: 'monthly',
};

export interface ChartDataset {
  label: string;
  scenarioId: 'A' | 'B';
  type: 'balance' | 'invested' | 'interest';
  data: (number | null)[];
}

export interface CompoundCalculatorState {
  paramsA: ScenarioParams;
  paramsB: ScenarioParams;
  comparison: ComparisonResult;
  chartMode: ChartMode;
  labels: string[];
  datasets: ChartDataset[];
  updateA: (patch: Partial<ScenarioParams>) => void;
  updateB: (patch: Partial<ScenarioParams>) => void;
  setChartMode: (mode: ChartMode) => void;
  resetAll: () => void;
}

export function useCompound(): CompoundCalculatorState {
  const [paramsA, setParamsA] = useState<ScenarioParams>(DEFAULT_A);
  const [paramsB, setParamsB] = useState<ScenarioParams>(DEFAULT_B);
  const [chartMode, setChartMode] = useState<ChartMode>('area');

  const updateA = useCallback(
    (patch: Partial<ScenarioParams>) => setParamsA(p => ({ ...p, ...patch })),
    []
  );
  const updateB = useCallback(
    (patch: Partial<ScenarioParams>) => setParamsB(p => ({ ...p, ...patch })),
    []
  );
  const resetAll = useCallback(() => {
    setParamsA(DEFAULT_A);
    setParamsB(DEFAULT_B);
    setChartMode('area');
  }, []);

  const comparison = useMemo(() => compareScenarios(paramsA, paramsB), [paramsA, paramsB]);

  // Build aligned labels + datasets for the chart
  const { labels, datasets } = useMemo(() => {
    const maxY = Math.max(paramsA.years, paramsB.years);
    const step  = maxY > 40 ? 10 : maxY > 25 ? 5 : maxY > 15 ? 2 : 1;

    const yearMarks: number[] = [];
    for (let y = 0; y <= maxY; y += step) yearMarks.push(y);
    if (yearMarks[yearMarks.length - 1] !== maxY) yearMarks.push(maxY);

    const lbl = yearMarks.map(y => (y === 0 ? 'Now' : `Yr ${y}`));

    function project(
      series: typeof comparison.a.series,
      yr: number,
      key: keyof (typeof series)[0]
    ): number | null {
      const pt = series.find(p => p.year === yr);
      return pt ? (pt[key] as number) : null;
    }

    const ds: ChartDataset[] =
      chartMode === 'interest-only'
        ? [
            { label: 'A interest earned', scenarioId: 'A', type: 'interest', data: yearMarks.map(y => project(comparison.a.series, y, 'interest')) },
            { label: 'B interest earned', scenarioId: 'B', type: 'interest', data: yearMarks.map(y => project(comparison.b.series, y, 'interest')) },
          ]
        : [
            { label: 'A balance',  scenarioId: 'A', type: 'balance',  data: yearMarks.map(y => project(comparison.a.series, y, 'balance')) },
            { label: 'A invested', scenarioId: 'A', type: 'invested', data: yearMarks.map(y => project(comparison.a.series, y, 'invested')) },
            { label: 'B balance',  scenarioId: 'B', type: 'balance',  data: yearMarks.map(y => project(comparison.b.series, y, 'balance')) },
            { label: 'B invested', scenarioId: 'B', type: 'invested', data: yearMarks.map(y => project(comparison.b.series, y, 'invested')) },
          ];

    return { labels: lbl, datasets: ds };
  }, [comparison, chartMode, paramsA.years, paramsB.years]);

  return {
    paramsA, paramsB,
    comparison,
    chartMode, setChartMode,
    labels, datasets,
    updateA, updateB,
    resetAll,
  };
}
