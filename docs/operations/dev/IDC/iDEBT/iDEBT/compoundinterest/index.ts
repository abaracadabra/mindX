// ─── compound-calculator/index.ts ────────────────────────────────────────────
// Public API — import only what you need.

// Root component (default export for convenience)
export { CompoundCalculator, default } from './components/CompoundCalculator';

// Sub-components (composable individually)
export { ScenarioCard }   from './components/scenario/ScenarioCard';
export { CompoundChart }  from './components/chart/CompoundChart';
export { DeltaSummary }   from './components/delta/DeltaSummary';
export { ExplainerPanel } from './components/explainer/ExplainerPanel';
export {
  Popover,
  InfoTrigger,
  PopoverHeader,
  PopoverBody,
  PopoverFormula,
  PopoverHighlight,
} from './components/popover/Popover';

// Hook (bring your own UI)
export { useCompound }    from './hooks/useCompound';
export type { CompoundCalculatorState } from './hooks/useCompound';

// Pure engine (Node.js / browser / edge — no React)
export {
  calcBalance,
  calcSimpleBalance,
  buildSeries,
  evaluateScenario,
  compareScenarios,
  doublingYears,
  inflationAdjust,
  FREQ_N,
  FREQ_LABELS,
  fmt,
} from './engine/compound.engine';

// Types
export type {
  ScenarioParams,
  DataPoint,
  ScenarioResult,
  ComparisonResult,
  CompoundFrequency,
  ChartMode,
  ExplainerTab,
} from './types';
