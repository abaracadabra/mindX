/**
 * Minimal ABI for LiquidityLocker (S.M.A.I.R.T LP time-lock).
 * Compatible with ethers.js v5.
 */
const LiquidityLockerABI = [
  {
    inputs: [{ name: "lpToken", type: "address" }, { name: "beneficiary", type: "address" }],
    name: "getLockDetails",
    outputs: [
      { name: "amount", type: "uint256" },
      { name: "releaseTime", type: "uint256" },
      { name: "isLocked", type: "bool" }
    ],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [{ name: "lpToken", type: "address" }],
    name: "withdrawLP",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  }
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { LiquidityLockerABI };
}
