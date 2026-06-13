/**
 * WebSocket handler for /rooms/:id/ws — bidirectional agentic interaction.
 *
 * Wire protocol (text frames, JSON):
 *
 *   S→C  hello             { room_id, session_id?, your_tier, seats: [...] }
 *   C→S  convene           { directive, importance?, context? }
 *   S→C  vote.start        { session_id, directive }
 *   S→C  vote.delta        { session_id, seat, content_delta }
 *   S→C  vote.complete     { session_id, seat, vote, reasoning }
 *   S→C  verdict.final     { session_id, verdict, votes }
 *   C→S  amendment.propose { payload }              (tier ≥ seat to propose)
 *   C→S  question.ask      { to_seat?, text }       (tier ≥ person)
 *   S→C  question.broadcast{ from, to_seat?, text }
 *   C→S  auth.refresh      { token }                (tier upgrade mid-session)
 *   S→C  error             { code, detail }
 *   S→C  pong / C→S  ping  (10s keepalive)
 *
 * Auth: Bearer JWT on the Upgrade request; verified once at handshake.
 * Tier-upgrade control frame re-issues by validating a fresh Bearer the
 * client provides in an auth.refresh message.
 */

import { createNodeWebSocket } from '@hono/node-ws';
import type { Hono } from 'hono';
import type { WSContext } from 'hono/ws';
import { verifySession } from '../auth/session.js';
import { TIERS } from '../auth/tiers.js';
import { getRoom } from '../rooms/store.js';
import { convene, castVote } from '../consensus/convene.js';
import { aggregateVotes } from '../consensus/verdict.js';
import { newSessionId, persistSession } from '../consensus/sessions.js';
import { log } from '../log.js';
import type { Session, Vote } from '../consensus/types.js';
import type { TieredSession } from '../auth/tiers.js';

interface WSClient {
  ws: WSContext;
  session: TieredSession;
  room_id: string;
}

const ROOM_CLIENTS = new Map<string, Set<WSClient>>();

function broadcast(room_id: string, frame: object): void {
  const clients = ROOM_CLIENTS.get(room_id);
  if (!clients) return;
  const payload = JSON.stringify(frame);
  for (const c of clients) {
    try { c.ws.send(payload); } catch { /* dropped client; cleanup on close */ }
  }
}

function send(ws: WSContext, frame: object): void {
  try { ws.send(JSON.stringify(frame)); } catch { /* swallow */ }
}

