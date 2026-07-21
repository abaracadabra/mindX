// Substrate instrument rack — the landing page's hardware readout.
//
// Two read-only dreamknob racks driven by the mind's own insight endpoints:
//   · /insight/substrate/evolution  (agents/substrate_evolver.py, per dream cycle)
//   · /insight/godel/recent         (godel choices — the self-reference audit trail)
// Same doctrine as the mesh: nothing here is authored — every needle, LED and
// digit IS the number the mind produced. No control on this panel accepts input.
import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  DreamknobProvider, Rack, Gauge, SegmentDisplay, AlphaDisplay,
  MeterBridge, LampRow, FlatKnob, SteppedKnob,
} from 'dreamknob'

const GOLD = '#e3b341', BLUE = '#58a6ff', GREEN = '#56d364', PURPLE = '#ba94ff'
const INK3 = '#6b7480'
const MONO = "'JetBrains Mono','SF Mono','Fira Code',ui-monospace,monospace"

const THEME = {
  accent: GOLD,
  track: 'rgba(120,132,148,.18)',
  face: '#0a0e16',
  text: '#e6edf3',
  label: INK3,
  ticks: '#3a4350',
  panel: 'rgba(6,9,15,.72)',
  ledGreen: GREEN,
  ledAmber: GOLD,
  fontMono: MONO,
}

// AlphaDisplay charset: A-Z 0-9 space - _ = + * / \ ? $ : % .
function tickerText(s) {
  return (s || '')
    .toUpperCase()
    .replace(/Δ/g, ' DELTA ')
    .replace(/,/g, ' - ')
    .replace(/[^A-Z0-9 \-_=+*/\\?$:%.]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function Ticker({ text, chars = 34 }) {
  const msg = tickerText(text)
  const scrolls = msg.length > chars
  const loop = scrolls ? msg + '  ***  ' : msg
  const [off, setOff] = useState(0)
  useEffect(() => {
    if (!scrolls) return
    if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setOff(o => (o + 1) % loop.length), 220)
    return () => clearInterval(id)
  }, [loop, scrolls])
  const view = scrolls ? (loop + loop).slice(off, off + chars) : msg
  return <AlphaDisplay value={view} chars={chars} height={15} aria-hidden />
}

function Strip({ caption, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 7 }}>
      {children}
      <span style={{ fontFamily: MONO, fontSize: 9.5, letterSpacing: '.16em', color: INK3 }}>
        {caption}
      </span>
    </div>
  )
}

const ROW_STYLE = {
  display: 'flex', flexWrap: 'wrap', gap: 22,
  justifyContent: 'center', alignItems: 'center',
}
const TICKER_STYLE = {
  display: 'flex', justifyContent: 'center',
  marginTop: 14, paddingTop: 12,
  borderTop: '1px solid rgba(120,132,148,.14)',
}

