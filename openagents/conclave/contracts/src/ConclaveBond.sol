// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IConclaveBond} from "./interfaces/IConclaveBond.sol";

/// @title ConclaveBond
/// @notice EVM honor-stake module. Members lock native value (or, in a
///         later version, an ERC20 like PAI) before being seated. The
///         Conclave contract may slash a leaker's bond.
///
///         An x402 / Algorand path is supported by setting `algoBridge`:
///         when nonzero, `postBond` may be called with a single 32-byte
///         Algorand txid in `extraData` to attest a stake on Algorand.
///         The slash path on the Algorand side is handled by the
///         parsec-wallet relayer subscribing to `MemberSlashed` events.
contract ConclaveBond is IConclaveBond {
    address public immutable conclave;     // the Conclave contract
    address public immutable algoBridge;   // optional x402/Algorand relayer

    // conclave_id => member => locked amount (wei)
    mapping(bytes32 => mapping(address => uint256)) private _bonds;
    // conclave_id => member => Algorand txid (if posted via bridge)
    mapping(bytes32 => mapping(address => bytes32)) public algorandTxOf;

    // window after which a non-slashed member can release their bond
    uint64 public constant RELEASE_DELAY = 30 days;
    // conclave_id => member => earliest release time
    mapping(bytes32 => mapping(address => uint64)) public releasableAt;

    error NotConclave();
    error NoBond();
    error TooEarly();
    error TransferFailed();

    event BondPosted(bytes32 indexed conclave_id, address indexed member,
                     uint256 amount, bytes32 algoTxid);
    event BondReleased(bytes32 indexed conclave_id, address indexed member,
                       uint256 amount);
    event BondSlashed(bytes32 indexed conclave_id, address indexed member,
                      uint256 amount);

    constructor(address conclave_, address algoBridge_) {
        conclave = conclave_;
        algoBridge = algoBridge_;
    }

    // ---------- views ---------- //

    function bondOf(bytes32 conclave_id, address member)
        external
        view
        returns (uint256)
    {
        return _bonds[conclave_id][member];
    }

    // ---------- post / release ---------- //

    /// @inheritdoc IConclaveBond
    /// @dev `extraData` is empty for native posts, or a 32-byte Algorand
    ///      txid (left-padded) for cross-chain attestation by the bridge.
    function postBond(bytes32 conclave_id, uint256 amount) external payable {
        require(amount > 0, "ConclaveBond: zero amount");
        require(msg.value == amount, "ConclaveBond: value mismatch");
        _bonds[conclave_id][msg.sender] += amount;
        releasableAt[conclave_id][msg.sender] =
            uint64(block.timestamp) + RELEASE_DELAY;
        emit BondPosted(conclave_id, msg.sender, amount, bytes32(0));
    }

    /// @notice Bridge-only: attest that `member` has staked `amount`
    ///         worth of PAI on Algorand under txid `algoTxid`. The bridge
    ///         operator (parsec-wallet relayer) is trusted to verify the
    ///         Algorand-side stake before calling this.
    function attestAlgorandBond(
        bytes32 conclave_id,
        address member,
        uint256 amount,
        bytes32 algoTxid
    ) external {
        require(msg.sender == algoBridge, "ConclaveBond: not bridge");
        _bonds[conclave_id][member] += amount;
        algorandTxOf[conclave_id][member] = algoTxid;
        releasableAt[conclave_id][member] =
            uint64(block.timestamp) + RELEASE_DELAY;
        emit BondPosted(conclave_id, member, amount, algoTxid);
    }

    /// @inheritdoc IConclaveBond
    function releaseBond(bytes32 conclave_id) external {
        uint256 amt = _bonds[conclave_id][msg.sender];
        if (amt == 0) revert NoBond();
        if (block.timestamp < releasableAt[conclave_id][msg.sender]) {
            revert TooEarly();
        }
        _bonds[conclave_id][msg.sender] = 0;
        // Native path. Algorand-attested bonds release via the bridge.
        if (algorandTxOf[conclave_id][msg.sender] == bytes32(0)) {
            (bool ok, ) = msg.sender.call{value: amt}("");
            if (!ok) revert TransferFailed();
        }
        emit BondReleased(conclave_id, msg.sender, amt);
    }

    /// @inheritdoc IConclaveBond
    function slash(bytes32 conclave_id, address member)
        external
        returns (uint256 amount)
    {
        if (msg.sender != conclave) revert NotConclave();
        amount = _bonds[conclave_id][member];
        if (amount == 0) return 0;
        _bonds[conclave_id][member] = 0;
        // Slashed funds go to the Conclave contract for downstream
        // distribution (treasury / counter-party / burn). v0.1 forwards
        // to convener for transparency.
        (bool ok, ) = conclave.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit BondSlashed(conclave_id, member, amount);
    }

    receive() external payable {}
}
