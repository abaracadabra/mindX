// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl}    from "@openzeppelin/contracts/access/AccessControl.sol";
import {EIP712}           from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

import {IBankonEntitlement} from "./interfaces/IPay2Play.sol";
import {IProofOracle}       from "./interfaces/IProofOracle.sol";

interface IERC721Bal  { function balanceOf(address owner) external view returns (uint256); }
interface IERC1155Bal { function balanceOf(address owner, uint256 id) external view returns (uint256); }

/// @title  Pay2PlayGate — the gate to a service (API call / privileged room).
/// @author cypherpunk2048
/// @notice pay2play is the rail; this is the **gate**. A service here is a gated
///         resource — an API call or entry to a DeltaVerse-style privileged room.
///         Admission is granted by **signature**: the wallet signs a `Connect`
///         message, the gate verifies the signature (identity), checks the
///         on-chain entitlement (**persistence.state** from {BankonEntitlement}),
///         optionally a **proof.oracle** for "world" connection, and optionally a
///         **modular-NFT** gate (DeltaVerse expansion — github.com/deltav-deltaverse).
///         On success it emits `Admitted` — the seamless-connect signal an
///         off-chain **signature event-listener layer** watches to open the API /
///         room session. No tokens move here; the gate only reads state and admits.
///
///         The seam:
///           pay2play (pay → entitlement) → Pay2PlayGate (signature → admission)
///           → off-chain listener (Admitted event → opens the session).
contract Pay2PlayGate is AccessControl, EIP712 {
    bytes32 public constant ROOM_ADMIN_ROLE = keccak256("ROOM_ADMIN_ROLE");

    enum NftKind { None, ERC721, ERC1155 }

    /// A gated resource. `service` is the pay2play entitlement that must be held.
    /// `proofOracle` (optional) attests a world-condition. `nft*` (optional) gates
    /// on a modular NFT balance.
    struct Room {
        bytes32 service;     // required entitlement key (persistence.state)
        address proofOracle; // IProofOracle, or address(0) for none
        address nft;         // modular-NFT gate token, or address(0) for none
        NftKind nftKind;
        uint256 nftId;       // ERC-1155 id (ignored for ERC-721)
        uint256 minNft;      // minimum balance required (>=1 typical)
        bool    active;
        string  name;        // human label, e.g. "deltaverse.room.obsidian"
    }

    /// @notice Persistence.state the gate reads — the pay2play entitlement ledger.
    IBankonEntitlement public immutable entitlement;

    mapping(bytes32 => Room)    private  _rooms;
    mapping(address => uint256) public   nonces; // per-identity, for admitWithSig

    bytes32 private constant CONNECT_TYPEHASH =
        keccak256("Connect(bytes32 roomId,address user,uint256 nonce)");

    event RoomSet(bytes32 indexed roomId, bytes32 service, address proofOracle, address nft, uint8 nftKind, uint256 nftId, uint256 minNft, bool active, string name);
    event Admitted(bytes32 indexed roomId, address indexed user, address indexed by);

    error RoomInactive(bytes32 roomId);
    error NotEntitled(address user, bytes32 service);
    error NftGateFailed(bytes32 roomId, address user);
    error WorldProofFailed(bytes32 roomId, address user);
    error InvalidSignature();
    error ZeroAddress();

    constructor(address admin, IBankonEntitlement entitlement_) EIP712("Pay2PlayGate", "1") {
        if (admin == address(0) || address(entitlement_) == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ROOM_ADMIN_ROLE, admin);
        entitlement = entitlement_;
    }

    /* ───── Rooms ────────────────────────────────────────────────── */

    function setRoom(bytes32 roomId, Room calldata rm) external onlyRole(ROOM_ADMIN_ROLE) {
        _rooms[roomId] = rm;
        emit RoomSet(roomId, rm.service, rm.proofOracle, rm.nft, uint8(rm.nftKind), rm.nftId, rm.minNft, rm.active, rm.name);
    }

    function getRoom(bytes32 roomId) external view returns (Room memory) {
        return _rooms[roomId];
    }

    /* ───── Admission ────────────────────────────────────────────── */

    /// @notice Read-only pre-check: entitlement + NFT gate (proof is checked at
    ///         admit time with the proof bytes). UIs call this to enable/grey a
    ///         "connect" button before asking the wallet to sign.
    function eligible(address user, bytes32 roomId) public view returns (bool) {
        Room memory rm = _rooms[roomId];
        if (!rm.active) return false;
        if (!entitlement.hasAccess(user, rm.service)) return false;
        return _nftOk(rm, user);
    }

    /// @notice Admit yourself to `roomId` (msg.sender is the identity).
    function admit(bytes32 roomId, bytes calldata worldProof) external {
        _admit(roomId, msg.sender, worldProof, msg.sender);
    }

    /// @notice Seamless connect: `user` signed `Connect(roomId,user,nonce)` and
    ///         anyone (a relayer / the room server) submits it. The admission
    ///         binds to the signer — ownership of the private key is the identity.
    function admitWithSig(bytes32 roomId, address user, bytes calldata worldProof, bytes calldata sig) external {
        if (user == address(0)) revert ZeroAddress();
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(CONNECT_TYPEHASH, roomId, user, nonces[user]++))
        );
        if (!SignatureChecker.isValidSignatureNow(user, digest, sig)) revert InvalidSignature();
        _admit(roomId, user, worldProof, msg.sender);
    }

    function _admit(bytes32 roomId, address user, bytes calldata worldProof, address by) internal {
        Room memory rm = _rooms[roomId];
        if (!rm.active) revert RoomInactive(roomId);
        if (!entitlement.hasAccess(user, rm.service)) revert NotEntitled(user, rm.service);
        if (!_nftOk(rm, user)) revert NftGateFailed(roomId, user);
        if (rm.proofOracle != address(0)) {
            if (!IProofOracle(rm.proofOracle).proven(user, roomId, worldProof)) {
                revert WorldProofFailed(roomId, user);
            }
        }
        emit Admitted(roomId, user, by);
    }

    function _nftOk(Room memory rm, address user) internal view returns (bool) {
        if (rm.nftKind == NftKind.None) return true;
        if (rm.nftKind == NftKind.ERC721) return IERC721Bal(rm.nft).balanceOf(user) >= rm.minNft;
        return IERC1155Bal(rm.nft).balanceOf(user, rm.nftId) >= rm.minNft; // ERC1155
    }

    /// @notice EIP-712 domain separator, for off-chain `admitWithSig` signing.
    function domainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }
}
