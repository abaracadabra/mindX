/**
 * Minimal ABI for BondingCurveFactory.launchPowerCurveNative (curve + optional presale).
 * Pass args as a single object; nested structs use objects with matching field names.
 */
const FactoryABI = [
  {
    inputs: [
      {
        name: "a",
        type: "tuple",
        components: [
          { name: "name", type: "string" },
          { name: "symbol", type: "string" },
          { name: "initialMintToOwner", type: "uint256" },
          { name: "kUD60x18", type: "uint256" },
          { name: "pUD60x18", type: "uint256" },
          { name: "protocolFeeBps", type: "uint16" },
          { name: "feeRecipient", type: "address" },
          { name: "enablePresale", type: "bool" },
          {
            name: "presaleOptions",
            type: "tuple",
            components: [
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
            ]
          },
          { name: "provisioner", type: "address" },
          {
            name: "liquidityTemplate",
            type: "tuple",
            components: [
              { name: "mode", type: "uint8" },
              { name: "enabled", type: "bool" },
              {
                name: "v2",
                type: "tuple",
                components: [
                  { name: "router", type: "address" },
                  { name: "weth", type: "address" },
                  { name: "enabled", type: "bool" }
                ]
              },
              {
                name: "v3",
                type: "tuple",
                components: [
                  { name: "positionManager", type: "address" },
                  { name: "weth", type: "address" },
                  { name: "fee", type: "uint24" },
                  { name: "tickLower", type: "int24" },
                  { name: "tickUpper", type: "int24" },
                  { name: "enabled", type: "bool" }
                ]
              },
              {
                name: "v4",
                type: "tuple",
                components: [
                  { name: "poolManager", type: "address" },
                  { name: "poolId", type: "bytes32" },
                  { name: "hook", type: "address" },
                  { name: "enabled", type: "bool" }
                ]
              },
              { name: "token", type: "address" },
              { name: "tokenAmount", type: "uint256" },
              { name: "nativeAmount", type: "uint256" },
              { name: "recipient", type: "address" },
              { name: "deadline", type: "uint256" }
            ]
          }
        ]
      }
    ],
    name: "launchPowerCurveNative",
    outputs: [
      { name: "tokenAddr", type: "address" },
      { name: "poolAddr", type: "address" },
      { name: "presaleAddr", type: "address" }
    ],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, name: "creator", type: "address" },
      { indexed: true, name: "token", type: "address" },
      { indexed: false, name: "pool", type: "address" }
    ],
    name: "LaunchedCurve",
    type: "event"
  }
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { FactoryABI };
}
