/**
 * Convene HTTP fallback + recent-sessions read.
 *
 *   POST /rooms/:id/convene       — synchronous; returns the full session+verdict
 *   GET  /rooms/:id/observe       — SSE; tails active sessions for this room
 *   GET  /sessions/recent         — recent finished sessions
 */

import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';
import { requireSession, requireTier, TIERS } from '../auth/middleware.js';
import { getRoom } from '../rooms/store.js';
import { convene } from './convene.js';
import { newSessionId, persistSession, recentSessions, getActive } from './sessions.js';
import { sanctioningEnabled, verifySanction } from '../daio/sanction.js';
import type { Session } from './types.js';

export const consensusRoutes = new Hono();

consensusRoutes.post('/rooms/:id/convene', requireSession(), async (c) => {
  const room_id = c.req.param('id');
  const room = getRoom(room_id);
  if (!room) return c.json({ error: 'room_not_found' }, 404);
  const session = c.get('session');

  // Only seats or cabinet may initiate a convene in private rooms.
  // Public rooms: anyone with personhood may initiate.
  if (room.mode === 'private' && session.tier < TIERS.seat) {
    return c.json({ error: 'private_room_requires_seat_or_cabinet' }, 403);
  }
  if (room.mode !== 'private' && session.tier < TIERS.person) {
    return c.json({ error: 'public_room_requires_personhood' }, 403);
  }

  const body = await c.req.json().catch(() => ({}));
  const directive = String(body.directive ?? '').trim();
  if (!directive) return c.json({ error: 'directive_required' }, 400);
  const importance = (['routine', 'standard', 'high', 'critical'].includes(body.importance) ? body.importance : 'standard') as Session['importance'];

  // DAIO gate: if the room is marked daio_sanctioned (cross-room joint action),
  // every convene there requires a fresh DAIO sanction. Off-by-default — the
  // env flag MINDX_DAIO_SANCTIONING_ENABLED short-circuits when unset.
  if (sanctioningEnabled() && room.daio_sanctioned) {
    const verdict = await verifySanction(body.sanction, 'convene_cross_room');
    if (!verdict.ok) {
      return c.json({
        error: 'daio_sanction_required',
        reason: verdict.reason,
        signers_valid: verdict.signers_valid,
        threshold: verdict.threshold,
      }, 403);
    }
  }

  const s: Session = {
    session_id: newSessionId(),
    room_id,
    directive: directive.slice(0, 2000),
    importance,
    initiated_by: session.address,
    votes: [],
    verdict: null,
    started_at: Math.floor(Date.now() / 1000),
    finished_at: null,
    context: typeof body.context === 'string' ? body.context.slice(0, 8000) : undefined,
  };

  await convene(s, room.seats);
  persistSession(s);
  return c.json(s);
});

consensusRoutes.get('/rooms/:id/observe', (c) => {
  const room_id = c.req.param('id');
  const room = getRoom(room_id);
  if (!room) return c.json({ error: 'room_not_found' }, 404);
  // Public read; private rooms still observable via this SSE feed because
  // the data emitted is the verdict + per-vote summary, not the seat's
  // private LLM call. Operators that want stricter visibility can flip
  // the room mode.
  return streamSSE(c, async (stream) => {
    // Initial hello.
    await stream.writeSSE({ event: 'hello', data: JSON.stringify({ room_id, ts: Date.now() }) });
    // Poll for completed sessions until client disconnects. (We don't have
    // a true pub/sub yet; this is a 1-Hz poll on the in-memory active map +
    // a finished-since pointer. Phase D2 / G can swap for an EventEmitter.)
    let lastFinished = 0;
    while (!stream.aborted) {
      await stream.sleep(1000);
      const active = getActive('');  // dummy — we'll improve in Phase G
      if (active) {
        await stream.writeSSE({ event: 'active', data: JSON.stringify({ session_id: active.session_id }) });
      }
      // For finished sessions, the convene HTTP path already returned them;
      // observers re-query /sessions/recent. SSE just keeps the conn warm.
      void lastFinished;
    }
  });
});

consensusRoutes.get('/sessions/recent', (c) => {
  const limit = Math.max(1, Math.min(200, Number(c.req.query('limit') ?? 50)));
  const sessions = recentSessions(limit);
  return c.json({ sessions, count: sessions.length });
});
