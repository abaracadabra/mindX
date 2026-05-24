// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

/// @title IBankonExtensions
/// @notice Interface bundle for the new bankoneth contracts that live alongside
///         the four re-homed BANKON v1 core contracts: Resolver, InftAdapter,
///         X402Attestor, AgenticPlaceHook, EthRegistrar, DomainHosting.

/// @notice BankonSubnameResolver — PublicResolver subclass with the BANKON
///         text-record namespace and the iNFT-Mode-A TBA override on `addr(node)`.
interface IBankonSubnameResolver {
    function addr(bytes32 node) external view returns (address);
    function text(bytes32 node, string calldata key) external view returns (string memory);
    function setAddr(bytes32 node, address a) external;
    function setText(bytes32 node, string calldata key, string calldata value) external;
    function setINFTBinding(bytes32 node, address tbaAddress, uint256 zeroGTokenId) external;
}

/// @notice BankonInftAdapter — Mode A glue. Receives the ERC-1155 subname from
///         NameWrapper, emits a RequestINFTMint event that an off-chain 0G-side
///         worker picks up and acts on, maintains a registry mapping
///         (ensLabelhash → 0G iNFT tokenId) populated by operator-attested
///         WireCrossChain.registerINFTTokenId() calls.
interface IBankonInftAdapter {
    event RequestINFTMint(
        bytes32 indexed parentNode,
        bytes32 indexed labelhash,
        address indexed claimant,
        uint256 erc1155TokenId,
        string  metadataURI
    );

    event INFTBound(
        bytes32 indexed labelhash,
        uint256 indexed zeroGTokenId,
        address indexed tbaAddress
    );

    function requestMint(
        bytes32 parentNode,
        bytes32 labelhash,
        address claimant,
        uint256 erc1155TokenId,
        string calldata metadataURI
    ) external;

    function registerZeroGTokenId(bytes32 labelhash, uint256 zeroGTokenId) external;

    function zeroGTokenIdOf(bytes32 labelhash) external view returns (uint256);
    function tbaAddressOf(bytes32 labelhash) external view returns (address);
}

/// @notice BankonX402Attestor — EIP-712 facilitator-key registry + nonce replay
///         guard for x402 receipts from the GoPlausible Algorand facilitator.
interface IBankonX402Attestor {
    struct X402Receipt {
        bytes32 receiptHash;       // hash returned by the Algorand facilitator
        address claimant;          // EVM-side beneficiary
        uint256 usd6;              // USDC base units (6 decimals)
        uint64  nonce;             // monotonic per-facilitator
        uint64  expiresAt;         // unix seconds
        bytes   signature;         // EIP-712 sig by the facilitator key
    }

    event FacilitatorRegistered(address indexed facilitator, bool active);
    event ReceiptConsumed(bytes32 indexed receiptHash, address indexed claimant, uint64 nonce);

    function setFacilitator(address facilitator, bool active) external;
    function verify(X402Receipt calldata r) external returns (bool);
    function isReceiptSpent(bytes32 receiptHash) external view returns (bool);
}

/// @notice BankonAgenticPlaceHook — optional per-mint listing emitter. Off-chain
///         indexer on agenticplace.pythai.net consumes the event and creates the
///         marketplace card.
interface IBankonAgenticPlaceHook {
    event AgenticPlaceListing(
        bytes32 indexed parentNode,
        bytes32 indexed labelhash,
        address indexed tbaAddress,
        uint256 zeroGTokenId,
        string  metadataURI,
        address author
    );

    function list(
        bytes32 parentNode,
        bytes32 labelhash,
        address tbaAddress,
        uint256 zeroGTokenId,
        string calldata metadataURI,
        address author
    ) external;

    function setWebhookURL(string calldata url) external;
    function webhookURL() external view returns (string memory);
}

/// @notice BankonEthRegistrar — Flow B. Wraps the canonical ENS
///         ETHRegistrarController commit-reveal flow so customers buy
///         `newdomain.eth` end-to-end through bankoneth.
interface IBankonEthRegistrar {
    struct CommitParams {
        string  label;        // "newdomain" — without the ".eth"
        address owner;
        uint256 durationYears;
        bytes32 secret;       // server-managed deterministic salt
        address resolver;
        bool    reverseRecord;
        uint16  ownerControlledFuses;
    }

    event Committed(bytes32 indexed commitment, address indexed payer, address indexed owner);
    event Registered(string label, address indexed owner, uint256 cost, address asset);

    function commit(CommitParams calldata p) external returns (bytes32 commitment);
    function reveal(CommitParams calldata p, bytes calldata payment) external payable;
    function quote(string calldata label, uint256 durationYears) external view returns (uint256 wei_, uint256 usd6);
}

/// @notice BankonDomainHosting — Flow C. Subdomain-minting-as-a-service. External
///         `.eth` holders enroll their domain (wrapping if needed, burning
///         CANNOT_UNWRAP for the parent-lock requirement) and bankoneth issues
///         subnames under their parent.
interface IBankonDomainHosting {
    struct EnrolledParent {
        address parentOwner;
        uint256 pricePerLabel6;   // USDC base units
        uint16  childFuses;        // applied to every issued subname
        uint64  defaultExpiry;     // unix seconds for newly minted children
        uint16  ownerShareBps;     // basis points of revenue routed to parentOwner (10000 = 100%)
        bool    active;
    }

    event ParentEnrolled(bytes32 indexed parentNode, address indexed parentOwner, uint16 ownerShareBps);
    event SubnameIssued(bytes32 indexed parentNode, string label, address indexed owner);

    function enroll(
        bytes32 parentNode,
        uint256 pricePerLabel6,
        uint16  childFuses,
        uint64  defaultExpiry,
        uint16  ownerShareBps
    ) external;

    function disenroll(bytes32 parentNode) external;

    function issue(
        bytes32 parentNode,
        string calldata label,
        address owner,
        bytes calldata payment
    ) external payable returns (bytes32 subnameNode);

    function parentOf(bytes32 parentNode) external view returns (EnrolledParent memory);
}