function SubstrateRack({ evo }) {
  const mesh = evo.mesh || {}
  const stats = evo.stats || {}
  const dream = stats.dream || {}
  const ascent = stats.ascent || {}
  const offload = stats.offload || {}

  const energyPct = Math.round((Number(mesh.energy) || 0) * 100)
  const delta = typeof ascent.delta === 'number' ? ascent.delta : null
  const deltaRange = delta === null ? 0.01 : Math.max(0.01, Math.abs(delta) * 1.5)
  const rawGb = (Number(offload.raw_bytes) || 0) / 1e9
  const gzGb = (Number(offload.gz_bytes) || 0) / 1e9
  const meterMax = Math.max(1, Math.ceil(rawGb * 1.15))

  return (
    <Rack
      title="SUBSTRATE INSTRUMENTS · LIVE"
      orientation="column"
      gap={0}
      padding={18}
      accentColor={GOLD}
      style={{ width: '100%' }}
      aria-label="Substrate instrument rack — read-only gauges of the mind's last dream cycle"
    >
      <div style={ROW_STYLE}>
      <Strip caption="GENERATION">
        <SegmentDisplay value={evo.generation} digits={3} height={30} color={GREEN} />
      </Strip>

      <Gauge value={energyPct} min={0} max={100} size={86} unit="%" digits={3}
        color={GOLD} label="MESH ENERGY" aria-label="Mesh energy" />
      <Gauge value={Number(mesh.nodes) || 0} min={0} max={140} size={86} digits={3}
        color={BLUE} label="MESH NODES" aria-label="Mesh nodes" />
      <Gauge value={Number(mesh.link_dist) || 0} min={0} max={240} size={86} digits={3}
        color={GREEN} label="LINK REACH" aria-label="Link reach" />

      {delta !== null && (
        <FlatKnob
          readOnly
          value={delta}
          min={-deltaRange}
          max={deltaRange}
          origin={0}
          arcFrom="center"
          size={86}
          label="IMPRINT"
          sublabel={String(
            ascent.model || String(ascent.label || '').replace(/_/g, ' ') ||
            `gen ${ascent.generation ?? '—'}`
          ).slice(0, 18)}
          format={v => (v > 0 ? '+' : '') + v.toFixed(4)}
          color={ascent.imprinted ? GREEN : INK3}
          aria-label={`Imprint recall delta ${delta}`}
        />
      )}

      {Number(offload.bundles) > 0 && (
        <MeterBridge
          channels={[
            { label: 'RAW', value: rawGb },
            { label: 'GZ', value: gzGb },
          ]}
          min={0} max={meterMax}
          length={84} breadth={9} segments={20}
          peakTextDecimals={2}
          label="OFF-NODE GB"
          aria-label={`Distributed memory: ${rawGb.toFixed(2)} GB raw, ${gzGb.toFixed(2)} GB compressed`}
        />
      )}

      <LampRow
        size={9}
        labelPosition="below"
        gap={16}
        aria-label="Cycle status lamps"
        lamps={[
          { label: 'DREAMED', on: (Number(dream.agents) || 0) > 0, color: BLUE },
          { label: 'IMPRINTED', on: !!ascent.imprinted, color: GREEN },
          { label: 'DISTRIBUTED', on: !!mesh.distributed, color: PURPLE },
        ]}
      />
      </div>

      <div style={TICKER_STYLE}>
        <Strip caption="LAST CYCLE">
          <Ticker text={evo.headline} chars={44} />
        </Strip>
      </div>
    </Rack>
  )
}

// ── Gödel choices rack — /insight/godel/recent, computed client-side ──
const CONFIDENCE = ['LOW', 'MED', 'HIGH']

function godelMetrics(events) {
  const total = events.length
  const byType = {}
  for (const e of events) byType[e.choice_type] = (byType[e.choice_type] || 0) + 1
  const degraded = byType.degraded_planning || 0
  const scores = events.map(e => Number(e.eval_score)).filter(n => Number.isFinite(n))
  const evalMean = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null

  const latestSel = events.find(e => e.choice_type === 'self_aware_model_selection')
  const confMatch = latestSel && /confidence=(\w+)/.exec(latestSel.rationale || '')
  const conf = confMatch ? confMatch[1].toLowerCase() : null
  const confIdx = conf === 'high' ? 2 : conf === 'medium' || conf === 'med' ? 1 : conf === 'low' ? 0 : null

  const validated = events.some(e => /validated_changes=True/i.test(e.rationale || ''))
  const latest = events[0]
  return {
    total, byType, degraded, evalMean, confIdx, conf, validated,
    model: latestSel ? latestSel.chosen_option : null,
    latestTs: latest ? latest.timestamp_utc : null,
  }
}

