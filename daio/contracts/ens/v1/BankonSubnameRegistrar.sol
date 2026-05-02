// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {ERC1155Holder} from "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";

import {
    INameWrapper, IPublicResolver, IBankonPriceOracle,
    IBankonReputationGate, IIdentityRegistry8004, IBankonPaymentRouter
} from "./interfaces/IBankon.sol";

/// @notice Off-chain payment voucher payload — written to docs/INFT_7857-style
///         text records on the resolved subname. Field set is intentionally
///         small + chain-aware (ENSIP-11 + custom keys for x402).
struct AgentMetadata {
    string  agentURI;          // ERC-8004 agent card JSON URI
    string  mindxEndpoint;     // optional consumer URL (e.g. https://mindx.pythai.net/agent/<id>)
    string  x402Endpoint;      // service endpoint that speaks HTTP 402
    string  algoIDNftDID;      // Algorand DID, did:algo:…
    bytes   contenthash;       // ipfs/ar contenthash (ENSIP-7)
    address baseAddress;       // Base L2 (coinType 0x80002105 = 2147483648 + 8453)
    bytes   algoAddr;          // Algorand 32-byte address (coinType 0x8000011B = SLIP-44 283)
}

/// @title  BankonSubnameRegistrar
/// @notice ENS NameWrapper-based registrar issuing agent subnames under
///         `bankon.eth`. Bundles ERC-8004 identity, EIP-712 voucher payment,
///         BONAFIDE/x402 reputation gating, and length-tiered pricing.
///
///         **Agnostic-module**: any framework — mindX, OpenClaw, NanoClaw,
///         or your stack — can register agent subnames via this contract.
///         The registrar does not assume any framework is present; gateway
///         relayers + clients can be implemented in any language.
///
///         **Horizontal scaling**: multi-chain x402 settlement via
///         BankonPaymentRouter (Base USDC, Algorand PYTHAI, L1 ETH/USDC).
///         **Vertical scaling**: 4 length tiers × 3+ payment assets ×
///         3 reputation tiers (paid / free-by-stake / free-by-attestation).
contract BankonSubnameRegistrar is
    AccessControl,
    ReentrancyGuard,
    Pausable,
    EIP712,
    ERC1155Holder
{
    using ECDSA for bytes32;

    /* ───── Roles ─────────────────────────────────────────────────── */
    bytes32 public constant BANKON_OPS_ROLE      = keccak256("BANKON_OPS_ROLE");
    bytes32 public constant BONAFIDE_GOV_ROLE    = keccak256("BONAFIDE_GOV_ROLE");
    bytes32 public constant GATEWAY_SIGNER_ROLE  = keccak256("GATEWAY_SIGNER_ROLE");
    bytes32 public constant MINDX_AGENT_MINTER_ROLE = keccak256("MINDX_AGENT_MINTER_ROLE");

    /* ───── Constants ─────────────────────────────────────────────── */
    /// Soulbound default: PARENT_CANNOT_CONTROL | CANNOT_UNWRAP |
    ///                    CANNOT_TRANSFER | CAN_EXTEND_EXPIRY
    /// = 0x10000 | 0x1 | 0x4 | 0x40000 = 0x50005.
    uint32 public constant DEFAULT_FUSES = uint32(0x10000 | 0x1 | 0x4 | 0x40000);

    /// EIP-712 typehashes.
    bytes32 public constant REGISTRATION_TYPEHASH = keccak256(
        "Registration(string label,address owner,uint64 expiry,bytes32 paymentReceiptHash,uint256 deadline)"
    );
    bytes32 public constant RENEWAL_TYPEHASH = keccak256(
        "Renewal(string label,uint64 newExpiry,bytes32 paymentReceiptHash,uint256 deadline)"
    );

    /// SLIP-44 coinTypes for ENSIP-11 multi-chain addr records.
    uint256 public constant COIN_TYPE_BASE = 0x80002105;     // EVM Base = 2147483648 | 8453
    uint256 public constant COIN_TYPE_ALGO = 0x8000011B;     // SLIP-44 283 (Algorand)

    /* ───── Immutable wiring ──────────────────────────────────────── */
    INameWrapper        public immutable nameWrapper;
    IPublicResolver     public immutable defaultResolver;
    bytes32             public immutable parentNode;            // namehash("bankon.eth")
    IBankonPaymentRouter public immutable paymentRouter;

    /* ───── Mutable wiring ────────────────────────────────────────── */
    IBankonPriceOracle    public priceOracle;
    IBankonReputationGate public reputationGate;
    IIdentityRegistry8004 public identityRegistry8004;

    bool public erc8004BundleEnabled = true;

    /* ───── State ─────────────────────────────────────────────────── */
    mapping(bytes32 => bool)   public usedReceipts;     // EIP-712 voucher replay protection
    mapping(bytes32 => string) public labelOf;          // node → label, for indexing
    mapping(bytes32 => address) public ownerOfLabel;    // node → owner

    /* ───── Events ────────────────────────────────────────────────── */
    event SubnameRegistered(
        bytes32 indexed node,
        string  label,
        address indexed owner,
        uint64  expiry,
        uint256 priceUSD6,
        bytes32 paymentReceiptHash,
        uint256 erc8004AgentId,
        bool    free
    );
    event SubnameRenewed(bytes32 indexed node, string label, uint64 newExpiry, uint256 priceUSD6);
    event ResolverRecordsWritten(bytes32 indexed node, address indexed owner);
    event PriceOracleUpdated(address oldOracle, address newOracle);
    event ReputationGateUpdated(address oldGate, address newGate);
    event IdentityRegistryUpdated(address oldReg, address newReg);
    event Erc8004BundleToggled(bool enabled);

    /* ───── Errors ────────────────────────────────────────────────── */
    error LabelTooShort();
    error LabelEmpty();
    error ReceiptAlreadyUsed();
    error VoucherExpired();
    error InvalidGatewaySignature();
    error NotEligible();
    error InvalidExpiry();
    error ZeroAddress();

    /* ───── Constructor ───────────────────────────────────────────── */
    constructor(
        address _nameWrapper,
        address _defaultResolver,
        bytes32 _parentNode,
        address _paymentRouter,
        address _priceOracle,
        address _reputationGate,
        address _identityRegistry8004,
        address _admin
    )
        EIP712("BankonSubnameRegistrar", "1")
    {
        if (_nameWrapper == address(0))     revert ZeroAddress();
        if (_defaultResolver == address(0)) revert ZeroAddress();
        if (_paymentRouter == address(0))   revert ZeroAddress();
        if (_priceOracle == address(0))     revert ZeroAddress();
        if (_reputationGate == address(0))  revert ZeroAddress();
        if (_admin == address(0))           revert ZeroAddress();
        nameWrapper          = INameWrapper(_nameWrapper);
        defaultResolver      = IPublicResolver(_defaultResolver);
        parentNode           = _parentNode;
        paymentRouter        = IBankonPaymentRouter(_paymentRouter);
        priceOracle          = IBankonPriceOracle(_priceOracle);
        reputationGate       = IBankonReputationGate(_reputationGate);
        identityRegistry8004 = IIdentityRegistry8004(_identityRegistry8004);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(BANKON_OPS_ROLE, _admin);
        _grantRole(BONAFIDE_GOV_ROLE, _admin);
    }

    /* ═════════════════════════════════════════════════════════════════ */
    /*  Registration                                                     */
    /* ═════════════════════════════════════════════════════════════════ */

    /// @notice Register an agent subname after off-chain x402 payment.
    /// @dev Caller is typically the gateway relayer; the EIP-712 voucher
    ///      binds (label,owner,expiry,paymentReceiptHash,deadline) to a
    ///      gateway signer authorized via `GATEWAY_SIGNER_ROLE`.
    function register(
        string calldata label,
        address owner,
        uint64 expiry,
        bytes32 paymentReceiptHash,
        uint256 deadline,
        bytes calldata gatewaySig,
        AgentMetadata calldata meta
    )
        external
        nonReentrant
        whenNotPaused
        returns (bytes32 node, uint256 agentId)
    {
        _checkLabel(label);
        if (owner == address(0))                                   revert ZeroAddress();
        if (block.timestamp > deadline)                            revert VoucherExpired();
        if (usedReceipts[paymentReceiptHash])                      revert ReceiptAlreadyUsed();
        if (!reputationGate.isEligibleForRegistration(owner))      revert NotEligible();

        // Verify EIP-712 voucher.
        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(
            REGISTRATION_TYPEHASH,
            keccak256(bytes(label)),
            owner,
            expiry,
            paymentReceiptHash,
            deadline
        )));
        if (!hasRole(GATEWAY_SIGNER_ROLE, digest.recover(gatewaySig))) {
            revert InvalidGatewaySignature();
        }
        usedReceipts[paymentReceiptHash] = true;

        expiry = _capExpiry(expiry);

        // Three-step register-records-transfer (the canonical pattern from
        // docs.ens.domains/wrapper/creating-subname-registrar).
        node = _writeAndTransfer(label, owner, expiry, meta);

        // Bundle ERC-8004 identity mint.
        if (erc8004BundleEnabled && address(identityRegistry8004) != address(0)) {
            agentId = identityRegistry8004.register(owner, meta.agentURI);
            // Best-effort metadata writes — never revert if registry rejects.
            _safeSetMeta(agentId, "bankon.ensName", bytes(_concat(label, ".bankon.eth")));
            _safeSetMeta(agentId, "bankon.subnameNode", abi.encode(node));
        }

        // Record receipt with the payment router for accounting + buyback signaling.
        uint256 priceUSD6 = priceOracle.priceUSD(label, _yearsFromExpiry(expiry));
        if (paymentRouter.splitConfigured()) {
            // Best-effort — don't unwind the mint if the router refuses.
            try paymentRouter.recordReceipt(paymentReceiptHash, priceUSD6, address(0)) {}
            catch {}
        }

        emit SubnameRegistered(node, label, owner, expiry, priceUSD6,
                               paymentReceiptHash, agentId, false);
    }

    /// @notice Free address-as-label registration for mindX agents.
    /// @dev    Label is the lowercase 40-char hex of `agent` (no 0x prefix),
    ///         producing `<addr>.bankon.eth`. Caller must hold
    ///         MINDX_AGENT_MINTER_ROLE — the agent itself does not pay or
    ///         attest reputation; the role-holder (a mint service) attests
    ///         that the agent is a registered mindX agent.
    ///
    ///         The existing free/paid system is preserved:
    ///         - `register` (paid, EIP-712 voucher) — UNCHANGED
    ///         - `registerFree` (free, reputation-gated, 7+ char) — UNCHANGED
    ///         - `registerAgentSubname` (free, role-gated, address-as-label) — NEW
    ///
    ///         Anyone with MINDX_AGENT_MINTER_ROLE can mint at zero fee.
    ///         The role-holder is expected to verify off-chain that `agent`
    ///         is a real mindX agent before calling.
    function registerAgentSubname(
        address agent,
        uint64 expiry,
        AgentMetadata calldata meta
    )
        external
        nonReentrant
        whenNotPaused
        onlyRole(MINDX_AGENT_MINTER_ROLE)
        returns (bytes32 node, uint256 agentId, string memory label)
    {
        if (agent == address(0)) revert ZeroAddress();
        // Label = lowercase 40-char hex of address (no 0x). 40 chars > 7-min.
        label = _addressToLowerHex(agent);
        expiry = _capExpiry(expiry);
        node = _writeAndTransfer(label, agent, expiry, meta);

        if (erc8004BundleEnabled && address(identityRegistry8004) != address(0)) {
            agentId = identityRegistry8004.register(agent, meta.agentURI);
            _safeSetMeta(agentId, "bankon.ensName", bytes(_concat(label, ".bankon.eth")));
        }
        emit SubnameRegistered(node, label, agent, expiry, 0,
                               bytes32(0), agentId, true);
    }

    /// @dev Convert address to lowercase 40-char hex (no 0x prefix).
    function _addressToLowerHex(address a) internal pure returns (string memory) {
        bytes memory buf = new bytes(40);
        uint160 v = uint160(a);
        for (uint256 i = 0; i < 40; i++) {
            uint8 nibble = uint8((v >> ((39 - i) * 4)) & 0xf);
            buf[i] = bytes1(nibble < 10 ? nibble + 0x30 : nibble + 0x57); // '0'-'9' or 'a'-'f'
        }
        return string(buf);
    }

    /// @notice Free registration path for reputation-eligible agents (7+ char only).
    function registerFree(
        string calldata label,
        address owner,
        uint64 expiry,
        AgentMetadata calldata meta
    )
        external
        nonReentrant
        whenNotPaused
        returns (bytes32 node, uint256 agentId)
    {
        if (owner == address(0))                          revert ZeroAddress();
        if (bytes(label).length < 7)                      revert LabelTooShort();
        if (!reputationGate.isEligibleForFree(owner))     revert NotEligible();

        expiry = _capExpiry(expiry);
        node = _writeAndTransfer(label, owner, expiry, meta);

        if (erc8004BundleEnabled && address(identityRegistry8004) != address(0)) {
            agentId = identityRegistry8004.register(owner, meta.agentURI);
            _safeSetMeta(agentId, "bankon.ensName", bytes(_concat(label, ".bankon.eth")));
        }
        emit SubnameRegistered(node, label, owner, expiry, 0,
                               bytes32(0), agentId, true);
    }

    /// @notice Renew (extend expiry) of an existing subname.
    function renew(
        string calldata label,
        uint64 newExpiry,
        bytes32 paymentReceiptHash,
        uint256 deadline,
        bytes calldata gatewaySig
    )
        external
        nonReentrant
        whenNotPaused
    {
        if (block.timestamp > deadline) revert VoucherExpired();
        if (usedReceipts[paymentReceiptHash]) revert ReceiptAlreadyUsed();

        bytes32 digest = _hashTypedDataV4(keccak256(abi.encode(
            RENEWAL_TYPEHASH,
            keccak256(bytes(label)),
            newExpiry,
            paymentReceiptHash,
            deadline
        )));
        if (!hasRole(GATEWAY_SIGNER_ROLE, digest.recover(gatewaySig))) {
            revert InvalidGatewaySignature();
        }
        usedReceipts[paymentReceiptHash] = true;

        bytes32 labelhash = keccak256(bytes(label));
        bytes32 node      = keccak256(abi.encodePacked(parentNode, labelhash));
        uint64 actual = nameWrapper.extendExpiry(parentNode, labelhash, newExpiry);
        uint256 priceUSD6 = priceOracle.priceUSD(label, _yearsFromExpiry(actual));

        if (paymentRouter.splitConfigured()) {
            try paymentRouter.recordReceipt(paymentReceiptHash, priceUSD6, address(0)) {}
            catch {}
        }
        emit SubnameRenewed(node, label, actual, priceUSD6);
    }

    /* ═════════════════════════════════════════════════════════════════ */
    /*  Internals                                                        */
    /* ═════════════════════════════════════════════════════════════════ */

    function _checkLabel(string calldata label) internal pure {
        uint256 len = bytes(label).length;
        if (len == 0) revert LabelEmpty();
        if (len < 3)  revert LabelTooShort();
    }

    function _capExpiry(uint64 expiry) internal view returns (uint64) {
        if (expiry <= block.timestamp) revert InvalidExpiry();
        (, , uint64 parentExpiry) = nameWrapper.getData(uint256(parentNode));
        if (parentExpiry > 0 && expiry > parentExpiry) {
            return parentExpiry;
        }
        return expiry;
    }

    /// @dev Three-step canonical pattern: temp-self-own → write records →
    ///      transfer with locked fuses. Returns the subname node.
    function _writeAndTransfer(
        string memory label,
        address owner,
        uint64 expiry,
        AgentMetadata calldata meta
    ) internal returns (bytes32 node) {
        // Step 1: mint subname owned by THIS contract so we can write records.
        nameWrapper.setSubnodeOwner(parentNode, label, address(this), 0, expiry);
        node = keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));

        // Step 2: write resolver records via multicall.
        _writeAgentRecords(node, owner, meta);

        // Step 3: transfer to owner with soulbound fuses burned.
        nameWrapper.setSubnodeRecord(
            parentNode, label, owner,
            address(defaultResolver), 0,
            DEFAULT_FUSES, expiry
        );
        labelOf[node] = label;
        ownerOfLabel[node] = owner;
        emit ResolverRecordsWritten(node, owner);
    }

    function _writeAgentRecords(
        bytes32 node,
        address owner,
        AgentMetadata calldata meta
    ) internal {
        // Build the resolver multicall. We size dynamically to skip fields
        // the caller left empty so we don't waste gas on no-op writes.
        uint256 n = 1; // setAddr(node, owner) is always written
        if (bytes(meta.mindxEndpoint).length > 0) n++;
        if (bytes(meta.x402Endpoint).length > 0)  n++;
        if (bytes(meta.algoIDNftDID).length > 0)  n++;
        if (bytes(meta.agentURI).length > 0)      n++;
        if (meta.contenthash.length > 0)          n++;
        if (meta.baseAddress != address(0))       n++;
        if (meta.algoAddr.length > 0)             n++;

        bytes[] memory calls = new bytes[](n);
        uint256 i = 0;

        // setAddr(bytes32,address) — disambiguate from the multi-chain overload.
        calls[i++] = abi.encodeWithSignature("setAddr(bytes32,address)", node, owner);

        if (bytes(meta.mindxEndpoint).length > 0) {
            calls[i++] = abi.encodeCall(IPublicResolver.setText, (node, "url", meta.mindxEndpoint));
        }
        if (bytes(meta.x402Endpoint).length > 0) {
            calls[i++] = abi.encodeCall(IPublicResolver.setText, (node, "x402.endpoint", meta.x402Endpoint));
        }
        if (bytes(meta.algoIDNftDID).length > 0) {
            calls[i++] = abi.encodeCall(IPublicResolver.setText, (node, "algoid.did", meta.algoIDNftDID));
        }
        if (bytes(meta.agentURI).length > 0) {
            calls[i++] = abi.encodeCall(IPublicResolver.setText, (node, "agent.card", meta.agentURI));
        }
        if (meta.contenthash.length > 0) {
            calls[i++] = abi.encodeCall(IPublicResolver.setContenthash, (node, meta.contenthash));
        }
        if (meta.baseAddress != address(0)) {
            calls[i++] = abi.encodeWithSignature(
                "setAddr(bytes32,uint256,bytes)",
                node, COIN_TYPE_BASE, abi.encodePacked(meta.baseAddress)
            );
        }
        if (meta.algoAddr.length > 0) {
            calls[i++] = abi.encodeWithSignature(
                "setAddr(bytes32,uint256,bytes)",
                node, COIN_TYPE_ALGO, meta.algoAddr
            );
        }

        defaultResolver.multicall(calls);
    }

    function _safeSetMeta(uint256 agentId, bytes32 key, bytes memory value) internal {
        try identityRegistry8004.setMetadata(agentId, key, value) {} catch {}
    }

    function _yearsFromExpiry(uint64 expiry) internal view returns (uint256) {
        if (expiry <= block.timestamp) return 0;
        return (uint256(expiry) - block.timestamp + 365 days - 1) / 365 days;
    }

    function _concat(string memory a, string memory b)
        internal pure returns (string memory)
    {
        return string(abi.encodePacked(a, b));
    }

    /* ═════════════════════════════════════════════════════════════════ */
    /*  Read helpers + admin                                             */
    /* ═════════════════════════════════════════════════════════════════ */

    function quoteUSD(string calldata label, uint64 expiry)
        external view
        returns (uint256 usd6)
    {
        uint64 capped = expiry > 0 ? expiry : uint64(block.timestamp + 365 days);
        return priceOracle.priceUSD(label, _yearsFromExpiry(capped));
    }

    function setPriceOracle(address _o) external onlyRole(BONAFIDE_GOV_ROLE) {
        if (_o == address(0)) revert ZeroAddress();
        emit PriceOracleUpdated(address(priceOracle), _o);
        priceOracle = IBankonPriceOracle(_o);
    }

    function setReputationGate(address _g) external onlyRole(BONAFIDE_GOV_ROLE) {
        if (_g == address(0)) revert ZeroAddress();
        emit ReputationGateUpdated(address(reputationGate), _g);
        reputationGate = IBankonReputationGate(_g);
    }

    function setIdentityRegistry8004(address _r) external onlyRole(BONAFIDE_GOV_ROLE) {
        emit IdentityRegistryUpdated(address(identityRegistry8004), _r);
        identityRegistry8004 = IIdentityRegistry8004(_r);
    }

    function setErc8004Bundle(bool enabled) external onlyRole(BONAFIDE_GOV_ROLE) {
        erc8004BundleEnabled = enabled;
        emit Erc8004BundleToggled(enabled);
    }

    function pause()   external onlyRole(BANKON_OPS_ROLE) { _pause(); }
    function unpause() external onlyRole(BANKON_OPS_ROLE) { _unpause(); }

    /// @dev Compose ERC1155Holder + AccessControl interface support.
    function supportsInterface(bytes4 interfaceId)
        public view
        override(AccessControl, ERC1155Holder)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
