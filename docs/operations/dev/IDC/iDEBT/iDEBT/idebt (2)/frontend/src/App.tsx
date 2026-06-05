import { useState } from "react";
import { StressIndexDashboard } from "./components/StressIndexDashboard.js";
import { InheritanceForm }      from "./components/InheritanceForm.js";
import { ChainMap }             from "./components/ChainMap.js";
import { X402Payment }          from "./components/X402Payment.js";

type Tab = "index" | "open" | "chains" | "pay";

export default function App() {
  const [tab, setTab] = useState<Tab>("index");

  return (
    <div style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace", minHeight: "100vh", background: "#0a0a0a", color: "#e5e5e5" }}>
      <header style={{ borderBottom: "1px solid #222", padding: "16px 24px", display: "flex", alignItems: "center", gap: 24 }}>
        <strong style={{ letterSpacing: 1.5 }}>iDEBT</strong>
        <span style={{ opacity: 0.5, fontSize: 12 }}>Cryptographic Inheritance of Global DEBT</span>
        <nav style={{ marginLeft: "auto", display: "flex", gap: 16 }}>
          <Tab label="Index"        id="index"  active={tab} onClick={setTab} />
          <Tab label="Open"         id="open"   active={tab} onClick={setTab} />
          <Tab label="Chains"       id="chains" active={tab} onClick={setTab} />
          <Tab label="x402"         id="pay"    active={tab} onClick={setTab} />
        </nav>
      </header>

      <main style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
        {tab === "index"  && <StressIndexDashboard />}
        {tab === "open"   && <InheritanceForm />}
        {tab === "chains" && <ChainMap />}
        {tab === "pay"    && <X402Payment />}
      </main>
    </div>
  );
}

function Tab({ label, id, active, onClick }: {
  label: string;
  id: Tab;
  active: Tab;
  onClick: (t: Tab) => void;
}) {
  const isActive = id === active;
  return (
    <button
      onClick={() => onClick(id)}
      style={{
        background: "transparent",
        border: "none",
        color: isActive ? "#fff" : "#888",
        borderBottom: isActive ? "1px solid #fff" : "1px solid transparent",
        padding: "4px 2px",
        cursor: "pointer",
        fontFamily: "inherit"
      }}
    >
      {label}
    </button>
  );
}
