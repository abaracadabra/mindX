// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

interface IDebtInheritanceProtocol {
    function balanceOf(address) external view returns (uint256);
    function burnSGdsi(uint256 sGdsiAmount, uint256 minStableOut) external returns (uint256);
    function sGdsiRedemptionValue() external view returns (uint256);
}

interface IInverseDebtToken {
    function mint(uint256 usdcAmount, uint256 minIDebtOut) external returns (uint256);
}

interface IDebasementIndex {
    function currentIndex() external view returns (uint256);
    function btcEquivalent(uint256 usdcAmount) external view returns (uint256 satoshis);
}

/**
 * @title BitcoinProfitRecognizer
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Routes existing sGDSI position gains directly into iDEBT exposure, preserving
 *         the Bitcoin-denominated upside of the thesis. Users approve this contract on
 *         their sGDSI, call recognizeProfit(), and the contract atomically burns their
 *         sGDSI for USDC, then immediately mints iDEBT with that USDC on their behalf.
 *
 * @dev Why not just let users do the two steps themselves? Three reasons:
 *
 *      1. Fee efficiency: doing two txs means paying gas twice and triggering two sets
 *         of mint/burn fees. The recognizer can in principle negotiate fee discounts
 *         through governance (not implemented here but architecturally enabled by the
 *         routing role grant).
 *
 *      2. Atomicity: in the round-trip, the user is temporarily exposed to USDC between
 *         burn and mint. If the debasement index moves during that window (e.g., a fast
 *         Bitcoin rally), the user loses some of their gain. The recognizer keeps the
 *         conversion atomic — one transaction, one oracle read.
 *
 *      3. Clean profit reporting: the RecognizedProfit event carries the full trail
 *         (sGDSI burned, USDC proceeds, iDEBT minted, current BTC satoshi equivalent)
 *         in a single log, which the subgraph can index as a single semantic action
 *         rather than two unrelated events.
 *
 *      The contract is stateless — it holds no funds between calls and has no privileged
 *      relationship to the protocols it routes through. It is a pure composition helper,
 *      which means it inherits the security properties of its inputs rather than adding
 *      new attack surface.
 */
contract BitcoinProfitRecognizer is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    error ZeroAddress();
    error ZeroAmount();
    error SlippageExceeded(uint256 expected, uint256 actual);

    IDebtInheritanceProtocol public immutable dip;
    IInverseDebtToken public immutable idebt;
    IDebasementIndex public immutable debasementIndex;
    IERC20 public immutable stablecoin;

    event RecognizedProfit(
        address indexed user,
        uint256 sGdsiBurned,
        uint256 usdcProceeds,
        uint256 iDebtMinted,
        uint256 btcSatoshisEquivalent,
        uint256 debasementIndexAtRecognition
    );

    constructor(
        address admin,
        address _dip,
        address _idebt,
        address _debasementIndex,
        address _stablecoin
    ) {
        if (admin == address(0) || _dip == address(0) || _idebt == address(0)
            || _debasementIndex == address(0) || _stablecoin == address(0))
            revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);

        dip = IDebtInheritanceProtocol(_dip);
        idebt = IInverseDebtToken(_idebt);
        debasementIndex = IDebasementIndex(_debasementIndex);
        stablecoin = IERC20(_stablecoin);
    }

    /*//////////////////////////////////////////////////////////////
                     PROFIT RECOGNITION FLOW
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Atomically burn sGDSI for USDC and mint iDEBT with the proceeds.
     *         The user must have pre-approved this contract on sGDSI for `sGdsiAmount`
     *         and must have transferred the sGDSI tokens to this contract. The
     *         simplest call pattern: approve + transferFrom + this call. To make it
     *         one-step, integrators can use permit or a wrapper.
     *
     * @param sGdsiAmount Amount of sGDSI to burn (this contract must hold them).
     * @param minUsdcFromBurn Slippage floor on the burn step.
     * @param minIDebtFromMint Slippage floor on the mint step.
     */
    function recognizeProfit(
        uint256 sGdsiAmount,
        uint256 minUsdcFromBurn,
        uint256 minIDebtFromMint
    ) external nonReentrant whenNotPaused returns (uint256 iDebtOut) {
        if (sGdsiAmount == 0) revert ZeroAmount();

        // Step 1: pull sGDSI from the user.
        IERC20(address(dip)).safeTransferFrom(msg.sender, address(this), sGdsiAmount);

        // Step 2: burn sGDSI for USDC. Output goes to this contract.
        uint256 usdcBefore = stablecoin.balanceOf(address(this));
        uint256 stableOut = dip.burnSGdsi(sGdsiAmount, minUsdcFromBurn);
        uint256 usdcAfter = stablecoin.balanceOf(address(this));
        uint256 proceeds = usdcAfter - usdcBefore;
        require(proceeds >= minUsdcFromBurn, "proceeds below floor");
        require(proceeds == stableOut, "burn accounting mismatch");

        // Step 3: approve iDEBT contract to pull USDC and mint to this contract.
        stablecoin.forceApprove(address(idebt), proceeds);
        iDebtOut = idebt.mint(proceeds, minIDebtFromMint);

        // Step 4: forward iDEBT to the user.
        IERC20(address(idebt)).safeTransfer(msg.sender, iDebtOut);

        // Step 5: emit the composite event.
        uint256 btcSats = debasementIndex.btcEquivalent(proceeds);
        uint256 idx = debasementIndex.currentIndex();
        emit RecognizedProfit(msg.sender, sGdsiAmount, proceeds, iDebtOut, btcSats, idx);
    }

    /**
     * @notice Simpler route for users starting from USDC who want to skip the sGDSI
     *         intermediate step but still want the event to show through the recognizer
     *         for indexing consistency. Just mints iDEBT directly with the user's USDC.
     */
    function recognizeDirect(uint256 usdcAmount, uint256 minIDebtOut)
        external nonReentrant whenNotPaused returns (uint256 iDebtOut)
    {
        if (usdcAmount == 0) revert ZeroAmount();
        stablecoin.safeTransferFrom(msg.sender, address(this), usdcAmount);
        stablecoin.forceApprove(address(idebt), usdcAmount);
        iDebtOut = idebt.mint(usdcAmount, minIDebtOut);
        IERC20(address(idebt)).safeTransfer(msg.sender, iDebtOut);

        uint256 btcSats = debasementIndex.btcEquivalent(usdcAmount);
        uint256 idx = debasementIndex.currentIndex();
        emit RecognizedProfit(msg.sender, 0, usdcAmount, iDebtOut, btcSats, idx);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