export function wireWebSocket(app: Hono): { injectWebSocket: ReturnType<typeof createNodeWebSocket>['injectWebSocket'] } {
  const { upgradeWebSocket, injectWebSocket } = createNodeWebSocket({ app });

  app.get('/rooms/:id/ws', upgradeWebSocket((c) => {
    const room_id: string = c.req.param('id') ?? '';
    return {
      async onOpen(_evt, ws) {
        // Auth — Bearer in Authorization or token query param (browsers can't
        // set Authorization on WS upgrades, so we accept ?token=… too).
        const auth = String(c.req.header('Authorization') ?? '');
        const tokenFromQuery = String(c.req.query('token') ?? '');
        const token: string = auth.startsWith('Bearer ')
          ? auth.slice(7)
          : tokenFromQuery;
        if (!token) {
          send(ws, { type: 'error', code: 'missing_bearer' });
          ws.close(1008, 'missing_bearer');
          return;
        }
        const session = await verifySession(token);
        if (!session) {
          send(ws, { type: 'error', code: 'invalid_session' });
          ws.close(1008, 'invalid_session');
          return;
        }
        const room = getRoom(room_id);
        if (!room) {
          send(ws, { type: 'error', code: 'room_not_found' });
          ws.close(1008, 'room_not_found');
          return;
        }
        // Private rooms require seat or cabinet to join the WS.
        if (room.mode === 'private' && session.tier < TIERS.seat) {
          send(ws, { type: 'error', code: 'private_room_requires_seat' });
          ws.close(1008, 'private_room');
          return;
        }
        const client: WSClient = { ws, session, room_id };
        let set = ROOM_CLIENTS.get(room_id);
        if (!set) { set = new Set(); ROOM_CLIENTS.set(room_id, set); }
        set.add(client);
        (ws as unknown as { _client: WSClient })._client = client;

        send(ws, {
          type: 'hello',
          room_id,
          your_tier: session.tier,
          your_address: session.address,
          seats: room.seats.map(s => ({ role: s.role, weight: s.weight, veto: s.veto })),
          mode: room.mode,
          protected: room.protected,
        });
      },

      async onMessage(evt, ws) {
        const client = (ws as unknown as { _client?: WSClient })._client;
        if (!client) return;
        let frame: any;
        try { frame = JSON.parse(String(evt.data)); } catch {
          send(ws, { type: 'error', code: 'invalid_json' }); return;
        }
        const t = frame?.type;

        if (t === 'ping') { send(ws, { type: 'pong', ts: Date.now() }); return; }

        if (t === 'auth.refresh') {
          const sess = await verifySession(String(frame?.token ?? ''));
          if (!sess) { send(ws, { type: 'error', code: 'refresh_failed' }); return; }
          client.session = sess;
          send(ws, { type: 'auth.ok', tier: sess.tier, exp: sess.exp });
          return;
        }

        if (t === 'convene') {
          const room = getRoom(client.room_id);
          if (!room) { send(ws, { type: 'error', code: 'room_gone' }); return; }
          if (room.mode === 'private' && client.session.tier < TIERS.seat) {
            send(ws, { type: 'error', code: 'tier_insufficient' }); return;
          }
          if (room.mode !== 'private' && client.session.tier < TIERS.person) {
            send(ws, { type: 'error', code: 'tier_insufficient' }); return;
          }
          const directive = String(frame?.directive ?? '').trim();
          if (!directive) { send(ws, { type: 'error', code: 'directive_required' }); return; }

          const session: Session = {
            session_id: newSessionId(),
            room_id: client.room_id,
            directive: directive.slice(0, 2000),
            importance: frame?.importance ?? 'standard',
            initiated_by: client.session.address,
            votes: [],
            verdict: null,
            started_at: Math.floor(Date.now() / 1000),
            finished_at: null,
            context: typeof frame?.context === 'string' ? frame.context.slice(0, 8000) : undefined,
          };
          broadcast(client.room_id, { type: 'vote.start', session_id: session.session_id, directive: session.directive });

          // Run each voting seat in parallel; broadcast deltas as they arrive.
          const votingSeats = room.seats.filter(s => s.weight > 0);
          const votes: Vote[] = await Promise.all(votingSeats.map(seat =>
            castVote(seat, {
              directive: session.directive,
              context: session.context,
              onDelta: (chunk) => broadcast(client.room_id, {
                type: 'vote.delta', session_id: session.session_id, seat: seat.role, content_delta: chunk,
              }),
            }).then(v => {
              broadcast(client.room_id, {
                type: 'vote.complete', session_id: session.session_id, seat: v.seat,
                vote: v.value, reasoning: v.reasoning,
                provider: v.provider, model: v.model, latency_ms: v.latency_ms,
              });
              return v;
            })
          ));

          session.votes = votes;
          session.verdict = aggregateVotes(room.seats, votes);
          session.finished_at = Math.floor(Date.now() / 1000);
          persistSession(session);

          broadcast(client.room_id, {
            type: 'verdict.final',
            session_id: session.session_id,
            verdict: session.verdict,
            votes: votes.map(v => ({ seat: v.seat, value: v.value, weight: v.weight, veto: v.veto })),
          });
          return;
        }

        if (t === 'amendment.propose') {
          if (client.session.tier < TIERS.seat) {
            send(ws, { type: 'error', code: 'tier_insufficient_for_amendment' }); return;
          }
          broadcast(client.room_id, {
            type: 'amendment.proposed',
            from: client.session.address,
            payload: frame?.payload ?? null,
            ts: Date.now(),
          });
          return;
        }

        if (t === 'question.ask') {
          if (client.session.tier < TIERS.person) {
            send(ws, { type: 'error', code: 'tier_insufficient_for_question' }); return;
          }
          broadcast(client.room_id, {
            type: 'question.broadcast',
            from: client.session.address,
            to_seat: typeof frame?.to_seat === 'string' ? frame.to_seat : null,
            text: String(frame?.text ?? '').slice(0, 1000),
            ts: Date.now(),
          });
          return;
        }

        send(ws, { type: 'error', code: 'unknown_frame_type', got: t });
      },

      onClose(_evt, ws) {
        const client = (ws as unknown as { _client?: WSClient })._client;
        if (!client) return;
        ROOM_CLIENTS.get(client.room_id)?.delete(client);
        log('debug', 'ws', 'client closed', { room_id: client.room_id, address: client.session.address });
      },
    };
  }));

  return { injectWebSocket };
}
