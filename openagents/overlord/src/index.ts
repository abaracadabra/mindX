// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — public API.
//
// A portable overlord/overseer login + privilege model. Pure viem; consumes
// chronos promised time. Identity by signature; privilege by holdings whose
// blockchain tenure is chronos-verified; public vs privileged at the core.

export {
  type Role,
  type Privilege,
  type ChronosTime,
  type ChronosConsensus,
  type TokenStandard,
  type LevelBand,
  type HoldingConfig,
  type OverlordConfig,
  ROLE_ORDINAL,
  PRIVILEGED_ROLES,
  isPrivileged,
} from "./model.js";

export {
  buildChallenge,
  proveIdentity,
  addrEq,
  ERC1271_MAGIC,
  type ChallengeArgs,
  type IdentityProof,
  type IdentityMethod,
} from "./identity.js";

export {
  type Action,
  DESTRUCTIVE,
  can,
  capabilities,
} from "./capabilities.js";

export { readHolding, acquisitionTimestamp } from "./holdings.js";

export { promisedNow, tenureSec } from "./chronos.js";

export {
  resolvePrivilege,
  memberLevel,
  type ResolveInput,
} from "./resolver.js";

export {
  type Tier,
  ROLE_TO_TIER,
  TIER_NAME,
  roleToTier,
  privilegeToSession,
} from "./bridge.js";
