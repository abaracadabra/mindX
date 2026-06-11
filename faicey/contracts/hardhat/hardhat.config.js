// hardhat.config.js — Hardhat deployment template for SoundWave.
//
// Convention: Foundry + anvil are PREFERRED for all local testing (forge test; see
// ../test and ../script/DeploySoundWave.s.sol). Hardhat is provided here as the
// deployment template — it compiles the same ../src and runs scripts/deploy.js, which
// auto-writes the deployed address into ../../dapp/deployments/<chainId>.json and runs
// export-abis so the UI never hard-codes an address.
//
//   cd faicey/contracts/hardhat
//   npm i -D hardhat @nomicfoundation/hardhat-toolbox
//   npx hardhat run scripts/deploy.js --network localhost   # against `anvil`
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true },
  },
  paths: {
    sources: "../src",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    // Foundry's anvil — the preferred local chain.
    localhost: { url: "http://127.0.0.1:8545", chainId: 31337 },
    // Fill from env for testnets/mainnet.
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: process.env.DEPLOYER_PK ? [process.env.DEPLOYER_PK] : [],
    },
  },
};
