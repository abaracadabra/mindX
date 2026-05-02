// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ITessera} from "./interfaces/ITessera.sol";

/// @title Tessera
/// @notice Minimal soulbound W3C DID credential anchor for Conclave membership.
///         An address has a valid credential if the admin issued one and it
///         was not revoked. Each credential carries a DID string and a 32-byte
///         Ed25519 transport pubkey (the AXL peer id).
///
///         For a livenet deploy this is the placeholder. Production would
///         use full BONAFIDE Tessera with on-chain attestations + cross-chain.
contract Tessera is ITessera {
    address public admin;
    mapping(address => bool) public _valid;
    mapping(address => string) public _did;
    mapping(address => bytes32) public _key;

    error NotAdmin();
    event TesseraIssued(address indexed holder, string did, bytes32 indexed pubkey);
    event TesseraRevoked(address indexed holder);
    event AdminTransferred(address indexed from, address indexed to);

    modifier onlyAdmin() {
        if (msg.sender != admin) revert NotAdmin();
        _;
    }

    constructor(address admin_) {
        admin = admin_;
    }

    function issue(address holder, string calldata did, bytes32 pubkey) external onlyAdmin {
        _valid[holder] = true;
        _did[holder] = did;
        _key[holder] = pubkey;
        emit TesseraIssued(holder, did, pubkey);
    }

    function revoke(address holder) external onlyAdmin {
        _valid[holder] = false;
        emit TesseraRevoked(holder);
    }

    function transferAdmin(address newAdmin) external onlyAdmin {
        emit AdminTransferred(admin, newAdmin);
        admin = newAdmin;
    }

    // ─── ITessera ──────────────────────────────────────────

    function hasValidCredential(address holder) external view returns (bool) {
        return _valid[holder];
    }

    function didOf(address holder) external view returns (string memory) {
        return _did[holder];
    }

    function transportKeyOf(address holder) external view returns (bytes32) {
        return _key[holder];
    }
}
