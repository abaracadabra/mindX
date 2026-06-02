// SPDX-License-Identifier: Apache-2.0
//
// Debounced subname-availability checks.
//
// The UI's in-tab availability pill (`b-availability-pill`) calls this on
// every keystroke. It debounces, dedupes, and exposes a cancel handle so
// stale results are dropped when the user keeps typing.

import { type Address, type Hex, type PublicClient, keccak256, encodePacked, labelhash, pad } from "viem";

/** Result of a single availability check. */
export interface AvailabilityResult {
  label: string;
  available: boolean;
  /** The owner of the subname if not available, else zero. */
  owner: Address;
  /** Bytes32 ENS namehash of the full subname under the given parent. */
  node: Hex;
}

/** Subset of the NameWrapper ABI we need to look up owners. */
const NAME_WRAPPER_ABI = [
  {
    type: "function",
    name: "ownerOf",
    stateMutability: "view",
    inputs: [{ name: "id", type: "uint256" }],
    outputs: [{ name: "", type: "address" }],
  },
] as const;

export interface CheckAvailabilityArgs {
  publicClient:    PublicClient;
  nameWrapperAddr: Address;
  /** Bytes32 namehash of the parent (e.g. namehash("bankon.eth")). */
  parentNode: Hex;
  /** Label without the parent suffix (e.g. "alice"). */
  label: string;
}

/**
 * Single availability check. Returns whether the label is unowned under the
 * parent. Throws on RPC error; the caller decides whether to surface a
 * transient error or treat as "unknown".
 */
export async function checkAvailability(args: CheckAvailabilityArgs): Promise<AvailabilityResult> {
  const lh = labelhash(args.label) as Hex;
  const node = keccak256(
    encodePacked(["bytes32", "bytes32"], [pad(args.parentNode, { size: 32 }), lh]),
  );
  const owner = await args.publicClient.readContract({
    address: args.nameWrapperAddr,
    abi: NAME_WRAPPER_ABI,
    functionName: "ownerOf",
    args: [BigInt(node)],
  }) as Address;
  return {
    label: args.label,
    node,
    owner,
    available: owner === "0x0000000000000000000000000000000000000000",
  };
}

export type AvailabilityCallback = (
  result: AvailabilityResult | null,
  err: Error | null,
) => void;

/** Handle returned by createDebouncedAvailabilityChecker — call `.dispose()` to free. */
export interface AvailabilityHandle {
  /** Push a new label to check. Cancels any in-flight stale request. */
  check(label: string): void;
  /** Cancel any pending or in-flight request without firing the callback. */
  cancel(): void;
  /** Tear down internal timers; safe to call multiple times. */
  dispose(): void;
}

/**
 * Build a debounced availability checker.
 *
 * - Debounces by `delayMs` between user keystrokes.
 * - Cancels in-flight RPCs (logically) when a newer label is pushed — the
 *   stale callback is suppressed.
 * - Empty label fires the callback with `null` (clears the pill).
 */
export function createDebouncedAvailabilityChecker(
  args: Omit<CheckAvailabilityArgs, "label">,
  cb: AvailabilityCallback,
  delayMs = 280,
): AvailabilityHandle {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let inflight = 0;
  let lastLabel = "";

  const handle: AvailabilityHandle = {
    check(label: string) {
      lastLabel = label.trim();
      if (timer) clearTimeout(timer);
      if (!lastLabel) {
        cb(null, null);
        return;
      }
      timer = setTimeout(async () => {
        inflight += 1;
        const myToken = inflight;
        try {
          const res = await checkAvailability({ ...args, label: lastLabel });
          if (myToken === inflight && res.label === lastLabel) cb(res, null);
        } catch (e) {
          if (myToken === inflight) cb(null, e as Error);
        }
      }, delayMs);
    },
    cancel() {
      if (timer) clearTimeout(timer);
      timer = null;
      inflight += 1; // invalidate any in-flight result
    },
    dispose() {
      handle.cancel();
    },
  };

  return handle;
}
