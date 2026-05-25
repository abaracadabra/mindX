/**
 * boardroom-service entry point.
 *
 * Listens on CONFIG.port (default 8771). Exposes three transport tiers:
 *
 *   HTTP    — /healthz, /version, /rooms (CRUD), /auth/* (challenge/verify),
 *             POST /rooms/{id}/convene (synchronous fallback for non-WS clients)
 *   SSE     — GET /rooms/{id}/observe (read-only stream)
 *   WSS     — /rooms/{id}/ws (agent ↔ agent bidirectional)
 *
 * Apache fronts this at /boardroom-svc/* on mindx.pythai.net with
 * upgrade=websocket on the proxy directive.
 */

import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { CONFIG, loadAgentMap } from './config.js';
import { log } from './log.js';
import { authRoutes } from './auth/routes.js';
import { roomsRoutes } from './rooms/routes.js';
import { loadRoomStore, ensureMindxDefaultRoom } from './rooms/store.js';

const app = new Hono();

app.route('/auth', authRoutes);
app.route('/rooms', roomsRoutes);

// Boot room store + ensure mindX-default private room.
loadRoomStore();
ensureMindxDefaultRoom();

app.get('/healthz', (c) => c.json({
  status: 'ok',
  service: 'boardroom-service',
  version: '0.1.0',
  ts: Date.now(),
}));

app.get('/version', (c) => {
  const agentMap = loadAgentMap();
  return c.json({
    service: 'boardroom-service',
    version: '0.1.0',
    soldiers: Object.keys(agentMap.soldiers).length,
    warcouncil_seats: Object.keys(agentMap.warcouncil ?? {}).length,
    ceo: !!agentMap.ceo,
    domain: CONFIG.domain,
    transports: ['http', 'sse', 'wss'],
  });
});

// Routes wired in subsequent phases:
// app.route('/auth',  authRoutes);    // Phase B
// app.route('/rooms', roomsRoutes);   // Phase C
// app.route('/rooms', conveneRoutes); // Phase D (HTTP fallback + WS upgrade + SSE)

// Boot
const agentMap = loadAgentMap();
log('info', 'boot', 'agent_map.json loaded', {
  ceo: agentMap.ceo?.role,
  soldiers: Object.keys(agentMap.soldiers),
  warcouncil_size: Object.keys(agentMap.warcouncil ?? {}).length,
});

serve({
  fetch: app.fetch,
  port: CONFIG.port,
}, (info) => {
  log('info', 'boot', `boardroom-service listening on ${info.address}:${info.port}`, {
    port: info.port,
    domain: CONFIG.domain,
  });
});

// Graceful shutdown — important so systemd's stop signal lands cleanly.
const shutdown = (sig: string) => {
  log('info', 'shutdown', `received ${sig}, exiting`);
  process.exit(0);
};
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