function GodelRack({ events }) {
  const m = godelMetrics(events)
  const sel = (m.byType.self_aware_model_selection || 0)
  const exec = (m.byType.mindx_improvement_execution || 0) + (m.byType.mindx_improvement_selection || 0)
  const backlog = m.byType.backlog_directive_selection || 0

  const ticker = [
    m.model ? `MODEL: ${m.model}` : null,
    m.evalMean !== null ? `EVAL ${m.evalMean.toFixed(2)}` : null,
    `VALIDATED: ${m.validated ? 'TRUE' : 'FALSE'}`,
  ].filter(Boolean).join(' - ')

  return (
    <Rack
      title="GODEL CHOICES · LAST 50 · SELF-REFERENCE AUDIT"
      orientation="column"
      gap={0}
      padding={18}
      accentColor={BLUE}
      style={{ width: '100%' }}
      aria-label="Gödel choice rack — read-only instruments over the machine's recent decisions"
    >
      <div style={ROW_STYLE}>
      <Strip caption="CHOICES">
        <SegmentDisplay value={m.total} digits={3} height={30} color={BLUE} />
      </Strip>

      {/* default theme zones: green → amber → red as degradation climbs — semantically honest */}
      <Gauge value={m.total ? Math.round((m.degraded / m.total) * 100) : 0}
        min={0} max={100} size={86} unit="%" digits={3}
        label="DEGRADED" aria-label="Share of degraded planning choices" />

      {m.evalMean !== null && (
        <Gauge value={Math.round(m.evalMean * 100)} min={0} max={100} size={86} unit="%" digits={3}
          color={GOLD} label="EVAL SCORE" aria-label="Mean alignment eval score" />
      )}

      {m.confIdx !== null && (
        <SteppedKnob
          readOnly
          positions={CONFIDENCE}
          value={m.confIdx}
          size={86}
          label="CONFIDENCE"
          sublabel="model selection"
          color={m.confIdx === 2 ? GREEN : m.confIdx === 1 ? GOLD : INK3}
          aria-label={`Latest selection confidence ${CONFIDENCE[m.confIdx]}`}
        />
      )}

      <MeterBridge
        channels={[
          { label: 'SEL', value: sel },
          { label: 'IMP', value: exec },
          { label: 'BKL', value: backlog },
          { label: 'DEG', value: m.degraded },
        ]}
        min={0} max={Math.max(1, m.total)}
        length={84} breadth={9} segments={20}
        peakTextDecimals={0}
        label="CHOICE MIX"
        aria-label="Choice type distribution"
      />

      <LampRow
        size={9}
        labelPosition="below"
        gap={16}
        aria-label="Gödel loop status lamps"
        lamps={[
          { label: 'SELECTING', on: sel > 0, color: BLUE },
          { label: 'EXECUTING', on: exec > 0, color: GOLD },
          { label: 'VALIDATED', on: m.validated, color: GREEN },
          { label: 'DEGRADED', on: m.degraded > 0, color: '#e0654a' },
        ]}
      />
      </div>

      <div style={TICKER_STYLE}>
        <Strip caption="LATEST">
          <Ticker text={ticker} chars={44} />
        </Strip>
      </div>
    </Rack>
  )
}

function Racks({ evo, godel }) {
  return (
    <DreamknobProvider base="dark" theme={THEME}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, width: '100%' }}>
        {evo && <SubstrateRack evo={evo} />}
        {godel && godel.length > 0 && <GodelRack events={godel} />}
      </div>
    </DreamknobProvider>
  )
}

;(function mount() {
  const host = document.getElementById('substrate-rack')
  if (!host) return
  const get = url => fetch(url, { cache: 'no-store' })
    .then(r => (r.ok ? r.json() : null)).catch(() => null)
  Promise.all([
    get('/insight/substrate/evolution'),
    get('/insight/godel/recent'),
  ]).then(([evo, godel]) => {
    const hasEvo = evo && Number(evo.generation) > 0
    const events = (godel && godel.events) || []
    if (!hasEvo && !events.length) return
    host.hidden = false
    createRoot(host).render(<Racks evo={hasEvo ? evo : null} godel={events} />)
  })
})()
