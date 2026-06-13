// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// @openagents/deploy — public API.
// Contract: docs/services/contract_deployment_as_a_service.md

export {
  CHAIN_DEPLOY_CONFIG,
  configFor,
  activeRpcUrl,
  type ChainDeployConfig,
} from "./chain-config.js";

export {
  preflight,
  allPassed,
  firstFailure,
  type PreflightCheck,
  type PreflightInput,
} from "./preflight.js";

export {
  intent,
  runScript,
  deploy as foundryDeploy,
  forgeAvailable,
  type DeployScriptOpts,
  type DeployScriptResult,
  type DeployIntent,
  type SingleDeployOpts,
  type SingleDeployResult,
} from "./foundry-driver.js";

export {
  deploy as algokitDeploy,
  algokitAvailable,
  type AlgokitDeployOpts,
  type AlgokitDeployResult,
} from "./algokit-driver.js";

export {
  appendDeployedContract,
} from "./record-writer.js";

// Convenience namespaced exports.
import * as foundryDriver from "./foundry-driver.js";
import * as algokitDriver from "./algokit-driver.js";
export { foundryDriver, algokitDriver };
