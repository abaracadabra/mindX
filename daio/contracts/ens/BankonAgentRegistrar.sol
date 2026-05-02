// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title BankonAgentRegistrar
 * @notice Custom ENS subname registrar issuing <agent_id>.bankon.eth
 *         soulbound subdomains for every mindX-spawned agent.
 *
 *         Pattern follows docs.ens.domains/wrapper/creating-subname-registrar:
 *         (1) Mint subname owned by THIS contract,
 *         (2) Set address + text records via Public Resolver,
 *         (3) Transfer to agent wallet with soulbound fuses burned.
 *
 *         Prerequisites (ops, one-time):
 *         - bankon.eth wrapped via NameWrapper
 *         - Parent fuses CANNOT_UNWRAP + PARENT_CANNOT_CONTROL burned
 *         - NameWrapper.setApprovalForAll(<this>, true) called by parent owner
 *
 *         Fuses on subnames: CANNOT_UNWRAP | CANNOT_TRANSFER | CANNOT_BURN_FUSES = 0x7.
 *         Soulbound by design — agent identities cannot be sold or transferred.
 */

interface INameWrapper {
    function setSubnodeRecord(
        bytes32 parentNode,
        string calldata label,
        address owner,
        address resolver,
        uint64 ttl,
        uint32 fuses,
        uint64 expiry
    ) external returns (bytes32);

    function setApprovalForAll(address operator, bool approved) external;
    function ownerOf(uint256 tokenId) external view returns (address);
}

interface IPublicResolver {
    function setAddr(bytes32 node, address a) external;
    function setText(bytes32 node, string calldata key, string calldata value) external;
}

contract BankonAgentRegistrar is ERC1155Holder, Ownable {
    INameWrapper public immutable nameWrapper;
    bytes32      public immutable parentNode;     // namehash("bankon.eth")
    address      public           resolver;       // Public Resolver

    /// CANNOT_UNWRAP (0x1) | CANNOT_BURN_FUSES (0x2) | CANNOT_TRANSFER (0x4)
    uint32 public constant SOULBOUND_FUSES = 0x7;
    /// PARENT_CANNOT_CONTROL must be burned on the parent before this contract
    /// can burn child fuses; we additionally need bit 0x10000 (CAN_EXTEND_EXPIRY)
    /// to set non-trivial expiries, but we leave that to ops.
    uint32 public constant DEFAULT_FUSES = SOULBOUND_FUSES;

    mapping(string => bool)    public agentRegistered; // by agent_id
    mapping(string => address) public agentWallet;     // agent_id => wallet
    uint256 public totalRegistered;

    event AgentRegistered(
        string  indexed agentIdHashIndex,    // keccak (because string can't be indexed)
        string          agentId,
        address indexed agentWalletAddr,
        bytes32         subnameNode
    );
    event ResolverUpdated(address indexed oldResolver, address indexed newResolver);

    constructor(
        address nameWrapper_,
        bytes32 parentNode_,
        address resolver_
    ) Ownable(msg.sender) {
        require(nameWrapper_ != address(0), "Bad wrapper");
        require(resolver_   != address(0), "Bad resolver");
        nameWrapper = INameWrapper(nameWrapper_);
        parentNode  = parentNode_;
        resolver    = resolver_;
    }

    function setResolver(address newResolver) external onlyOwner {
        require(newResolver != address(0), "Bad resolver");
        emit ResolverUpdated(resolver, newResolver);
        resolver = newResolver;
    }

    /// @notice Atomic three-step subname issuance.
    ///         Caller must be contract owner (mindX IDManagerAgent controller).
    ///         The subname is minted soulbound to `agentWalletAddr`.
    /// @param agentId          short label (e.g. "ceo-mastermind-prime")
    /// @param agentWalletAddr  agent's Ethereum wallet (becomes the resolved addr)
    /// @param personaUrl       URL pointing to the agent dashboard or persona file
    /// @param personaSummary   short human-readable description
    /// @param expiry           unix timestamp (must be <= parent expiry)
    function registerAgent(
        string calldata agentId,
        address agentWalletAddr,
        string calldata personaUrl,
        string calldata personaSummary,
        uint64 expiry
    ) external onlyOwner returns (bytes32 subnameNode) {
        require(bytes(agentId).length > 0 && bytes(agentId).length <= 64, "Bad agentId");
        require(agentWalletAddr != address(0), "Bad wallet");
        require(!agentRegistered[agentId], "Agent already registered");
        require(expiry > block.timestamp, "Expiry in past");

        // Step 1: mint subname owned by this contract (so we can call resolver).
        nameWrapper.setSubnodeRecord(
            parentNode,
            agentId,
            address(this),
            resolver,
            0,
            0,            // no fuses on this transient mint
            expiry
        );

        subnameNode = keccak256(
            abi.encodePacked(parentNode, keccak256(bytes(agentId)))
        );

        // Step 2: set address + text records while we own it.
        IPublicResolver r = IPublicResolver(resolver);
        r.setAddr(subnameNode, agentWalletAddr);
        if (bytes(personaUrl).length > 0) {
            r.setText(subnameNode, "url", personaUrl);
        }
        if (bytes(personaSummary).length > 0) {
            r.setText(subnameNode, "description", personaSummary);
        }
        r.setText(subnameNode, "mindx.agent_id", agentId);
        r.setText(subnameNode, "mindx.framework", "agnostic");

        // Step 3: transfer to agent wallet, burn soulbound fuses.
        nameWrapper.setSubnodeRecord(
            parentNode,
            agentId,
            agentWalletAddr,
            resolver,
            0,
            DEFAULT_FUSES,
            expiry
        );

        agentRegistered[agentId] = true;
        agentWallet[agentId]     = agentWalletAddr;
        unchecked { ++totalRegistered; }

        emit AgentRegistered(agentId, agentId, agentWalletAddr, subnameNode);
    }

    /// @notice View helper — returns subname namehash without registering.
    function previewSubnameNode(string calldata agentId) external view returns (bytes32) {
        return keccak256(abi.encodePacked(parentNode, keccak256(bytes(agentId))));
    }
}
