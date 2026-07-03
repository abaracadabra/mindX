// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
pragma solidity ^0.8.24;

/**
 * DatoMembership — request-to-join a dato with a fee + settings.
 *
 * The EVM analogue of dato/core/membership.py. A participant joins by paying the
 * dato's join fee (native value here; the production path settles USDC via x402 /
 * the DAIO TreasuryFeeCollector — this contract records the fee + per-member
 * settings and admits on the DatoCore). cypherpunk2048: inline owner, no proxy,
 * zero imports. Collected fees are withdrawable only by the owning DAIO (→ treasury).
 *
 * Mirrors the daio TreasuryFeeCollector fee-categorization idea with a single
 * DATO_MEMBERSHIP_FEE purpose; kept dato-local so the live contract is untouched.
 */
interface IDatoCore {
    function admitMember(address wallet, bytes32 settingsHash, uint256 feePaid) external;
    function owner() external view returns (address);
    function settings() external view returns (uint8 defaultTier, uint256 joinFeeMicroUSD, bool openJoin, uint32 maxMembers);
}

contract DatoMembership {
    address public owner;            // the owning DAIO
    IDatoCore public immutable dato;
    uint256 public joinFeeWei;       // fee in native wei (operator sets to match the dato's USD fee)
    uint256 public collected;

    mapping(address => bytes32) public memberSettings;
    mapping(address => uint256) public feePaid;

    event JoinRequested(address indexed wallet, uint256 fee, bytes32 settingsHash, string settingsURI);
    event FeeWithdrawn(address indexed to, uint256 amount);
    event JoinFeeUpdated(uint256 oldFee, uint256 newFee);

    error NotOwner();
    error FeeTooLow(uint256 required);
    error ZeroAddress();
    error TransferFailed();

    modifier onlyOwner() { if (msg.sender != owner) revert NotOwner(); _; }

    constructor(address datoCore, uint256 joinFeeWei_) {
        if (datoCore == address(0)) revert ZeroAddress();
        dato = IDatoCore(datoCore);
        owner = IDatoCore(datoCore).owner();
        joinFeeWei = joinFeeWei_;
    }

    function setJoinFee(uint256 newFeeWei) external onlyOwner {
        emit JoinFeeUpdated(joinFeeWei, newFeeWei);
        joinFeeWei = newFeeWei;
    }

    /// @notice Request to join: pay >= joinFeeWei, attach per-member settings.
    /// Records the fee + settings and admits the caller on the DatoCore.
    function requestJoin(bytes32 settingsHash, string calldata settingsURI) external payable {
        if (msg.value < joinFeeWei) revert FeeTooLow(joinFeeWei);
        collected += msg.value;
        feePaid[msg.sender] = msg.value;
        memberSettings[msg.sender] = settingsHash;
        emit JoinRequested(msg.sender, msg.value, settingsHash, settingsURI);
        // Admit on the core (this contract is set as the dato's membership manager by the owner).
        dato.admitMember(msg.sender, settingsHash, msg.value);
    }

    /// @notice The owning DAIO withdraws collected fees (→ treasury / tithe).
    function withdraw(address payable to) external onlyOwner {
        if (to == address(0)) revert ZeroAddress();
        uint256 amount = address(this).balance;
        collected = 0;
        (bool ok, ) = to.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit FeeWithdrawn(to, amount);
    }
}
