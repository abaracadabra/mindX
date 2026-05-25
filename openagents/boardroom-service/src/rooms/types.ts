/**
 * Room types — the shape of /rooms/{id} state.
 */

export type RoomMode = 'private' | 'public_invite' | 'public_open';

export interface RoomSeat {
  /** Wallet address that occupies this seat. */
  address: `0x${string}`;
  /** Seat name (e.g. 'coo_operations', 'ciso_security', 'sun_tzu'). */
  role: string;
  /** Vote weight (1.0 default, 1.2 for veto-class seats). */
  weight: number;
  /** Hard veto — if true, a 'reject' vote from this seat overrides majority. */
  veto: boolean;
  /** When true, only wallets with personhood may occupy this seat. */
  personhood_required: boolean;
  /** Optional: which inference provider this seat uses (for AI-backed seats). */
  inference_provider?: string;
  /** Optional: model identifier within the provider. */
  model?: string;
  /** Optional: persona file (markdown) injected as system prompt. */
  persona?: string;
}

export interface Room {
  room_id: string;
  /** Wallet that created the room. Has cabinet authority by default. */
  owner: `0x${string}`;
  /** Display name (for the UI). */
  name: string;
  /** Free-form description. */
  description?: string;
  mode: RoomMode;
  /** Seats — voters. Order matters for tie-breaking. */
  seats: RoomSeat[];
  /** Cabinet — wallets that can manage the room (issue invites, edit seats). */
  cabinet: `0x${string}`[];
  /** Pending invites — wallet → invite token. Cleared on accept. */
  invited: Record<string, string>;
  /** When true, this room is a special mindX-owned default that can't be deleted. */
  protected: boolean;
  /** True if DAIO has sanctioned cross-room joint action for this room. */
  daio_sanctioned: boolean;
  /** Unix seconds. */
  created_at: number;
  /** Unix seconds — last mutation. */
  updated_at: number;
}

export interface CreateRoomInput {
  name: string;
  description?: string;
  mode: RoomMode;
  seats?: RoomSeat[];
  cabinet?: `0x${string}`[];
}

/** Pretty-printed RoomSeat for /rooms responses (drops internals like inference_provider keys). */
export interface RoomSeatPublic {
  address: `0x${string}`;
  role: string;
  weight: number;
  veto: boolean;
  personhood_required: boolean;
}

export function publicSeats(seats: RoomSeat[]): RoomSeatPublic[] {
  return seats.map(s => ({
    address: s.address, role: s.role, weight: s.weight,
    veto: s.veto, personhood_required: s.personhood_required,
  }));
}
