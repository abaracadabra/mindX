// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Wrapper.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title ERC20Wrapper
 * @notice Wrap existing ERC20 tokens with additional functionality
 * @dev Wraps any ERC20 token and adds governance, permit, and additional features
 */
contract ERC20WrapperToken is
    ERC20,
    ERC20Wrapper,
    ERC20Permit,
    ERC20Votes,
    AccessControl,
    ReentrancyGuard
{
    using SafeERC20 for IERC20;

    bytes32 public constant WRAPPER_ADMIN_ROLE = keccak256("WRAPPER_ADMIN_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    // Wrapper configuration
    struct WrapperConfig {
        uint256 depositFee;         // Fee for depositing (BPS)
        uint256 withdrawFee;        // Fee for withdrawing (BPS)
        address feeRecipient;       // Address to receive fees
        bool feesEnabled;           // Whether fees are enabled
        bool emergencyWithdraw;     // Emergency withdrawal enabled
    }

    WrapperConfig public wrapperConfig;
    bool public paused;

    // Emergency withdrawal tracking
    mapping(address => bool) public emergencyWithdrawn;

    // Events
    event WrapperConfigUpdated(uint256 depositFee, uint256 withdrawFee, address feeRecipient, bool feesEnabled);
    event EmergencyWithdrawEnabled(bool enabled);
    event EmergencyWithdrawal(address indexed user, uint256 amount);
    event FeeCollected(address indexed from, uint256 amount, string feeType);

    modifier whenNotPaused() {
        require(!paused, "Wrapper is paused");
        _;
    }

    /**
     * @notice Initialize wrapper for existing ERC20 token
     * @param underlyingToken Address of token to wrap
     * @param name Wrapper token name
     * @param symbol Wrapper token symbol
     * @param admin Admin address
     */
    constructor(
        IERC20 underlyingToken,
        string memory name,
        string memory symbol,
        address admin
    )
        ERC20(name, symbol)
        ERC20Wrapper(underlyingToken)
        ERC20Permit(name)
    {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(WRAPPER_ADMIN_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);

        // Initialize with no fees
        wrapperConfig = WrapperConfig({
            depositFee: 0,
            withdrawFee: 0,
            feeRecipient: admin,
            feesEnabled: false,
            emergencyWithdraw: false
        });
    }

    /**
     * @notice Deposit underlying tokens and mint wrapped tokens
     * @param amount Amount to deposit
     * @return Amount of wrapped tokens minted
     */
    function deposit(uint256 amount) public nonReentrant whenNotPaused returns (uint256) {
        require(amount > 0, "Amount must be greater than 0");

        uint256 depositAmount = amount;
        uint256 feeAmount = 0;

        // Calculate and collect deposit fee
        if (wrapperConfig.feesEnabled && wrapperConfig.depositFee > 0) {
            feeAmount = (amount * wrapperConfig.depositFee) / 10000;
            depositAmount = amount - feeAmount;

            if (feeAmount > 0 && wrapperConfig.feeRecipient != address(0)) {
                underlying().safeTransferFrom(msg.sender, wrapperConfig.feeRecipient, feeAmount);
                emit FeeCollected(msg.sender, feeAmount, "DEPOSIT");
            }
        }

        // Transfer underlying tokens to wrapper
        underlying().safeTransferFrom(msg.sender, address(this), depositAmount);

        // Mint wrapped tokens (1:1 ratio)
        _mint(msg.sender, depositAmount);

        return depositAmount;
    }

    /**
     * @notice Withdraw underlying tokens by burning wrapped tokens
     * @param amount Amount of wrapped tokens to burn
     * @return Amount of underlying tokens returned
     */
    function withdraw(uint256 amount) public nonReentrant whenNotPaused returns (uint256) {
        require(amount > 0, "Amount must be greater than 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient wrapped token balance");

        uint256 withdrawAmount = amount;
        uint256 feeAmount = 0;

        // Calculate and collect withdrawal fee
        if (wrapperConfig.feesEnabled && wrapperConfig.withdrawFee > 0) {
            feeAmount = (amount * wrapperConfig.withdrawFee) / 10000;
            withdrawAmount = amount - feeAmount;

            // Burn fee portion without returning underlying
            if (feeAmount > 0) {
                _burn(msg.sender, feeAmount);
                emit FeeCollected(msg.sender, feeAmount, "WITHDRAW");
            }
        }

        // Burn wrapped tokens and return underlying
        _burn(msg.sender, withdrawAmount);
        underlying().safeTransfer(msg.sender, withdrawAmount);

        return withdrawAmount;
    }

    /**
     * @notice Emergency withdrawal function (bypasses normal fees)
     * @param amount Amount of wrapped tokens to emergency withdraw
     */
    function emergencyWithdraw(uint256 amount) external nonReentrant {
        require(wrapperConfig.emergencyWithdraw, "Emergency withdrawal not enabled");
        require(!emergencyWithdrawn[msg.sender], "Emergency withdrawal already used");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");

        emergencyWithdrawn[msg.sender] = true;

        // Emergency withdrawal bypasses fees and returns underlying 1:1
        _burn(msg.sender, amount);
        underlying().safeTransfer(msg.sender, amount);

        emit EmergencyWithdrawal(msg.sender, amount);
    }

    /**
     * @notice Configure wrapper fees and settings
     * @param depositFee Deposit fee in BPS
     * @param withdrawFee Withdrawal fee in BPS
     * @param feeRecipient Address to receive fees
     * @param feesEnabled Whether fees are enabled
     */
    function setWrapperConfig(
        uint256 depositFee,
        uint256 withdrawFee,
        address feeRecipient,
        bool feesEnabled
    ) external onlyRole(WRAPPER_ADMIN_ROLE) {
        require(depositFee <= 1000, "Deposit fee too high"); // Max 10%
        require(withdrawFee <= 1000, "Withdraw fee too high"); // Max 10%

        wrapperConfig = WrapperConfig({
            depositFee: depositFee,
            withdrawFee: withdrawFee,
            feeRecipient: feeRecipient,
            feesEnabled: feesEnabled,
            emergencyWithdraw: wrapperConfig.emergencyWithdraw // Keep existing setting
        });

        emit WrapperConfigUpdated(depositFee, withdrawFee, feeRecipient, feesEnabled);
    }

    /**
     * @notice Enable/disable emergency withdrawal
     * @param enabled Whether emergency withdrawal is enabled
     */
    function setEmergencyWithdraw(bool enabled) external onlyRole(DEFAULT_ADMIN_ROLE) {
        wrapperConfig.emergencyWithdraw = enabled;
        emit EmergencyWithdrawEnabled(enabled);
    }

    /**
     * @notice Pause wrapper operations
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        paused = true;
    }

    /**
     * @notice Unpause wrapper operations
     */
    function unpause() external onlyRole(PAUSER_ROLE) {
        paused = false;
    }

    /**
     * @notice Get exchange rate (should always be 1:1 for this implementation)
     * @return Exchange rate in underlying token per wrapped token
     */
    function exchangeRate() public pure returns (uint256) {
        return 1e18; // 1:1 exchange rate
    }

    /**
     * @notice Get total value locked in wrapper
     * @return Total underlying tokens locked
     */
    function totalValueLocked() public view returns (uint256) {
        return underlying().balanceOf(address(this));
    }

    /**
     * @notice Check if user has used emergency withdrawal
     * @param user User address
     * @return Whether user has used emergency withdrawal
     */
    function hasUsedEmergencyWithdraw(address user) external view returns (bool) {
        return emergencyWithdrawn[user];
    }

    // Required overrides

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        super._beforeTokenTransfer(from, to, amount);
    }

    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
    }

    function _mint(
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._mint(to, amount);
    }

    function _burn(
        address account,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._burn(account, amount);
    }

    function supportsInterface(bytes4 interfaceId) public view override(AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // Batch operations for gas efficiency

    /**
     * @notice Batch deposit for multiple amounts
     * @param amounts Array of amounts to deposit
     * @return Array of wrapped tokens minted
     */
    function batchDeposit(uint256[] calldata amounts) external returns (uint256[] memory) {
        uint256[] memory results = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            results[i] = deposit(amounts[i]);
        }
        return results;
    }

    /**
     * @notice Batch withdraw for multiple amounts
     * @param amounts Array of wrapped token amounts to withdraw
     * @return Array of underlying tokens returned
     */
    function batchWithdraw(uint256[] calldata amounts) external returns (uint256[] memory) {
        uint256[] memory results = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            results[i] = withdraw(amounts[i]);
        }
        return results;
    }
}