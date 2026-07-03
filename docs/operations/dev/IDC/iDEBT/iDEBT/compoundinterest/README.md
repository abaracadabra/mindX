# compound-calculator

A modular, production-grade compound interest calculator in TSX.
Drop individual components into any React / Next.js / Vite / dApp project.

---

## Install peer dependencies

```bash
npm install react react-dom recharts
# TypeScript is assumed — no @types needed for recharts ≥2
```

---

## Quickstart

```tsx
import { CompoundCalculator } from './compound-calculator/src';

export default function App() {
  return <CompoundCalculator />;
}
```

---

## Module map

```
src/
├── index.ts                          ← barrel — import everything from here
├── types/index.ts                    ← TypeScript interfaces & enums
│
├── engine/
│   └── compound.engine.ts            ← pure JS — no React, works in Node.js
│       calcBalance()                 ← FV formula, any compounding frequency
│       calcSimpleBalance()           ← simple interest comparison
│       buildSeries()                 ← year-by-year DataPoint array
│       evaluateScenario()            ← full ScenarioResult
│       compareScenarios()            ← ComparisonResult (A vs B)
│       doublingYears()               ← Rule of 72
│       inflationAdjust()             ← real purchasing-power value
│       fmt.*                         ← formatting helpers
│
├── hooks/
│   └── useCompound.ts                ← React state + derived data for charts
│       returns: paramsA/B, updateA/B, comparison, labels, datasets, chartMode
│
└── components/
    ├── CompoundCalculator.tsx        ← root orchestrator (Calculator | Learn tabs)
    ├── popover/
    │   └── Popover.tsx               ← accessible popover + InfoTrigger + helpers
    ├── scenario/
    │   └── ScenarioCard.tsx          ← full input card with inline info popovers
    ├── chart/
    │   └── CompoundChart.tsx         ← Recharts: area / line / bars / interest-only
    ├── delta/
    │   └── DeltaSummary.tsx          ← leader bar + stats + milestone table
    └── explainer/
        └── ExplainerPanel.tsx        ← 8 tabbed educational sections
```

---

## Usage patterns

### Full calculator (two scenarios)
```tsx
import { CompoundCalculator } from './compound-calculator/src';
<CompoundCalculator />
```

### Just the chart
```tsx
import { useCompound, CompoundChart } from './compound-calculator/src';

function MyChart() {
  const { labels, datasets, chartMode, setChartMode } = useCompound();
  return (
    <CompoundChart
      labels={labels}
      datasets={datasets}
      chartMode={chartMode}
      onModeChange={setChartMode}
    />
  );
}
```

### Just the engine (Node.js / server-side)
```ts
import { evaluateScenario, compareScenarios, fmt } from './compound-calculator/src/engine/compound.engine';

const result = evaluateScenario({
  id: 'A',
  principal: 5000,
  annualRate: 7,
  years: 30,
  monthlyContrib: 200,
  frequency: 'monthly',
});

console.log(fmt.currency(result.final.balance)); // $227,927
console.log(fmt.years(result.doublingYears));     // 10.3 yrs
```

### Bring your own UI with the hook
```tsx
import { useCompound, evaluateScenario } from './compound-calculator/src';

function CustomUI() {
  const { paramsA, updateA, comparison } = useCompound();
  return (
    <div>
      <input
        type="number"
        value={paramsA.principal}
        onChange={e => updateA({ principal: +e.target.value })}
      />
      <p>Final balance: {comparison.a.final.balance}</p>
    </div>
  );
}
```

### Standalone Explainer
```tsx
import { ExplainerPanel } from './compound-calculator/src';
<ExplainerPanel initialTab="formula" />
```

### Inline info popovers
```tsx
import { Popover, InfoTrigger, PopoverHeader, PopoverBody } from './compound-calculator/src';

<Popover
  trigger={<InfoTrigger color="#7a7f8e" size={14} />}
  placement="bottom"
  width={300}
>
  <PopoverHeader title="Annual Rate" subtitle="APY" />
  <PopoverBody>
    The percentage return per year, compounded at the chosen frequency.
  </PopoverBody>
</Popover>
```

---

## Core formula

```
A = P(1 + r/n)^(nt)  +  PMT × [(1 + r/n)^(nt) − 1] / (r/n)

P   — principal (initial deposit)
r   — annual rate as decimal (7% → 0.07)
n   — compounding periods/yr (12 for monthly)
t   — years
PMT — contribution per compounding period
```

Monthly contributions are scaled to per-period: `PMT_period = monthly × (12 / n)`.

---

## Compounding frequencies

| Key         | n   | EAR at 7%  |
|-------------|-----|------------|
| `daily`     | 365 | 7.2501%    |
| `monthly`   | 12  | 7.2290%    |
| `quarterly` | 4   | 7.1859%    |
| `annually`  | 1   | 7.0000%    |

---

## Types

```ts
type CompoundFrequency = 'daily' | 'monthly' | 'quarterly' | 'annually';
type ChartMode = 'grouped' | 'line' | 'area' | 'interest-only';
type ExplainerTab = 'overview' | 'formula' | 'principal' | 'rate'
                  | 'time' | 'frequency' | 'vs-simple' | 'rule72';

interface ScenarioParams {
  id: 'A' | 'B';
  principal: number;
  annualRate: number;
  years: number;
  monthlyContrib: number;
  frequency: CompoundFrequency;
}

interface DataPoint {
  year: number;
  balance: number;
  invested: number;
  interest: number;
  growthPct: number;
}

interface ScenarioResult {
  params: ScenarioParams;
  series: DataPoint[];
  final: DataPoint;
  doublingYears: number;
  inflationAdjusted?: number;
}
```

---

## License
MIT
