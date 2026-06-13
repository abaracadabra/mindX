// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// @openagents/contracts — public API.
// Contract: docs/services/contract_interaction_as_a_service.md

export {
  contractsFor,
  type ContractsForOptions,
  type ContractsRegistry,
  type ContractHandle,
} from "./registry.js";

export {
  parseDeploymentRecord,
  loadDeploymentRecord,
  addressOf,
  type DeploymentRecord,
  type DeployedContract,
} from "./deployments.js";

export {
  loadAbi,
  type AbiLoaderConfig,
} from "./abi-loader.js";
