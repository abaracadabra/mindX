// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/ui/manage — Phase 3 manage panels.
//
// Seven Lit Web Components that bring bankoneth UI to ens-app-v3 parity:
//
//   <b-records-editor>     edit records post-mint (multicall-batched)
//   <b-renewal>            extend expiry (subname or .eth 2LD mode)
//   <b-transfer>           NameWrapper safeTransferFrom + UR resolve
//   <b-primary-name>       ReverseRegistrar.setName
//   <b-my-names>           inventory dashboard
//   <b-permissions-panel>  fuse burn UX with IRREVERSIBLE confirmations
//   <b-siwe-signin>        EIP-4361 sign-in + pluggable gate predicate

export { BankonethRecordsEditor }    from "./b-records-editor";
export { BankonethRenewal }          from "./b-renewal";
export { BankonethTransfer }         from "./b-transfer";
export { BankonethPrimaryName }      from "./b-primary-name";
export { BankonethMyNames }          from "./b-my-names";
export { BankonethPermissionsPanel } from "./b-permissions-panel";
export { BankonethSiweSignin }       from "./b-siwe-signin";
export {
  BankonethContractNameStatus,
  type ContractRow,
} from "./b-contract-name-status";
