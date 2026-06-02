// SPDX-License-Identifier: Apache-2.0
//
// ABIs for the bankoneth contracts. These are *minimal* — they declare only the
// surfaces @bankoneth/core needs to read and write. For full ABIs, run `forge
// inspect <contract> abi` against a built bankoneth checkout.
//
// Keeping these inline (rather than importing JSON build artifacts) means
// downstream consumers don't need to wire up Foundry to use the client — they
// just `pnpm add @bankoneth/core` and go.

export const BANKON_PRICE_ORACLE_ABI = [
  {
    type: "function",
    name: "priceUSD",
    stateMutability: "view",
    inputs: [
      { name: "label", type: "string" },
      { name: "durationYears", type: "uint256" },
    ],
    outputs: [{ name: "usd6", type: "uint256" }],
  },
] as const;

export const BANKON_SUBNAME_REGISTRAR_ABI = [
  {
    type: "function",
    name: "register",
    stateMutability: "payable",
    inputs: [
      { name: "label", type: "string" },
      { name: "owner", type: "address" },
      { name: "durationYears", type: "uint256" },
      { name: "paymentRail", type: "uint8" },
      { name: "payment", type: "bytes" },
    ],
    outputs: [],
  },
  {
    type: "event",
    name: "SubnameMinted",
    anonymous: false,
    inputs: [
      { name: "parentNode", type: "bytes32", indexed: true },
      { name: "labelhash", type: "bytes32", indexed: true },
      { name: "owner", type: "address", indexed: true },
      { name: "expiry", type: "uint64", indexed: false },
    ],
  },
] as const;

export const BANKON_ETH_REGISTRAR_ABI = [
  {
    type: "function",
    name: "quote",
    stateMutability: "view",
    inputs: [
      { name: "label", type: "string" },
      { name: "durationYears", type: "uint256" },
    ],
    outputs: [
      { name: "wei_", type: "uint256" },
      { name: "usd6", type: "uint256" },
    ],
  },
  {
    type: "function",
    name: "commit",
    stateMutability: "nonpayable",
    inputs: [
      {
        name: "p",
        type: "tuple",
        components: [
          { name: "label", type: "string" },
          { name: "owner", type: "address" },
          { name: "durationYears", type: "uint256" },
          { name: "secret", type: "bytes32" },
          { name: "resolver", type: "address" },
          { name: "reverseRecord", type: "bool" },
          { name: "ownerControlledFuses", type: "uint16" },
        ],
      },
    ],
    outputs: [{ name: "commitment", type: "bytes32" }],
  },
  {
    type: "function",
    name: "reveal",
    stateMutability: "payable",
    inputs: [
      {
        name: "p",
        type: "tuple",
        components: [
          { name: "label", type: "string" },
          { name: "owner", type: "address" },
          { name: "durationYears", type: "uint256" },
          { name: "secret", type: "bytes32" },
          { name: "resolver", type: "address" },
          { name: "reverseRecord", type: "bool" },
          { name: "ownerControlledFuses", type: "uint16" },
        ],
      },
      { name: "payment", type: "bytes" },
    ],
    outputs: [],
  },
] as const;

export const BANKON_DOMAIN_HOSTING_ABI = [
  {
    type: "function",
    name: "enroll",
    stateMutability: "nonpayable",
    inputs: [
      { name: "parentNode", type: "bytes32" },
      { name: "pricePerLabel6", type: "uint256" },
      { name: "priceEthWei", type: "uint256" },
      { name: "childFuses", type: "uint32" },
      { name: "defaultExpiry", type: "uint64" },
      { name: "ownerShareBps", type: "uint16" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "setPrices",
    stateMutability: "nonpayable",
    inputs: [
      { name: "parentNode", type: "bytes32" },
      { name: "pricePerLabel6", type: "uint256" },
      { name: "priceEthWei", type: "uint256" },
    ],
    outputs: [],
  },
  {
    type: "function",
    name: "issue",
    stateMutability: "payable",
    inputs: [
      { name: "parentNode", type: "bytes32" },
      { name: "label", type: "string" },
      { name: "owner", type: "address" },
      { name: "payment", type: "bytes" },
    ],
    outputs: [{ name: "subnameNode", type: "bytes32" }],
  },
  {
    type: "function",
    name: "parentOf",
    stateMutability: "view",
    inputs: [{ name: "parentNode", type: "bytes32" }],
    outputs: [
      {
        name: "p",
        type: "tuple",
        components: [
          { name: "parentOwner", type: "address" },
          { name: "pricePerLabel6", type: "uint256" },
          { name: "priceEthWei", type: "uint256" },
          { name: "childFuses", type: "uint32" },
          { name: "defaultExpiry", type: "uint64" },
          { name: "ownerShareBps", type: "uint16" },
          { name: "active", type: "bool" },
        ],
      },
    ],
  },
] as const;

export const BANKON_SUBNAME_RESOLVER_ABI = [
  {
    type: "function",
    name: "addr",
    stateMutability: "view",
    inputs: [{ name: "node", type: "bytes32" }],
    outputs: [{ name: "", type: "address" }],
  },
  {
    type: "function",
    name: "text",
    stateMutability: "view",
    inputs: [
      { name: "node", type: "bytes32" },
      { name: "key", type: "string" },
    ],
    outputs: [{ name: "", type: "string" }],
  },
] as const;

export const BANKON_INFT_ADAPTER_ABI = [
  {
    type: "function",
    name: "tbaAddressOf",
    stateMutability: "view",
    inputs: [{ name: "labelhash", type: "bytes32" }],
    outputs: [{ name: "", type: "address" }],
  },
  {
    type: "function",
    name: "zeroGTokenIdOf",
    stateMutability: "view",
    inputs: [{ name: "labelhash", type: "bytes32" }],
    outputs: [{ name: "", type: "uint256" }],
  },
] as const;

export const BANKON_X402_ATTESTOR_ABI = [
  {
    type: "function",
    name: "isReceiptSpent",
    stateMutability: "view",
    inputs: [{ name: "receiptHash", type: "bytes32" }],
    outputs: [{ name: "", type: "bool" }],
  },
] as const;
