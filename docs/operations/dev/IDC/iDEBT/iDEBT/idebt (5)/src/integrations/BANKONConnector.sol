// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";
import { ECDSA }         from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

import { IBANKON } from "../interfaces/IBANKON.sol";

/// @title BANKONConnector
/// @notice Links Algorand AlgoIDNFT sovereign identity roots to EVM wallets.
/// @dev    The off-chain BANKON service (bankon.pythai.net) co-signs the
///         binding to prevent squatting. Signature scheme: EIP-191 personal
///         sign of the tuple (algoIdRoot, evmWallet, chainId).
contract BANKONConnector is IBANKON, AccessControl {
    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");

    address public bankonSigner; // BANKON service key

    mapping(address => SovereignId) private _bound;
    mapping(bytes32 => address)     public  ownerOfRoot;

    constructor(address admin, address bankonSigner_) {
        require(bankonSigner_ != address(0), "zero signer");
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNOR_ROLE, admin);
        bankonSigner = bankonSigner_;
    }

    // -------------------------------------------------------------- //
    //                              ADMIN                             //
    // -------------------------------------------------------------- //

    function rotateSigner(address next) external onlyRole(GOVERNOR_ROLE) {
        require(next != address(0), "zero");
        bankonSigner = next;
    }

    // -------------------------------------------------------------- //
    //                            BINDING                             //
    // -------------------------------------------------------------- //

    /// @param algoIdRoot  commitment root from AlgoIDNFT
    /// @param algoSig     BANKON signer's ECDSA signature over the EIP-191 digest
    function bind(bytes32 algoIdRoot, bytes calldata algoSig) external {
        if (ownerOfRoot[algoIdRoot] != address(0)) revert InvalidBinding();
        if (_bound[msg.sender].active)             revert InvalidBinding();

        bytes32 digest = ECDSA.toEthSignedMessageHash(
            keccak256(abi.encode(algoIdRoot, msg.sender, block.chainid))
        );
        address signer = ECDSA.recover(digest, algoSig);
        if (signer != bankonSigner) revert InvalidBinding();

        _bound[msg.sender] = SovereignId({
            algoIdRoot:  algoIdRoot,
            evmBinding:  msg.sender,
            boundAt:     uint64(block.timestamp),
            active:      true
        });
        ownerOfRoot[algoIdRoot] = msg.sender;
        emit SovereignIdBound(algoIdRoot, msg.sender);
    }

    function revoke() external {
        SovereignId storage s = _bound[msg.sender];
        if (!s.active) revert NotBound();
        emit SovereignIdRevoked(s.algoIdRoot);
        ownerOfRoot[s.algoIdRoot] = address(0);
        delete _bound[msg.sender];
    }

    // -------------------------------------------------------------- //
    //                              VIEWS                             //
    // -------------------------------------------------------------- //

    function sovereignOf(address account) external view returns (SovereignId memory) {
        return _bound[account];
    }

    function isBound(address account) external view returns (bool) {
        return _bound[account].active;
    }
}
