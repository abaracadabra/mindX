/**
 * Service client — talks to the three Node services through Apache reverse
 * proxy paths on whichever host serves this UI.
 *
 * Storage:
 *   - boardroomToken     in localStorage  ('boardroom_jwt')
 *   - dojoToken          in localStorage  ('dojo_jwt')
 *   - warcouncilToken    in localStorage  ('warcouncil_jwt')
 *
 * Each token is independently scoped — being logged into the boardroom
 * doesn't authorize you on the dojo or war-council.
 */

const PATHS = {
  boardroom:  '/boardroom-svc',
  dojo:       '/dojo-svc',
  warcouncil: '/warcouncil-svc',
} as const;
type Service = keyof typeof PATHS;

const TOKEN_KEY: Record<Service, string> = {
  boardroom:  'boardroom_jwt',
  dojo:       'dojo_jwt',
  warcouncil: 'warcouncil_jwt',
};

export function getToken(svc: Service): string | null {
  return localStorage.getItem(TOKEN_KEY[svc]);
}
export function setToken(svc: Service, token: string): void {
  localStorage.setItem(TOKEN_KEY[svc], token);
}
export function clearToken(svc: Service): void {
  localStorage.removeItem(TOKEN_KEY[svc]);
}

async function request(svc: Service, path: string, opts: RequestInit = {}): Promise<Response> {
  const headers = new Headers(opts.headers ?? {});
  const tok = getToken(svc);
  if (tok && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${tok}`);
  if (opts.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  return fetch(`${PATHS[svc]}${path}`, { ...opts, headers });
}

export async function getJson<T>(svc: Service, path: string): Promise<T> {
  const r = await request(svc, path);
  if (!r.ok) throw new Error(`${svc} ${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export async function postJson<T>(svc: Service, path: string, body: unknown): Promise<T> {
  const r = await request(svc, path, { method: 'POST', body: JSON.stringify(body) });
  if (!r.ok) {
    let detail: string;
    try { detail = JSON.stringify(await r.json()); } catch { detail = await r.text(); }
    throw new Error(`${svc} ${path}: ${r.status} — ${detail.slice(0, 200)}`);
  }
  return r.json() as Promise<T>;
}

// ── Auth handshake (called by the wallet-login flow in WalletLogin component)

export interface Challenge { challenge_id: string; message: string; exp: number; }
export interface VerifyResponse {
  session_token: string;
  address: string;
  tier: number;
  tier_name: string;
  scope: string;
  exp: number;
  resolved_via: string;
}

export async function authChallenge(svc: Service, wallet: string): Promise<Challenge> {
  const r = await fetch(`${PATHS[svc]}/auth/challenge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wallet, scope: `${svc}-service` }),
  });
  if (!r.ok) throw new Error(`challenge failed: ${r.status}`);
  return r.json();
}

export async function authVerify(svc: Service, challenge_id: string, signature: string): Promise<VerifyResponse> {
  const r = await fetch(`${PATHS[svc]}/auth/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ challenge_id, signature }),
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`verify failed: ${r.status} — ${txt.slice(0, 200)}`);
  }
  return r.json();
}

// ── Service-shape responses

export interface Room {
  room_id: string;
  name: string;
  mode: 'private' | 'public_invite' | 'public_open';
  protected: boolean;
  seat_count: number;
  created_at: number;
}

export interface RoomDetail extends Room {
  description?: string;
  seats: Array<{ address: string; role: string; weight: number; veto: boolean; personhood_required: boolean }>;
  cabinet_size: number;
  invited_count: number;
  daio_sanctioned: boolean;
  updated_at: number;
}

export interface Standing { agent_id: string; score: number; rank: string; }

export interface PersonhoodStatus { address: string; status: 'none' | 'pending' | 'granted'; tier_score: number; }

export const Api = {
  rooms:        (svc: Service)            => getJson<{ rooms: Room[]; count: number }>(svc, '/rooms'),
  room:         (svc: Service, id: string)=> getJson<RoomDetail>(svc, `/rooms/${id}`),
  standings:    ()                         => getJson<{ standings: Standing[]; count: number }>('dojo', '/standings'),
  personhood:   (addr: string)             => getJson<PersonhoodStatus>('dojo', `/personhood/${addr}`),
  declarePersonhood: ()                    => postJson('dojo', '/personhood/declare', {}),
  vouch:        (target: string)           => postJson('dojo', `/personhood/vouch/${target}`, {}),
};
export type { Service };
