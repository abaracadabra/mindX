/**
 * Minimal ABI for DAIOBridge / DAIO governance voting (daio.pythai.net)
 * Compatible with ethers.js and web3.js.
 */
const DAIO_BRIDGE_ABI = [
  {
    inputs: [{ name: "proposalId", type: "uint256" }],
    name: "getProposal",
    outputs: [
      { name: "proposer", type: "address" },
      { name: "title", type: "string" },
      { name: "status", type: "uint8" },
      { name: "forVotes", type: "uint256" },
      { name: "againstVotes", type: "uint256" }
    ],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [],
    name: "proposalCount",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function"
  },
  {
    inputs: [
      { name: "proposalId", type: "uint256" },
      { name: "support", type: "bool" }
    ],
    name: "vote",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [
      { name: "title", type: "string" },
      { name: "description", type: "string" },
      { name: "proposalType", type: "uint8" },
      { name: "projectId", type: "string" },
      { name: "target", type: "address" },
      { name: "executionData", type: "bytes" }
    ],
    name: "createProposal",
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ name: "proposalId", type: "uint256" }],
    name: "checkProposalStatus",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  },
  {
    inputs: [{ name: "proposalId", type: "uint256" }],
    name: "executeProposal",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  }
];

// ProposalStatus enum (for display)
const PROPOSAL_STATUS = [
  "Pending", "Active", "Succeeded", "Defeated", "Executed", "Cancelled"
];

if (typeof module !== "undefined" && module.exports) {
  module.exports = { DAIO_BRIDGE_ABI, PROPOSAL_STATUS };
}
