// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl}     from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard}   from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {SafeERC20}         from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20}            from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {EIP712}            from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {SignatureChecker}  from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

import {
    IBANKONPaymentRouter,
    IBankonServiceRegistry,
    IBankonEntitlement
} from "./interfaces/IPay2Play.sol";

/// @title  BANKONPaymentRouter — the essential pay-to-play spine.
/// @author cypherpunk2048
/// @notice The router for BANKON-as-a-Service. It binds the three modular
///         concerns: it reads price/terms from the {BankonServiceRegistry},
///         charges the payer (native coin or ERC-20), takes a **fair and
///         nominal** fee (set here, hard-capped), forwards the net to the
///         service beneficiary, and grants the entitlement in the
///         {BankonEntitlement} ledger.
///
///         Identity is a signature. `playWithSig` lets a sponsor pay while the
///         entitlement binds to the wallet that signed the EIP-712 `Play`
///         message — ownership of the private key is the proof of identity.
///         This is what fulfils bankon.pythai.net: pay → signature-proven
///         identity → access.
///
///         Settlement is direct (transfer to beneficiary), so the router never
///         custodies funds. For HTTP-402 / cross-chain settlement, pair this
///         with the existing `contracts/x402/X402Receipt.sol` attestor, which
///         can be granted `GRANTER_ROLE` on the entitlement ledger to grant
///         access off a verified receipt without re-charging here.
contract BANKONPaymentRouter is AccessControl, ReentrancyGuard, EIP712, IBANKONPaymentRouter {
    using SafeERC20 for IERC20;

    IBankonServiceRegistry public immutable registry;
    IBankonEntitlement     public immutable entitlement;

    /// Fair & nominal fee. Default 2.5%, hard-capped at 10% so the rail can
    /// never become extractive — the value is the service, not the toll.
    uint16 public feeBps = 250;
    uint16 public constant MAX_FEE_BPS = 1000;
    address public feeRecipient;

    /// Per-identity nonce for the signature-proven `playWithSig` path.
    mapping(address => uint256) public nonces;

    bytes32 private constant PLAY_TYPEHASH =
        keccak256("Play(bytes32 serviceId,address user,uint256 nonce)");

    error ServiceInactive(bytes32 id);
    error WrongValue(uint256 sent, uint256 want);
    error FeeTooHigh();
    error ZeroAddress();
    error InvalidSignature();
    error NativeTransferFailed();

    constructor(
        address admin,
        IBankonServiceRegistry registry_,
        IBankonEntitlement entitlement_,
        address feeRecipient_
    ) EIP712("BANKONPaymentRouter", "1") {
        if (
            admin == address(0) ||
            address(registry_) == address(0) ||
            address(entitlement_) == address(0) ||
            feeRecipient_ == address(0)
        ) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        registry    = registry_;
        entitlement = entitlement_;
        feeRecipient = feeRecipient_;
    }

    /* ───── Play (pay → entitlement) ─────────────────────────────── */

    /// @notice Pay for `serviceId` and grant the entitlement to yourself.
    function play(bytes32 serviceId) external payable {
        _play(serviceId, msg.sender, msg.sender);
    }

    /// @notice Pay for `serviceId` and grant the entitlement to `user` (sponsor).
    function playFor(bytes32 serviceId, address user) external payable {
        if (user == address(0)) revert ZeroAddress();
        _play(serviceId, msg.sender, user);
    }

    /// @notice Pay for `serviceId`; the entitlement binds to `user`, who proved
    ///         identity by signing the EIP-712 `Play(serviceId,user,nonce)`
    ///         message. Supports EOA (ECDSA) and smart-account (ERC-1271) signers.
    function playWithSig(bytes32 serviceId, address user, bytes calldata sig) external payable {
        if (user == address(0)) revert ZeroAddress();
        bytes32 digest = _hashTypedDataV4(
            keccak256(abi.encode(PLAY_TYPEHASH, serviceId, user, nonces[user]++))
        );
        if (!SignatureChecker.isValidSignatureNow(user, digest, sig)) revert InvalidSignature();
        _play(serviceId, msg.sender, user);
    }

    function _play(bytes32 serviceId, address payer, address user) internal nonReentrant {
        IBankonServiceRegistry.Service memory s = registry.getService(serviceId);
        if (!s.active) revert ServiceInactive(serviceId);

        uint256 fee = (s.price * feeBps) / 10000;
        uint256 net = s.price - fee;

        if (s.asset == address(0)) {
            if (msg.value != s.price) revert WrongValue(msg.value, s.price);
            if (fee > 0) _sendNative(feeRecipient, fee);
            if (net > 0) _sendNative(s.beneficiary, net);
        } else {
            if (msg.value != 0) revert WrongValue(msg.value, 0);
            if (fee > 0) IERC20(s.asset).safeTransferFrom(payer, feeRecipient, fee);
            if (net > 0) IERC20(s.asset).safeTransferFrom(payer, s.beneficiary, net);
        }

        uint64 until = s.period == 0
            ? type(uint64).max
            : uint64(block.timestamp) + s.period;
        entitlement.grant(user, serviceId, s.tier, until);

        emit Played(serviceId, payer, user, s.asset, s.price, fee, until);
    }

    function _sendNative(address to, uint256 amount) internal {
        (bool ok, ) = payable(to).call{value: amount}("");
        if (!ok) revert NativeTransferFailed();
    }

    /* ───── Admin ────────────────────────────────────────────────── */

    /// @notice Update the fair/nominal fee and its recipient (≤ 10%).
    function setFee(uint16 newBps, address newRecipient) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (newBps > MAX_FEE_BPS) revert FeeTooHigh();
        if (newRecipient == address(0)) revert ZeroAddress();
        feeBps = newBps;
        feeRecipient = newRecipient;
        emit FeeConfigUpdated(newBps, newRecipient);
    }

    /// @notice The EIP-712 domain separator, for off-chain `playWithSig` signing.
    function domainSeparator() external view returns (bytes32) {
        return _domainSeparatorV4();
    }
}
