// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// bankon_custody — the shared base for the BANKON treasury + remittance contracts.
// A safe multi-asset vault that can hold and receive ANY asset on ANY EVM chain —
// native, ERC-20, ERC-721, ERC-1155 — and whose value can ONLY ever be redeemed
// to the immutable founding owner (bankon.eth). Governance begins as a single-owner
// "dictator" (bankon.eth) and can migrate to an m-of-n multisig consensus
// (2-of-2, 2-of-3, 3-of-3) over owner-chosen wallet addresses, or renounce.
//
// Two outbound paths:
//   • redeem_*  → PERMISSIONLESS sweep, destination hard-wired to FOUNDER. Anyone can
//                 push assets home to bankon.eth; safe because the target is immutable.
//   • execute / allocate_*  → GOVERNED disbursement to any address (operations), gated
//                 by the dictator owner or the multisig consensus.
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {IERC1155} from "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";
import {ERC721Holder} from "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import {ERC1155Holder} from "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

abstract contract bankon_custody is ERC721Holder, ERC1155Holder, ReentrancyGuard {
    using SafeERC20 for IERC20;

    enum Mode { DICTATOR, MULTISIG }

    /// @notice The immutable founding owner — the ONLY destination value can be redeemed to (bankon.eth).
    address public immutable FOUNDER;

    Mode public mode;
    /// @notice Dictator admin (set to FOUNDER at birth). Authoritative only while mode == DICTATOR.
    address public owner;
    /// @notice Multisig signer set + threshold, once migrated (mode == MULTISIG).
    address[] public signers;
    uint256 public threshold;
    mapping(address => bool) public isSigner;
    /// @notice Replay nonce for multisig-authorized executes.
    uint256 public nonce;
    /// @notice Once true, governance can NEVER return to a 1:1 dictator (one-way, opt-in at renounce).
    bool public dictator_locked;

    bytes32 private constant EXECUTE_TYPEHASH =
        keccak256("Execute(address target,uint256 value,bytes32 dataHash,uint256 nonce)");
    bytes32 private constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    // Cached EIP-712 domain separator (rebuilt only on a chain-id fork). [audit: gas]
    uint256 private immutable _CACHED_CHAIN_ID;
    bytes32 private immutable _CACHED_DOMAIN_SEPARATOR;

    event Redeemed(string kind, address indexed asset, uint256 idOrAmount);
    event Allocated(string kind, address indexed asset, address indexed to, uint256 idOrAmount);
    event Executed(address indexed target, uint256 value, bytes data, bool viaMultisig);
    event GovernanceSet(Mode mode, address[] signers, uint256 threshold, address owner);
    event DictatorLockedOut();

    error not_owner();
    error not_dictator();
    error not_multisig();
    error bad_consensus();
    error insufficient_approvals();
    error unsorted_or_unknown_signer();
    error dictator_locked_out();

    constructor(address founder_) {
        require(founder_ != address(0), "founder=0");
        FOUNDER = founder_;
        owner = founder_;     // begins life as dictator/admin of the one founding address
        mode = Mode.DICTATOR;
        _CACHED_CHAIN_ID = block.chainid;
        _CACHED_DOMAIN_SEPARATOR = _buildDomainSeparator();
    }

    receive() external payable {}

    // ─────────────────────────────── redeem: home to FOUNDER only ───────────────────────────────
    // Permissionless — destination is the immutable FOUNDER, so anyone may push assets home.

    function redeem_native() external nonReentrant {
        uint256 bal = address(this).balance;
        if (bal == 0) return;
        (bool ok, ) = payable(FOUNDER).call{value: bal}("");
        require(ok, "native redeem failed");
        emit Redeemed("native", address(0), bal);
    }

    function redeem_erc20(address token) external nonReentrant {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal == 0) return;
        IERC20(token).safeTransfer(FOUNDER, bal);
        emit Redeemed("erc20", token, bal);
    }

    function redeem_erc721(address token, uint256 id) external nonReentrant {
        IERC721(token).safeTransferFrom(address(this), FOUNDER, id);
        emit Redeemed("erc721", token, id);
    }

    function redeem_erc1155(address token, uint256 id, uint256 amount) external nonReentrant {
        uint256 amt = amount == 0 ? IERC1155(token).balanceOf(address(this), id) : amount;
        IERC1155(token).safeTransferFrom(address(this), FOUNDER, id, amt, "");
        emit Redeemed("erc1155", token, id);
    }

    // ─────────────────────────────── governed allocation (operations) ───────────────────────────
    // DICTATOR: onlyOwner direct. MULTISIG: encode as execute_signed(token,...). Sends anywhere.

    function allocate_native(address to, uint256 amount) external nonReentrant onlyDictator {
        (bool ok, ) = payable(to).call{value: amount}("");
        require(ok, "native allocate failed");
        emit Allocated("native", address(0), to, amount);
    }
    function allocate_erc20(address token, address to, uint256 amount) external nonReentrant onlyDictator {
        IERC20(token).safeTransfer(to, amount);
        emit Allocated("erc20", token, to, amount);
    }
    function allocate_erc721(address token, address to, uint256 id) external nonReentrant onlyDictator {
        IERC721(token).safeTransferFrom(address(this), to, id);
        emit Allocated("erc721", token, to, id);
    }
    function allocate_erc1155(address token, address to, uint256 id, uint256 amount) external nonReentrant onlyDictator {
        IERC1155(token).safeTransferFrom(address(this), to, id, amount, "");
        emit Allocated("erc1155", token, to, id);
    }

    /// @notice Arbitrary governed call (dictator). For multisig use execute_signed.
    function execute(address target, uint256 value, bytes calldata data)
        external nonReentrant onlyDictator returns (bytes memory)
    {
        return _exec(target, value, data, false);
    }

    /// @notice Arbitrary call authorized by m-of-n multisig signatures (EIP-712). `sigs` must be
    ///         ordered by ascending recovered signer to prevent duplicates; ≥ threshold required.
    function execute_signed(address target, uint256 value, bytes calldata data, bytes[] calldata sigs)
        external nonReentrant returns (bytes memory)
    {
        if (mode != Mode.MULTISIG) revert not_multisig();
        _verify(_digest(target, value, data), sigs);
        nonce += 1;
        return _exec(target, value, data, true);
    }

    function _exec(address target, uint256 value, bytes calldata data, bool viaMs) internal returns (bytes memory) {
        (bool ok, bytes memory ret) = target.call{value: value}(data);
        require(ok, "execute failed");
        emit Executed(target, value, data, viaMs);
        return ret;
    }

    // ─────────────────────────────── governance: renounce / re-key state machine ─────────────────

    /// @notice "Renounce" the current governance shape in favour of a new one. The valid shapes are
    ///         **1:1** (single owner / dictator — `owner` forwarded as the default address, not
    ///         necessarily one of any prior pair), **2:2**, **2:3**, **3:3**. Transitions:
    ///           • a 1:1 dictator may go directly to 2:2 / 2:3 / 3:3;
    ///           • a multisig may re-key to any other shape — including a 3:3 voting to instate a 1:1
    ///             — but only via `execute_signed` (i.e. authorized by ≥ threshold signatures).
    ///         `lock_out_dictator` (only valid when moving to a multisig) makes it a **complete,
    ///         never-return-to-1:1** renounce: once set, instating a 1:1 is forbidden forever.
    function renounce_to(address[] calldata newSigners, uint256 newThreshold, bool lock_out_dictator)
        external
    {
        // authorized by the CURRENT mode
        if (mode == Mode.DICTATOR) { if (msg.sender != owner) revert not_owner(); }
        else { if (msg.sender != address(this)) revert not_multisig(); } // multisig → via execute_signed self-call

        uint256 n = newSigners.length;
        if (!_valid_consensus(n, newThreshold)) revert bad_consensus();
        if (lock_out_dictator && n == 1) revert bad_consensus();           // contradiction
        if (dictator_locked && n == 1) revert dictator_locked_out();       // permanent: no return to 1:1

        // clear the old signer set
        for (uint256 i = 0; i < signers.length; i++) isSigner[signers[i]] = false;
        delete signers;
        // install the new set
        for (uint256 i = 0; i < n; i++) {
            address s = newSigners[i];
            require(s != address(0) && !isSigner[s], "bad signer");
            isSigner[s] = true;
            signers.push(s);
        }
        threshold = newThreshold;
        if (n == 1) { mode = Mode.DICTATOR; owner = newSigners[0]; }        // instate a 1:1
        else { mode = Mode.MULTISIG; owner = FOUNDER; }                     // owner forwarded as default

        if (lock_out_dictator && !dictator_locked) { dictator_locked = true; emit DictatorLockedOut(); }
        emit GovernanceSet(mode, newSigners, threshold, owner);
    }

    function _valid_consensus(uint256 n, uint256 m) internal pure returns (bool) {
        return (m == 1 && n == 1) || (m == 2 && (n == 2 || n == 3)) || (m == 3 && n == 3);
    }

    function signerCount() external view returns (uint256) { return signers.length; }

    // ─────────────────────────────── EIP-712 multisig verification ───────────────────────────────

    function _buildDomainSeparator() private view returns (bytes32) {
        return keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256("bankon_custody"), keccak256("1"), block.chainid, address(this)));
    }
    function _domainSeparator() internal view returns (bytes32) {
        // Cached unless the chain forked to a new chain-id (then recompute, fork-safe).
        return block.chainid == _CACHED_CHAIN_ID ? _CACHED_DOMAIN_SEPARATOR : _buildDomainSeparator();
    }
    function _digest(address target, uint256 value, bytes calldata data) internal view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(EXECUTE_TYPEHASH, target, value, keccak256(data), nonce));
        return keccak256(abi.encodePacked("\x19\x01", _domainSeparator(), structHash));
    }
    function _verify(bytes32 digest, bytes[] calldata sigs) internal view {
        // sigs.length ≥ threshold AND every sig is a distinct, valid signer (strictly ascending
        // recovered address ⇒ no duplicates) ⇒ ≥ threshold distinct approvals. [audit: dropped
        // the redundant post-loop count check].
        if (sigs.length < threshold) revert insufficient_approvals();
        address last = address(0);
        for (uint256 i = 0; i < sigs.length; i++) {
            address rec = ECDSA.recover(digest, sigs[i]);
            if (rec <= last || !isSigner[rec]) revert unsorted_or_unknown_signer();
            last = rec;
        }
    }

    modifier onlyDictator() {
        if (mode != Mode.DICTATOR) revert not_dictator();
        if (msg.sender != owner) revert not_owner();
        _;
    }
}
