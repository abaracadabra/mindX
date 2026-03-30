// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Snapshot.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ERC20Extended
 * @notice Comprehensive ERC20 implementation with all modern extensions
 * @dev Combines ERC20 with permit, voting, snapshots, burning, pausing, and role-based access
 */
contract ERC20Extended is
    ERC20,
    ERC20Permit,
    ERC20Votes,
    ERC20Snapshot,
    ERC20Burnable,
    ERC20Pausable,
    AccessControl,
    ReentrancyGuard
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant SNAPSHOT_ROLE = keccak256("SNAPSHOT_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant BLACKLIST_ROLE = keccak256("BLACKLIST_ROLE");

    // Blacklist functionality
    mapping(address => bool) private _blacklisted;

    // Supply controls
    uint256 private _maxSupply;
    bool private _hasMaxSupply;

    // Fee mechanism
    struct FeeConfig {
        uint256 transferFee;        // BPS (10000 = 100%)
        uint256 mintFee;           // BPS
        uint256 burnFee;           // BPS
        address feeRecipient;
        bool feesEnabled;
    }

    FeeConfig public feeConfig;

    // Events
    event MaxSupplySet(uint256 maxSupply);
    event BlacklistUpdated(address indexed account, bool blacklisted);
    event FeeConfigUpdated(uint256 transferFee, uint256 mintFee, uint256 burnFee, address feeRecipient);
    event FeesCollected(address indexed from, address indexed to, uint256 amount, string feeType);

    /**
     * @notice Initialize ERC20Extended with full configuration
     * @param name Token name
     * @param symbol Token symbol
     * @param initialSupply Initial token supply
     * @param maxSupply Maximum token supply (0 = no limit)
     * @param admin Address to receive admin role
     */
    constructor(
        string memory name,
        string memory symbol,
        uint256 initialSupply,
        uint256 maxSupply,
        address admin
    ) ERC20(name, symbol) ERC20Permit(name) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);
        _grantRole(SNAPSHOT_ROLE, admin);
        _grantRole(BURNER_ROLE, admin);
        _grantRole(BLACKLIST_ROLE, admin);

        if (maxSupply > 0) {
            _maxSupply = maxSupply;
            _hasMaxSupply = true;
            emit MaxSupplySet(maxSupply);
        }

        if (initialSupply > 0) {
            _mint(admin, initialSupply);
        }
    }

    /**
     * @notice Mint tokens to account
     * @param to Address to mint to
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(!_blacklisted[to], "Cannot mint to blacklisted address");

        if (_hasMaxSupply) {
            require(totalSupply() + amount <= _maxSupply, "Exceeds maximum supply");
        }

        uint256 mintAmount = amount;
        uint256 feeAmount = 0;

        // Apply mint fee if enabled
        if (feeConfig.feesEnabled && feeConfig.mintFee > 0) {
            feeAmount = (amount * feeConfig.mintFee) / 10000;
            mintAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                _mint(feeConfig.feeRecipient, feeAmount);
                emit FeesCollected(address(0), feeConfig.feeRecipient, feeAmount, "MINT");
            }
        }

        _mint(to, mintAmount);
    }

    /**
     * @notice Burn tokens from account
     * @param from Address to burn from
     * @param amount Amount to burn
     */
    function burnFrom(address from, uint256 amount) public onlyRole(BURNER_ROLE) {
        require(from != address(0), "Cannot burn from zero address");

        uint256 burnAmount = amount;
        uint256 feeAmount = 0;

        // Apply burn fee if enabled
        if (feeConfig.feesEnabled && feeConfig.burnFee > 0) {
            feeAmount = (amount * feeConfig.burnFee) / 10000;
            burnAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                _transfer(from, feeConfig.feeRecipient, feeAmount);
                emit FeesCollected(from, feeConfig.feeRecipient, feeAmount, "BURN");
            }
        }

        _burn(from, burnAmount);
    }

    /**
     * @notice Create snapshot of token balances
     * @return Snapshot ID
     */
    function snapshot() public onlyRole(SNAPSHOT_ROLE) returns (uint256) {
        return _snapshot();
    }

    /**
     * @notice Pause token transfers
     */
    function pause() public onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause token transfers
     */
    function unpause() public onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @notice Add/remove address from blacklist
     * @param account Address to blacklist
     * @param blacklisted Whether to blacklist or unblacklist
     */
    function setBlacklist(address account, bool blacklisted) public onlyRole(BLACKLIST_ROLE) {
        _blacklisted[account] = blacklisted;
        emit BlacklistUpdated(account, blacklisted);
    }

    /**
     * @notice Check if address is blacklisted
     * @param account Address to check
     * @return Whether address is blacklisted
     */
    function isBlacklisted(address account) public view returns (bool) {
        return _blacklisted[account];
    }

    /**
     * @notice Configure fee structure
     * @param transferFee Transfer fee in BPS
     * @param mintFee Mint fee in BPS
     * @param burnFee Burn fee in BPS
     * @param feeRecipient Address to receive fees
     * @param enabled Whether fees are enabled
     */
    function setFeeConfig(
        uint256 transferFee,
        uint256 mintFee,
        uint256 burnFee,
        address feeRecipient,
        bool enabled
    ) public onlyRole(DEFAULT_ADMIN_ROLE) {
        require(transferFee <= 1000, "Transfer fee too high"); // Max 10%
        require(mintFee <= 1000, "Mint fee too high");         // Max 10%
        require(burnFee <= 1000, "Burn fee too high");         // Max 10%

        feeConfig = FeeConfig({
            transferFee: transferFee,
            mintFee: mintFee,
            burnFee: burnFee,
            feeRecipient: feeRecipient,
            feesEnabled: enabled
        });

        emit FeeConfigUpdated(transferFee, mintFee, burnFee, feeRecipient);
    }

    /**
     * @notice Get maximum supply
     * @return Maximum supply (0 if unlimited)
     */
    function maxSupply() public view returns (uint256) {
        return _hasMaxSupply ? _maxSupply : 0;
    }

    /**
     * @notice Check if token has maximum supply limit
     * @return Whether token has supply limit
     */
    function hasMaxSupply() public view returns (bool) {
        return _hasMaxSupply;
    }

    // Required overrides for multiple inheritance

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Snapshot, ERC20Pausable) {
        require(!_blacklisted[from], "Sender is blacklisted");
        require(!_blacklisted[to], "Recipient is blacklisted");

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

    function transfer(
        address to,
        uint256 amount
    ) public override nonReentrant whenNotPaused returns (bool) {
        address from = _msgSender();

        uint256 transferAmount = amount;
        uint256 feeAmount = 0;

        // Apply transfer fee if enabled
        if (feeConfig.feesEnabled && feeConfig.transferFee > 0) {
            feeAmount = (amount * feeConfig.transferFee) / 10000;
            transferAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                _transfer(from, feeConfig.feeRecipient, feeAmount);
                emit FeesCollected(from, feeConfig.feeRecipient, feeAmount, "TRANSFER");
            }
        }

        _transfer(from, to, transferAmount);
        return true;
    }

    function transferFrom(
        address from,
        address to,
        uint256 amount
    ) public override nonReentrant whenNotPaused returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);

        uint256 transferAmount = amount;
        uint256 feeAmount = 0;

        // Apply transfer fee if enabled
        if (feeConfig.feesEnabled && feeConfig.transferFee > 0) {
            feeAmount = (amount * feeConfig.transferFee) / 10000;
            transferAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                _transfer(from, feeConfig.feeRecipient, feeAmount);
                emit FeesCollected(from, feeConfig.feeRecipient, feeAmount, "TRANSFER");
            }
        }

        _transfer(from, to, transferAmount);
        return true;
    }

    // Support for ERC165
    function supportsInterface(bytes4 interfaceId) public view override(AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}