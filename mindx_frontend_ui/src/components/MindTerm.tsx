import React, { useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";

type WSMsg =
  | { type: "out"; data: string }
  | { type: "risk"; line: string; level: string; reason: string }
  | { type: "sys"; data: string };

type Block = {
  block_id: string;
  command: string;
  created_at: string;
  started_at: string;
  finished_at: string | null;
  exit_code: number | null;
  output_len: number;
  meta: Record<string, any>;
};

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000";

export default function MindTerm() {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  const [pending, setPending] = useState<{ line: string; level: string; reason: string } | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [eventsConnected, setEventsConnected] = useState(false);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const getTermSize = () => {
    const term = termRef.current;
    if (!term) return { cols: 120, rows: 40 };
    return { cols: term.cols || 120, rows: term.rows || 40 };
  };

  const createSession = async (cols: number, rows: number) => {
    const r = await fetch(`${API_BASE}/mindterm/sessions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ shell: null, cwd: null, cols, rows })
    });
    if (!r.ok) throw new Error(`create session failed: ${r.status}`);
    const j = await r.json();
    return j.session_id as string;
  };

  const postResize = async (sid: string, cols: number, rows: number) => {
    await fetch(`${API_BASE}/mindterm/sessions/${sid}/resize`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ cols, rows })
    });
  };

  const refreshBlocks = async (sid: string) => {
    const r = await fetch(`${API_BASE}/mindterm/sessions/${sid}/blocks?limit=80`);
    if (!r.ok) return;
    const j = await r.json();
    setBlocks(j.blocks ?? []);
  };

  const connect = (sid: string) => {
    const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/mindterm/sessions/${sid}/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      termRef.current?.write(`\r\n[mindterm] connected session ${sid}\r\n`);
    };

    ws.onmessage = async (ev) => {
      const msg: WSMsg = JSON.parse(ev.data);
      if (msg.type === "out") {
        termRef.current?.write(msg.data);
      } else if (msg.type === "risk") {
        setPending({ line: msg.line, level: msg.level, reason: msg.reason });
        termRef.current?.write(
          `\r\n[mindterm][RISK:${msg.level}] ${msg.reason}\r\n[mindterm] confirm in side panel.\r\n`
        );
      } else if (msg.type === "sys") {
        termRef.current?.write(`\r\n[mindterm] ${msg.data}\r\n`);
        // likely new block started/finished soon
        await refreshBlocks(sid);
      }
    };

    ws.onclose = () => {
      termRef.current?.write(`\r\n[mindterm] disconnected\r\n`);
    };
  };

  const connectEvents = (sid: string) => {
    // Optional observer channel (useful for debugging + mindX agent subscriptions)
    const ew = new WebSocket(`${API_BASE.replace("http", "ws")}/mindterm/sessions/${sid}/events`);
    ew.onopen = () => setEventsConnected(true);
    ew.onclose = () => setEventsConnected(false);
    ew.onmessage = async (ev) => {
      // If you want: display events or feed into mindX UI state.
      // For now, refresh blocks on finishes.
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "CommandFinished" || msg.type === "CommandStarted") {
          await refreshBlocks(sid);
        }
      } catch {}
    };
  };

  useEffect(() => {
    if (!hostRef.current) return;

    const term = new Terminal({
      convertEol: true,
      cursorBlink: true,
      fontSize: 13
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(hostRef.current);
    fit.fit();

    termRef.current = term;
    fitRef.current = fit;

    const ro = new ResizeObserver(async () => {
      fit.fit();
      const sid = sessionIdRef.current;
      if (!sid) return;
      const t = termRef.current;
      if (!t) return;
      try { await postResize(sid, t.cols, t.rows); } catch {}
    });
    ro.observe(hostRef.current);

    // Keystrokes:
    // - Always forward raw data to PTY
    // - Additionally send {type:"line"} only on Enter for policy-gated execution
    let lineBuf = "";

    term.onData((data) => {
      // Enter (CR)
      if (data === "\r") {
        wsRef.current?.send(JSON.stringify({ type: "line", data: lineBuf }));
        lineBuf = "";
        // Send CR to keep shell prompt behavior consistent
        wsRef.current?.send(JSON.stringify({ type: "in", data: "\r" }));
        return;
      }
      // Backspace
      if (data === "\u007f") {
        lineBuf = lineBuf.slice(0, -1);
        wsRef.current?.send(JSON.stringify({ type: "in", data }));
        return;
      }
      // Other keys
      lineBuf += data;
      wsRef.current?.send(JSON.stringify({ type: "in", data }));
    });

    (async () => {
      term.write("mindterm v0.0.4 (mindX)\r\n");
      const { cols, rows } = getTermSize();
      const sid = await createSession(cols, rows);
      setSessionId(sid);
      connect(sid);
      connectEvents(sid);
      await refreshBlocks(sid);
    })().catch((e) => {
      term.write(`\r\n[error] ${String(e)}\r\n`);
    });

    return () => {
      ro.disconnect();
      wsRef.current?.close();
      term.dispose();
    };
  }, []);

  const confirm = (allow: boolean) => {
    wsRef.current?.send(JSON.stringify({ type: "confirm", allow }));
    setPending(null);
  };

  return (
    <div style={{ display: "flex", height: "100%", gap: 12 }}>
      <div style={{ flex: 1, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12, overflow: "hidden" }}>
        <div ref={hostRef} style={{ height: "100%" }} />
      </div>

      <div style={{ width: 420, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 700 }}>mindterm</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>
              session: {sessionId ?? "…"} | events: {eventsConnected ? "on" : "off"}
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 600 }}>Policy gate</div>
            {pending ? (
              <>
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  <div><b>Level:</b> {pending.level}</div>
                  <div><b>Reason:</b> {pending.reason}</div>
                  <div style={{ marginTop: 8 }}><b>Command:</b></div>
                  <pre style={{ whiteSpace: "pre-wrap" }}>{pending.line}</pre>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => confirm(true)}>Allow</button>
                  <button onClick={() => confirm(false)}>Deny</button>
                </div>
              </>
            ) : (
              <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>
                No pending confirmations.
              </div>
            )}
          </div>
        </div>

        <div style={{ flex: 1, padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12, overflow: "auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 600 }}>Command blocks</div>
            <button
              onClick={async () => {
                if (!sessionId) return;
                await refreshBlocks(sessionId);
              }}
            >
              Refresh
            </button>
          </div>

          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
            {blocks.length === 0 ? (
              <div style={{ fontSize: 12, opacity: 0.8 }}>No blocks yet.</div>
            ) : (
              blocks.slice().reverse().map((b) => (
                <div key={b.block_id} style={{ padding: 10, border: "1px solid rgba(255,255,255,0.10)", borderRadius: 10 }}>
                  <div style={{ fontSize: 12, opacity: 0.85 }}>
                    <span style={{ fontWeight: 700 }}>{b.exit_code === null ? "RUN" : (b.exit_code === 0 ? "OK" : `ERR ${b.exit_code}`)}</span>
                    {" · "}
                    <span>{b.block_id.slice(0, 10)}</span>
                    {" · "}
                    <span>{b.finished_at ? "finished" : "running"}</span>
                  </div>
                  <pre style={{ margin: "8px 0 0", whiteSpace: "pre-wrap" }}>{b.command}</pre>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ fontSize: 12, opacity: 0.75 }}>
          v0.0.4 notes: blocks use a bash-compatible sentinel wrapper; if the user changes shell semantics heavily, sentinel parsing may miss.
        </div>
      </div>
    </div>
  );
}

