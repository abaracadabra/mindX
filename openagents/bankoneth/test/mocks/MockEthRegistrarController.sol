// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Minimal storage-backed mock of the canonical ENS
///         ETHRegistrarController (mainnet:
///         0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547). Mirrors the surface
///         BankonEthRegistrar calls: commit-reveal, rentPrice, register with
///         automatic overpayment refund, valid/available, min/max commitment
///         age. Configurable rent price + premium + availability so test
///         cases can drive branch coverage.
///
///         Not a faithful reimplementation — no actual subname write, no
///         NameWrapper integration. Just enough behaviour to exercise the
///         bankoneth wrapper's branches.
contract MockEthRegistrarController {
    uint256 public constant MIN_COMMITMENT_AGE = 60;
    uint256 public constant MAX_COMMITMENT_AGE = 86_400;

    // Per-second base price in wei. Tests configure directly.
    uint256 public basePricePerSec = 1 gwei; // 1 gwei/sec → ~0.0316 ETH/year
    uint256 public premiumWei      = 0;
    bool    public unavailable     = false;
    bool    public invalidate      = false;

    /// commitment → timestamp committed.
    mapping(bytes32 => uint256) public commitments;

    struct Registration {
        string  label;
        address owner;
        uint256 duration;
        uint256 paid;
    }
    Registration internal _last;

    function lastOwner()    external view returns (address) { return _last.owner; }
    function lastDuration() external view returns (uint256) { return _last.duration; }
    function lastPaid()     external view returns (uint256) { return _last.paid; }
    function lastLabel()    external view returns (string memory) { return _last.label; }

    // ── Admin (tests-only) ─────────────────────────────────────────

    function setBasePricePerSec(uint256 v) external { basePricePerSec = v; }
    function setPremium(uint256 v)         external { premiumWei = v; }
    function setUnavailable(bool v)        external { unavailable = v; }
    function setInvalid(bool v)            external { invalidate = v; }

    // ── ENS controller surface ─────────────────────────────────────

    function rentPrice(string calldata, uint256 duration)
        external
        view
        returns (uint256 base, uint256 premium)
    {
        return (duration * basePricePerSec, premiumWei);
    }

    function valid(string calldata name) external view returns (bool) {
        if (invalidate) return false;
        return bytes(name).length >= 3;
    }

    function available(string calldata) external view returns (bool) {
        return !unavailable;
    }

    function minCommitmentAge() external pure returns (uint256) { return MIN_COMMITMENT_AGE; }
    function maxCommitmentAge() external pure returns (uint256) { return MAX_COMMITMENT_AGE; }

    function makeCommitment(
        string calldata name,
        address owner,
        uint256 duration,
        bytes32 secret,
        address resolver,
        bytes[] calldata data,
        bool reverseRecord,
        uint16 ownerControlledFuses
    ) external pure returns (bytes32) {
        return keccak256(
            abi.encode(
                name, owner, duration, secret, resolver,
                data, reverseRecord, ownerControlledFuses
            )
        );
    }

    function commit(bytes32 commitment) external {
        commitments[commitment] = block.timestamp;
    }

    function register(
        string calldata name,
        address owner,
        uint256 duration,
        bytes32 /*secret*/,
        address /*resolver*/,
        bytes[] calldata /*data*/,
        bool /*reverseRecord*/,
        uint16 /*ownerControlledFuses*/
    ) external payable {
        uint256 cost = duration * basePricePerSec + premiumWei;
        require(msg.value >= cost, "MockEthRegistrarController: underpay");
        _last = Registration(name, owner, duration, cost);

        // Match the live controller: refund overpayment to msg.sender.
        if (msg.value > cost) {
            (bool ok, ) = payable(msg.sender).call{value: msg.value - cost}("");
            require(ok, "MockEthRegistrarController: refund failed");
        }
    }

    receive() external payable {}
}
