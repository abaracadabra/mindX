// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Subset of the ENS NameWrapper interface this registrar uses.
///         Reference: https://github.com/ensdomains/ens-contracts (NameWrapper.sol).
interface INameWrapper {
    function ownerOf(uint256 id) external view returns (address);
    function getData(uint256 id)
        external view
        returns (address owner, uint32 fuses, uint64 expiry);

    function setSubnodeOwner(
        bytes32 parentNode,
        string calldata label,
        address owner,
        uint32 fuses,
        uint64 expiry
    ) external returns (bytes32);

    function setSubnodeRecord(
        bytes32 parentNode,
        string calldata label,
        address owner,
        address resolver,
        uint64 ttl,
        uint32 fuses,
        uint64 expiry
    ) external returns (bytes32);

    function setChildFuses(
        bytes32 parentNode,
        bytes32 labelhash,
        uint32 fuses,
        uint64 expiry
    ) external;

    function setFuses(bytes32 node, uint16 ownerControlledFuses) external returns (uint32);
    function setResolver(bytes32 node, address resolver) external;
    function extendExpiry(bytes32 parentNode, bytes32 labelhash, uint64 expiry)
        external returns (uint64);

    function isWrapped(bytes32 node) external view returns (bool);
    function setApprovalForAll(address operator, bool approved) external;
    function approve(address to, uint256 tokenId) external;
}

/// @notice Subset of the ENS Public Resolver interface used by the registrar.
interface IPublicResolver {
    function setAddr(bytes32 node, address a) external;
    function setAddr(bytes32 node, uint256 coinType, bytes calldata a) external;
    function setText(bytes32 node, string calldata key, string calldata value) external;
    function setContenthash(bytes32 node, bytes calldata hash) external;
    function multicall(bytes[] calldata data) external returns (bytes[] memory);
}

/// @notice BankonPriceOracle interface — length-tier USD pricing in USDC base units (6 decimals).
interface IBankonPriceOracle {
    function priceUSD(string calldata label, uint256 durationYears)
        external view returns (uint256 usd6);
    function priceInToken(string calldata label, uint256 durationYears, address token)
        external view returns (uint256 amount);
}

/// @notice BankonReputationGate interface — agnostic eligibility surface.
///         Any reputation system (BONAFIDE, ERC-8004 attestation, custom) can
///         implement this to gate paid + free registration.
interface IBankonReputationGate {
    function isEligibleForFree(address agent) external view returns (bool);
    function isEligibleForRegistration(address agent) external view returns (bool);
    function bonafideScore(address agent) external view returns (uint256);
}

/// @notice ERC-8004-style identity registry. Hooked optionally by the registrar
///         to bundle agent identity mints with subname registrations.
interface IIdentityRegistry8004 {
    function register(address agentWallet, string calldata agentURI)
        external returns (uint256 agentId);
    function setMetadata(uint256 agentId, bytes32 key, bytes calldata value) external;
}

/// @notice BankonPaymentRouter interface — split + sweep of USDC/PYTHAI/ETH revenue.
interface IBankonPaymentRouter {
    function splitConfigured() external view returns (bool);
    function recordReceipt(bytes32 receiptHash, uint256 usd6, address asset) external;
    function distribute(address asset, uint256 amount) external;
}
