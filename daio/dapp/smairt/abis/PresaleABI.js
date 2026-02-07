/**
 * Minimal ABI for BondingCurvePresaleSMAIRT (S.M.A.I.R.T bonding presale).
 * Compatible with ethers.js v5.
 */
const PresaleABI = [
  { inputs: [], name: "state", outputs: [{ type: "uint8" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "nativeRaised", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [{ name: "", type: "address" }], name: "contributions", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "tokensBoughtForSale", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
  { inputs: [{ name: "", type: "address" }], name: "claimed", outputs: [{ type: "bool" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "curvePool", outputs: [{ type: "address" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "curveToken", outputs: [{ type: "address" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "locker", outputs: [{ type: "address" }], stateMutability: "view", type: "function" },
  { inputs: [], name: "lpTokenAddress", outputs: [{ type: "address" }], stateMutability: "view", type: "function" },
  {
    inputs: [],
    name: "options",
    outputs: [
      { name: "hardCapNative", type: "uint256" },
      { name: "softCapNative", type: "uint256" },
      { name: "maxContributionPerUserNative", type: "uint256" },
      { name: "minContributionPerUserNative", type: "uint256" },
      { name: "startTime", type: "uint256" },
      { name: "endTime", type: "uint256" },
      { name: "useLiquidityFreePresale", type: "bool" },
      { name: "useTeamAllocationFromFunds", type: "bool" },
      { name: "useTeamAllocationFromSupply", type: "bool" },
      { name: "teamAllocationFromFundsBps", type: "uint32" },
      { name: "teamAllocationFromSupplyBps", type: "uint32" },
      { name: "teamWallet", type: "address" },
      { name: "nativeForLiquidityBps", type: "uint32" },
      { name: "presaleNativeForMarketingBps", type: "uint32" },
      { name: "presaleNativeForDevBps", type: "uint32" },
      { name: "presaleNativeForDaoBps", type: "uint32" },
      { name: "presaleMarketingWallet", type: "address" },
      { name: "presaleDevWallet", type: "address" },
      { name: "presaleDaoWallet", type: "address" },
      { name: "liquidityLockDurationDays", type: "uint256" },
      { name: "liquidityBeneficiaryAddress", type: "address" },
      { name: "minTokensForLiquidity", type: "uint256" },
      { name: "minTokensForSale", type: "uint256" }
    ],
    stateMutability: "view",
    type: "function"
  },
  { stateMutability: "payable", type: "receive" },
  { inputs: [], name: "buy", outputs: [], stateMutability: "payable", type: "function" },
  { inputs: [], name: "claim", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "refund", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "activate", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "cancel", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "finalize", outputs: [], stateMutability: "nonpayable", type: "function" },
  { inputs: [], name: "owner", outputs: [{ type: "address" }], stateMutability: "view", type: "function" }
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { PresaleABI };
}
