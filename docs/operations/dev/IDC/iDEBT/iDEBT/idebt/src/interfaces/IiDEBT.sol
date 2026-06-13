// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IiDEBT
/// @notice Cryptographic Inheritance of Global DEBT.
/// @dev    Each iDEBT position is a non-fungible claim carrying:
///         - principal   : underlying debt notional (1e18)
///         - stressMark  : stress index at mint (1e18)
///         - maturity    : unix timestamp of intended expiry
///         - heirs       : ordered successors for cryptographic inheritance
///         - dormancy    : seconds of on-chain inactivity before heir can claim
interface IiDEBT {
    struct Position {
        uint256 principal;
        uint256 stressMark;
        uint64  mintedAt;
        uint64  maturity;
        uint64  lastHeartbeat;
        uint64  dormancy;
        address holder;
    }

    struct Heir {
        address successor;
        uint16  sharesBps; // basis points of the position
        bytes32 proofRoot; // commitment (e.g. PoseidonHash of heir tuple)
    }

    event PositionOpened(uint256 indexed tokenId, address indexed holder, uint256 principal);
    event PositionClosed(uint256 indexed tokenId, address indexed holder, uint256 payout);
    event HeartbeatRecorded(uint256 indexed tokenId, uint64 at);
    event HeirsConfigured(uint256 indexed tokenId, uint8 count, bytes32 rootCommit);
    event InheritanceClaimed(uint256 indexed tokenId, address indexed heir, uint256 shareBps);
    event DebtServiced(uint256 indexed tokenId, uint256 amount, address indexed payer);

    error NotHolder();
    error NotMatured();
    error NotDormant();
    error InvalidHeirs();
    error ExceedsCap();
    error PaymentRequired();

    /// @notice Open a new iDEBT position and receive an ERC-721 claim token.
    function openPosition(
        uint256 principal,
        uint64  maturity,
        uint64  dormancy,
        Heir[] calldata heirs
    ) external returns (uint256 tokenId);

    /// @notice Record a heartbeat proving the holder is alive/active.
    function heartbeat(uint256 tokenId) external;

    /// @notice Service debt for a position.
    function service(uint256 tokenId, uint256 amount) external;

    /// @notice Claim inheritance. Callable only by a registered heir after dormancy expires.
    function claimInheritance(uint256 tokenId, bytes calldata heirProof)
        external
        returns (uint256 payout);

    /// @notice Close a matured position and settle.
    function close(uint256 tokenId) external returns (uint256 payout);

    /// @notice View a position.
    function positionOf(uint256 tokenId) external view returns (Position memory);

    /// @notice Mark-to-market value of a position at the current stress index.
    function markToMarket(uint256 tokenId) external view returns (uint256);
}
