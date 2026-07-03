// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ERC721 }        from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import { Pausable }      from "@openzeppelin/contracts/utils/Pausable.sol";
import { IERC20 }        from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 }     from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { MerkleProof }   from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

import { IiDEBT }                 from "../interfaces/IiDEBT.sol";
import { IGlobalDebtStressIndex } from "../interfaces/IGlobalDebtStressIndex.sol";
import { IX402 }                  from "../interfaces/IX402.sol";
import { DebtMath }               from "../libraries/DebtMath.sol";

/// @title iDEBT
/// @notice Cryptographic Inheritance of Global DEBT — ERC-721 debt positions
///         that mark-to-market against the GlobalDebtStressIndex and pass to
///         registered heirs after on-chain dormancy.
/// @dev    Inheritance uses a Merkle commitment: the holder commits to a
///         `proofRoot` at open time; heirs later present a proof of membership
///         alongside their share. This lets holders keep heir identities
///         private until a claim is made.
contract iDEBT is IiDEBT, ERC721, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;
    using DebtMath  for uint256;

    bytes32 public constant GOVERNOR_ROLE   = keccak256("GOVERNOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE  = keccak256("EMERGENCY_ROLE");

    /// @notice Payment scope identifier for x402 gated `openPosition`.
    bytes32 public constant SCOPE_OPEN = keccak256("iDEBT.open");
    /// @notice Payment scope identifier for x402 gated `claimInheritance`.
    bytes32 public constant SCOPE_CLAIM = keccak256("iDEBT.claim");

    IGlobalDebtStressIndex public immutable stressIndex;
    IERC20                 public immutable settlementToken; // e.g. USDC
    IX402                  public x402;                      // optional payment gate

    uint256 public nextTokenId = 1;
    uint256 public maxPrincipal = 10_000_000e18; // default cap per position
    uint256 public protocolFeeBps = 50;          // 0.5%
    address public feeSink;

    // tokenId => position
    mapping(uint256 => Position)         private _positions;
    // tokenId => Merkle root over heir leaves
    mapping(uint256 => bytes32)          private _heirRoot;
    // tokenId => heir count
    mapping(uint256 => uint8)            private _heirCount;
    // tokenId => (heir leaf => claimed?)
    mapping(uint256 => mapping(bytes32 => bool)) private _claimed;

    constructor(
        address stressIndex_,
        address settlementToken_,
        address feeSink_,
        address admin
    ) ERC721("iDEBT Position", "iDEBT") {
        require(stressIndex_ != address(0) && settlementToken_ != address(0), "zero");
        stressIndex = IGlobalDebtStressIndex(stressIndex_);
        settlementToken = IERC20(settlementToken_);
        feeSink = feeSink_;
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNOR_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);
    }

    // -------------------------------------------------------------- //
    //                             ADMIN                              //
    // -------------------------------------------------------------- //

    function setX402(address gate) external onlyRole(GOVERNOR_ROLE) {
        x402 = IX402(gate);
    }

    function setFee(uint256 bps, address sink) external onlyRole(GOVERNOR_ROLE) {
        require(bps <= 1_000, "fee too high");
        protocolFeeBps = bps;
        feeSink = sink;
    }

    function setMaxPrincipal(uint256 cap) external onlyRole(GOVERNOR_ROLE) {
        maxPrincipal = cap;
    }

    function pause()   external onlyRole(EMERGENCY_ROLE) { _pause(); }
    function unpause() external onlyRole(EMERGENCY_ROLE) { _unpause(); }

    // -------------------------------------------------------------- //
    //                           OPEN / HOLD                          //
    // -------------------------------------------------------------- //

    /// @inheritdoc IiDEBT
    /// @dev `heirs` MUST be presented in canonical order; the Merkle root is
    ///      computed off-chain using keccak256 leaves of (successor, sharesBps,
    ///      proofRoot_i) and passed as the last element's `proofRoot`.
    function openPosition(
        uint256 principal,
        uint64  maturity,
        uint64  dormancy,
        Heir[] calldata heirs
    ) external override whenNotPaused nonReentrant returns (uint256 tokenId) {
        if (principal == 0 || principal > maxPrincipal) revert ExceedsCap();
        if (maturity <= block.timestamp) revert NotMatured();
        if (heirs.length == 0 || heirs.length > 32) revert InvalidHeirs();
        _ensurePaid(SCOPE_OPEN);

        uint256 sharesSum;
        bytes32 root = heirs[0].proofRoot; // convention: first heir carries the root
        for (uint256 i = 0; i < heirs.length; ++i) {
            if (heirs[i].successor == address(0)) revert InvalidHeirs();
            sharesSum += heirs[i].sharesBps;
        }
        if (sharesSum != 10_000) revert InvalidHeirs();

        tokenId = nextTokenId++;
        uint256 mark = stressIndex.score();

        _positions[tokenId] = Position({
            principal:     principal,
            stressMark:    mark,
            mintedAt:      uint64(block.timestamp),
            maturity:      maturity,
            lastHeartbeat: uint64(block.timestamp),
            dormancy:      dormancy,
            holder:        msg.sender
        });
        _heirRoot[tokenId]  = root;
        _heirCount[tokenId] = uint8(heirs.length);

        // Pull principal collateral + protocol fee from holder.
        uint256 fee = (principal * protocolFeeBps) / 10_000;
        if (fee > 0 && feeSink != address(0)) {
            settlementToken.safeTransferFrom(msg.sender, feeSink, fee);
        }
        settlementToken.safeTransferFrom(msg.sender, address(this), principal);

        _safeMint(msg.sender, tokenId);
        emit PositionOpened(tokenId, msg.sender, principal);
        emit HeirsConfigured(tokenId, uint8(heirs.length), root);
    }

    /// @inheritdoc IiDEBT
    function heartbeat(uint256 tokenId) external override whenNotPaused {
        Position storage p = _positions[tokenId];
        if (p.holder != msg.sender) revert NotHolder();
        p.lastHeartbeat = uint64(block.timestamp);
        emit HeartbeatRecorded(tokenId, uint64(block.timestamp));
    }

    /// @inheritdoc IiDEBT
    function service(uint256 tokenId, uint256 amount) external override whenNotPaused nonReentrant {
        Position storage p = _positions[tokenId];
        require(p.principal != 0, "no position");
        require(amount > 0 && amount <= p.principal, "bad amount");
        settlementToken.safeTransferFrom(msg.sender, address(this), amount);
        unchecked { p.principal -= amount; }
        emit DebtServiced(tokenId, amount, msg.sender);
    }

    // -------------------------------------------------------------- //
    //                         MARK-TO-MARKET                         //
    // -------------------------------------------------------------- //

    /// @inheritdoc IiDEBT
    /// @dev     Position value shrinks as stress rises relative to the mint
    ///          stressMark, and grows as stress falls. Formula:
    ///             mtm = principal * (1 - Δstress)    clamped to [0, 2x principal]
    ///          where Δstress = score_now - stressMark (signed in WAD).
    function markToMarket(uint256 tokenId) public view returns (uint256) {
        Position memory p = _positions[tokenId];
        if (p.principal == 0) return 0;
        uint256 now_ = stressIndex.score();
        int256 delta = int256(now_) - int256(p.stressMark);
        int256 factor = int256(1e18) - delta;
        if (factor <= 0) return 0;
        uint256 mtm = DebtMath.wmul(p.principal, uint256(factor));
        uint256 cap = p.principal * 2;
        return mtm > cap ? cap : mtm;
    }

    // -------------------------------------------------------------- //
    //                       CLOSE / INHERITANCE                      //
    // -------------------------------------------------------------- //

    /// @inheritdoc IiDEBT
    function close(uint256 tokenId) external override whenNotPaused nonReentrant returns (uint256 payout) {
        Position storage p = _positions[tokenId];
        if (p.holder != msg.sender) revert NotHolder();
        if (block.timestamp < p.maturity) revert NotMatured();

        payout = markToMarket(tokenId);
        uint256 remaining = p.principal;

        // Wipe position before transfer to prevent reentrancy replay.
        delete _positions[tokenId];
        delete _heirRoot[tokenId];
        delete _heirCount[tokenId];
        _burn(tokenId);

        // Settle from contract treasury; if MTM > principal we pay only
        // principal (upside captured by DAIO reserve), if MTM < principal the
        // holder absorbs the loss.
        uint256 send = payout > remaining ? remaining : payout;
        if (send > 0) settlementToken.safeTransfer(msg.sender, send);
        emit PositionClosed(tokenId, msg.sender, send);
    }

    /// @inheritdoc IiDEBT
    /// @dev Heir proof encoding (abi-encoded):
    ///        (address successor, uint16 sharesBps, bytes32[] merkleProof)
    ///      The leaf is keccak256(abi.encode(successor, sharesBps)).
    function claimInheritance(uint256 tokenId, bytes calldata heirProof)
        external
        override
        whenNotPaused
        nonReentrant
        returns (uint256 payout)
    {
        Position storage p = _positions[tokenId];
        require(p.principal != 0, "no position");
        if (block.timestamp < p.lastHeartbeat + p.dormancy) revert NotDormant();
        _ensurePaid(SCOPE_CLAIM);

        (address successor, uint16 sharesBps, bytes32[] memory proof) =
            abi.decode(heirProof, (address, uint16, bytes32[]));
        if (successor != msg.sender) revert NotHolder();

        bytes32 leaf = keccak256(abi.encode(successor, sharesBps));
        if (!MerkleProof.verify(proof, _heirRoot[tokenId], leaf)) revert InvalidHeirs();
        if (_claimed[tokenId][leaf]) revert InvalidHeirs();
        _claimed[tokenId][leaf] = true;

        // Compute this heir's payout share from mark-to-market.
        uint256 mtm = markToMarket(tokenId);
        payout = (mtm * sharesBps) / 10_000;
        // Reduce principal by the share so subsequent heirs draw on remainder.
        uint256 principalShare = (p.principal * sharesBps) / 10_000;
        p.principal = p.principal > principalShare ? p.principal - principalShare : 0;

        if (payout > 0) settlementToken.safeTransfer(successor, payout);
        emit InheritanceClaimed(tokenId, successor, sharesBps);

        // If the last heir just claimed, burn the NFT.
        if (p.principal == 0) {
            address holder = p.holder;
            delete _positions[tokenId];
            delete _heirRoot[tokenId];
            delete _heirCount[tokenId];
            _burn(tokenId);
            emit PositionClosed(tokenId, holder, 0);
        }
    }

    // -------------------------------------------------------------- //
    //                              VIEWS                             //
    // -------------------------------------------------------------- //

    function positionOf(uint256 tokenId) external view returns (Position memory) {
        return _positions[tokenId];
    }

    function heirRootOf(uint256 tokenId) external view returns (bytes32) {
        return _heirRoot[tokenId];
    }

    function supportsInterface(bytes4 id) public view override(ERC721, AccessControl) returns (bool) {
        return super.supportsInterface(id);
    }

    // -------------------------------------------------------------- //
    //                          INTERNALS                             //
    // -------------------------------------------------------------- //

    function _ensurePaid(bytes32 scope) internal view {
        if (address(x402) == address(0)) return;
        if (!x402.hasPaid(msg.sender, scope)) revert PaymentRequired();
    }

    /// @dev Keep the holder pointer in sync when the NFT is transferred. ERC721
    ///      `_update` is the post-Cancun hook that runs on every mint/transfer/burn.
    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address from)
    {
        from = super._update(to, tokenId, auth);
        // Only refresh holder on live positions (not on burn).
        if (to != address(0) && _positions[tokenId].principal != 0) {
            _positions[tokenId].holder        = to;
            _positions[tokenId].lastHeartbeat = uint64(block.timestamp);
        }
    }
}
