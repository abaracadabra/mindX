// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity ^0.8.24;

/**
 * DatoNamingRegistry — tiered, extensible permanence naming for datos.
 *
 * Names are `<handle>.<tier>.<root>` where the middle label is the permanence
 * tier (immortal | immutable | mutable) — the name *declares* its permanence.
 * Roots are extensible: "blockchain" ships enabled and the DAIO owner can
 * `addRoot("eth")`, `addRoot("ar")`, … so the namespace grows without redeploy.
 *
 * ENS-handler shape (cf. daio/contracts/ens/v1/BankonSubnameRegistrar.sol): each
 * name resolves to a controller + a permanence proof URI (Arweave tx / anchor) +
 * the owning DatoCore. cypherpunk2048: inline owner (DAIO), no proxy, zero imports.
 */
contract DatoNamingRegistry {
    struct NameRecord {
        address controller;     // who controls the name (data controller wallet)
        string  proofURI;       // arweave://<txid> | anchor:<sha256> | ""
        address datoCore;       // the DatoCore that owns this name (optional)
        uint8   tier;           // 0 immortal | 1 immutable | 2 mutable
        bool    exists;
        bool    soulbound;      // if true, controller cannot be reassigned
    }

    address public owner;       // the owning DAIO
    mapping(bytes32 => bool) public rootEnabled;     // keccak(root) => enabled
    string[] public roots;
    mapping(bytes32 => NameRecord) private _names;   // namehash => record

    event RootAdded(string root);
    event NameRegistered(bytes32 indexed node, string name, address controller, uint8 tier, string proofURI);
    event NameUpdated(bytes32 indexed node, address controller, string proofURI);
    event OwnershipTransferred(address indexed from, address indexed to);

    error NotOwner();
    error UnknownRoot();
    error BadTier();
    error NameTaken();
    error Soulbound();
    error NotController();
    error ZeroAddress();

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }

    constructor(address daioOwner) {
        if (daioOwner == address(0)) revert ZeroAddress();
        owner = daioOwner;
        _addRoot("blockchain");
        emit OwnershipTransferred(address(0), daioOwner);
    }

    function addRoot(string calldata root) external onlyOwner { _addRoot(root); }

    function _addRoot(string memory root) internal {
        bytes32 k = keccak256(bytes(root));
        if (!rootEnabled[k]) { rootEnabled[k] = true; roots.push(root); emit RootAdded(root); }
    }

    function rootsCount() external view returns (uint256) { return roots.length; }

    /// @notice ENS-style namehash over the three labels handle.tier.root (sha-of-keccak chain).
    function namehash(string memory handle, string memory tier, string memory root) public pure returns (bytes32 node) {
        node = bytes32(0);
        node = keccak256(abi.encodePacked(node, keccak256(bytes(root))));
        node = keccak256(abi.encodePacked(node, keccak256(bytes(tier))));
        node = keccak256(abi.encodePacked(node, keccak256(bytes(handle))));
    }

    function _tierCode(string memory tier) internal pure returns (uint8) {
        bytes32 t = keccak256(bytes(tier));
        if (t == keccak256("immortal"))  return 0;
        if (t == keccak256("immutable")) return 1;
        if (t == keccak256("mutable"))   return 2;
        revert BadTier();
    }

    /// @notice Register `<handle>.<tier>.<root>`. Owner-gated (the DAIO/dato issues names).
    function registerName(
        string calldata handle,
        string calldata tier,
        string calldata root,
        address controller,
        string calldata proofURI,
        address datoCore,
        bool soulbound
    ) external onlyOwner returns (bytes32 node) {
        if (controller == address(0)) revert ZeroAddress();
        if (!rootEnabled[keccak256(bytes(root))]) revert UnknownRoot();
        uint8 tierCode = _tierCode(tier);
        node = namehash(handle, tier, root);
        if (_names[node].exists) revert NameTaken();
        _names[node] = NameRecord({
            controller: controller, proofURI: proofURI, datoCore: datoCore,
            tier: tierCode, exists: true, soulbound: soulbound
        });
        emit NameRegistered(node, string(abi.encodePacked(handle, ".", tier, ".", root)), controller, tierCode, proofURI);
    }

    /// @notice Update the proof URI (e.g. a fresh Arweave tx for a mutable record).
    /// Controller-gated; soulbound names keep their controller fixed.
    function updateProof(bytes32 node, string calldata proofURI) external {
        NameRecord storage r = _names[node];
        if (!r.exists) revert UnknownRoot();
        if (msg.sender != r.controller && msg.sender != owner) revert NotController();
        r.proofURI = proofURI;
        emit NameUpdated(node, r.controller, proofURI);
    }

    function reassign(bytes32 node, address newController) external {
        NameRecord storage r = _names[node];
        if (!r.exists) revert UnknownRoot();
        if (msg.sender != r.controller && msg.sender != owner) revert NotController();
        if (r.soulbound) revert Soulbound();
        if (newController == address(0)) revert ZeroAddress();
        r.controller = newController;
        emit NameUpdated(node, newController, r.proofURI);
    }

    function resolve(string calldata handle, string calldata tier, string calldata root)
        external view returns (NameRecord memory)
    {
        return _names[namehash(handle, tier, root)];
    }

    function resolveNode(bytes32 node) external view returns (NameRecord memory) {
        return _names[node];
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
