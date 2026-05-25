/**
 * Room CRUD routes.
 *
 *   GET    /rooms                          list rooms (filtered by mode)
 *   GET    /rooms/:id                      one room
 *   POST   /rooms                          create — tier ≥ person
 *   POST   /rooms/:id/invite               issue invite — tier ≥ cabinet
 *   POST   /rooms/:id/accept-invite        accept invite — tier ≥ invitee
 *   DELETE /rooms/:id                      delete — tier ≥ cabinet (refused for protected rooms)
 */

import { Hono } from 'hono';
import { isAddress } from 'viem';
import { requireSession, requireTier, TIERS } from '../auth/middleware.js';
import { getRoom, listRooms, createRoom, deleteRoom, inviteToRoom, acceptInvite } from './store.js';
import { publicSeats } from './types.js';
import type { RoomMode, CreateRoomInput } from './types.js';

export const roomsRoutes = new Hono();

roomsRoutes.get('/', (c) => {
  const modeStr = c.req.query('mode') as RoomMode | undefined;
  const rooms = listRooms(modeStr ? { mode: modeStr } : {});
  // Public listing shows only public_invite + public_open rooms unless
  // the caller is authenticated; private rooms are hidden from anonymous.
  const auth = c.req.header('Authorization');
  const visible = auth ? rooms : rooms.filter(r => r.mode !== 'private');
  return c.json({
    rooms: visible.map(r => ({
      room_id: r.room_id,
      name: r.name,
      mode: r.mode,
      protected: r.protected,
      seat_count: r.seats.length,
      created_at: r.created_at,
    })),
    count: visible.length,
  });
});

roomsRoutes.get('/:id', (c) => {
  const id = c.req.param('id');
  const r = getRoom(id);
  if (!r) return c.json({ error: 'not_found' }, 404);
  return c.json({
    room_id: r.room_id,
    name: r.name,
    description: r.description,
    mode: r.mode,
    seats: publicSeats(r.seats),
    cabinet_size: r.cabinet.length,
    invited_count: Object.keys(r.invited).length,
    protected: r.protected,
    daio_sanctioned: r.daio_sanctioned,
    created_at: r.created_at,
    updated_at: r.updated_at,
  });
});

roomsRoutes.post('/', requireTier(TIERS.person), async (c) => {
  const session = c.get('session');
  const body = await c.req.json().catch(() => ({}));
  const input: CreateRoomInput = {
    name: String(body.name ?? '').trim(),
    description: body.description ? String(body.description).slice(0, 500) : undefined,
    mode: (body.mode === 'private' || body.mode === 'public_invite' || body.mode === 'public_open')
      ? body.mode
      : 'public_invite',
    seats: Array.isArray(body.seats) ? body.seats : [],
    cabinet: Array.isArray(body.cabinet)
      ? body.cabinet.filter((a: unknown) => typeof a === 'string' && isAddress(a as `0x${string}`))
                    .map((a: string) => a.toLowerCase() as `0x${string}`)
      : undefined,
  };
  if (!input.name) return c.json({ error: 'name_required' }, 400);
  const r = createRoom(session.address, input);
  return c.json({ room_id: r.room_id, name: r.name, mode: r.mode, created_at: r.created_at }, 201);
});

roomsRoutes.post('/:id/invite', requireTier(TIERS.cabinet), async (c) => {
  const id = c.req.param('id');
  const r = getRoom(id);
  if (!r) return c.json({ error: 'not_found' }, 404);
  const body = await c.req.json().catch(() => ({}));
  const wallet = String(body.wallet ?? '').toLowerCase();
  if (!isAddress(wallet as `0x${string}`)) {
    return c.json({ error: 'invalid_wallet' }, 400);
  }
  const token = inviteToRoom(id, wallet as `0x${string}`);
  return c.json({ room_id: id, invitee: wallet, invite_token: token });
});

roomsRoutes.post('/:id/accept-invite', requireSession(), async (c) => {
  const session = c.get('session');
  const id = c.req.param('id');
  const body = await c.req.json().catch(() => ({}));
  const token = String(body.invite_token ?? '');
  const ok = acceptInvite(id, session.address, token);
  if (!ok) return c.json({ error: 'invite_invalid_or_expired' }, 401);
  return c.json({ room_id: id, accepted: true });
});

roomsRoutes.delete('/:id', requireTier(TIERS.cabinet), (c) => {
  const id = c.req.param('id');
  const ok = deleteRoom(id);
  if (!ok) return c.json({ error: 'not_found_or_protected' }, 400);
  return c.json({ room_id: id, deleted: true });
});
