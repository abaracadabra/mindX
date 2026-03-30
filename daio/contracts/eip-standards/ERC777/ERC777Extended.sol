// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC777/ERC777.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/introspection/IERC1820Registry.sol";

/**
 * @title ERC777Extended
 * @notice Comprehensive ERC777 implementation with operators, hooks, and advanced features
 * @dev Advanced fungible token with send/receive hooks and operator functionality
 */
contract ERC777Extended is ERC777, AccessControl, ReentrancyGuard {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant OPERATOR_MANAGER_ROLE = keccak256("OPERATOR_MANAGER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

    // ERC1820 Registry
    IERC1820Registry private _erc1820 = IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);

    // Token configuration
    bool private _paused;
    mapping(address => bool) private _blacklisted;
    mapping(address => bool) private _authorizedOperators;

    // Hook configuration
    mapping(address => bool) private _sendHookEnabled;
    mapping(address => bool) private _receiveHookEnabled;

    // Transfer restrictions
    mapping(address => uint256) private _transferLimits;
    mapping(address => uint256) private _lastTransferTime;
    mapping(address => uint256) private _transferAmountInPeriod;
    uint256 private _globalTransferLimit;
    uint256 private _transferPeriod = 86400; // 24 hours

    // Fee mechanism
    struct FeeConfig {
        uint256 transferFee;        // BPS (10000 = 100%)
        uint256 burnFee;           // BPS
        address feeRecipient;
        bool feesEnabled;
    }

    FeeConfig public feeConfig;

    // Events
    event Paused();
    event Unpaused();
    event BlacklistUpdated(address indexed account, bool blacklisted);
    event AuthorizedOperatorAdded(address indexed operator);
    event AuthorizedOperatorRemoved(address indexed operator);
    event TransferLimitSet(address indexed account, uint256 limit);
    event HookConfigured(address indexed account, bool sendHook, bool receiveHook);
    event FeeConfigUpdated(uint256 transferFee, uint256 burnFee, address feeRecipient);
    event FeesCollected(address indexed from, uint256 amount, string feeType);

    modifier whenNotPaused() {
        require(!_paused, "Token transfers are paused");
        _;
    }

    modifier notBlacklisted(address account) {
        require(!_blacklisted[account], "Account is blacklisted");
        _;
    }

    /**
     * @notice Initialize ERC777Extended
     * @param name Token name
     * @param symbol Token symbol
     * @param defaultOperators Default operators
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        address[] memory defaultOperators,
        address admin
    ) ERC777(name, symbol, defaultOperators) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(BURNER_ROLE, admin);
        _grantRole(OPERATOR_MANAGER_ROLE, admin);
        _grantRole(PAUSER_ROLE, admin);

        // Initialize default operators as authorized
        for (uint256 i = 0; i < defaultOperators.length; i++) {
            _authorizedOperators[defaultOperators[i]] = true;
        }

        // Set default global transfer limit (10% of total supply)
        _globalTransferLimit = type(uint256).max / 10;
    }

    /**
     * @notice Mint tokens to address
     * @param to Address to mint to
     * @param amount Amount to mint
     * @param userData Additional user data
     * @param operatorData Additional operator data
     */
    function mint(
        address to,
        uint256 amount,
        bytes memory userData,
        bytes memory operatorData
    ) public onlyRole(MINTER_ROLE) notBlacklisted(to) {
        require(to != address(0), "Cannot mint to zero address");
        require(amount > 0, "Amount must be greater than 0");

        _mint(to, amount, userData, operatorData);
    }

    /**
     * @notice Burn tokens from address
     * @param account Address to burn from
     * @param amount Amount to burn
     * @param userData Additional user data
     * @param operatorData Additional operator data
     */
    function burnFrom(
        address account,
        uint256 amount,
        bytes memory userData,
        bytes memory operatorData
    ) public onlyRole(BURNER_ROLE) {
        require(account != address(0), "Cannot burn from zero address");
        require(amount > 0, "Amount must be greater than 0");

        uint256 burnAmount = amount;
        uint256 feeAmount = 0;

        // Apply burn fee if enabled
        if (feeConfig.feesEnabled && feeConfig.burnFee > 0) {
            feeAmount = (amount * feeConfig.burnFee) / 10000;
            burnAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                _send(account, feeConfig.feeRecipient, feeAmount, userData, operatorData, false);
                emit FeesCollected(account, feeAmount, "BURN");
            }
        }

        _burn(account, burnAmount, userData, operatorData);
    }

    /**
     * @notice Send tokens with hooks
     * @param recipient Recipient address
     * @param amount Amount to send
     * @param data Additional data
     */
    function send(
        address recipient,
        uint256 amount,
        bytes memory data
    ) public override whenNotPaused notBlacklisted(msg.sender) notBlacklisted(recipient) nonReentrant {
        _checkTransferLimit(msg.sender, amount);

        uint256 transferAmount = amount;
        uint256 feeAmount = 0;

        // Apply transfer fee if enabled
        if (feeConfig.feesEnabled && feeConfig.transferFee > 0) {
            feeAmount = (amount * feeConfig.transferFee) / 10000;
            transferAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                super.send(feeConfig.feeRecipient, feeAmount, "");
                emit FeesCollected(msg.sender, feeAmount, "TRANSFER");
            }
        }

        super.send(recipient, transferAmount, data);
    }

    /**
     * @notice Operator send tokens
     * @param sender Sender address
     * @param recipient Recipient address
     * @param amount Amount to send
     * @param data Additional data
     * @param operatorData Operator data
     */
    function operatorSend(
        address sender,
        address recipient,
        uint256 amount,
        bytes memory data,
        bytes memory operatorData
    ) public override whenNotPaused notBlacklisted(sender) notBlacklisted(recipient) nonReentrant {
        require(_authorizedOperators[msg.sender] || isOperatorFor(msg.sender, sender), "Not authorized operator");

        _checkTransferLimit(sender, amount);

        uint256 transferAmount = amount;
        uint256 feeAmount = 0;

        // Apply transfer fee if enabled
        if (feeConfig.feesEnabled && feeConfig.transferFee > 0) {
            feeAmount = (amount * feeConfig.transferFee) / 10000;
            transferAmount = amount - feeAmount;

            if (feeAmount > 0 && feeConfig.feeRecipient != address(0)) {
                _send(sender, feeConfig.feeRecipient, feeAmount, data, operatorData, true);
                emit FeesCollected(sender, feeAmount, "TRANSFER");
            }
        }

        super.operatorSend(sender, recipient, transferAmount, data, operatorData);
    }

    /**
     * @notice Pause token transfers
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        _paused = true;
        emit Paused();
    }

    /**
     * @notice Unpause token transfers
     */
    function unpause() external onlyRole(PAUSER_ROLE) {
        _paused = false;
        emit Unpaused();
    }

    /**
     * @notice Add/remove address from blacklist
     * @param account Address to blacklist
     * @param blacklisted Whether to blacklist or unblacklist
     */
    function setBlacklist(address account, bool blacklisted) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _blacklisted[account] = blacklisted;
        emit BlacklistUpdated(account, blacklisted);
    }

    /**
     * @notice Add authorized operator
     * @param operator Operator address
     */
    function addAuthorizedOperator(address operator) external onlyRole(OPERATOR_MANAGER_ROLE) {
        require(operator != address(0), "Operator cannot be zero address");
        _authorizedOperators[operator] = true;
        emit AuthorizedOperatorAdded(operator);
    }

    /**
     * @notice Remove authorized operator
     * @param operator Operator address
     */
    function removeAuthorizedOperator(address operator) external onlyRole(OPERATOR_MANAGER_ROLE) {
        _authorizedOperators[operator] = false;
        emit AuthorizedOperatorRemoved(operator);
    }

    /**
     * @notice Set transfer limit for account
     * @param account Account address
     * @param limit Transfer limit per period
     */
    function setTransferLimit(address account, uint256 limit) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _transferLimits[account] = limit;
        emit TransferLimitSet(account, limit);
    }

    /**
     * @notice Set global transfer limit
     * @param limit Global transfer limit per period
     */
    function setGlobalTransferLimit(uint256 limit) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _globalTransferLimit = limit;
    }

    /**
     * @notice Set transfer period
     * @param period Transfer period in seconds
     */
    function setTransferPeriod(uint256 period) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(period > 0, "Period must be greater than 0");
        _transferPeriod = period;
    }

    /**
     * @notice Configure hooks for account
     * @param account Account address
     * @param sendHook Whether to enable send hook
     * @param receiveHook Whether to enable receive hook
     */
    function configureHooks(
        address account,
        bool sendHook,
        bool receiveHook
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _sendHookEnabled[account] = sendHook;
        _receiveHookEnabled[account] = receiveHook;
        emit HookConfigured(account, sendHook, receiveHook);
    }

    /**
     * @notice Configure fee structure
     * @param transferFee Transfer fee in BPS
     * @param burnFee Burn fee in BPS
     * @param feeRecipient Address to receive fees
     * @param enabled Whether fees are enabled
     */
    function setFeeConfig(
        uint256 transferFee,
        uint256 burnFee,
        address feeRecipient,
        bool enabled
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(transferFee <= 1000, "Transfer fee too high"); // Max 10%
        require(burnFee <= 1000, "Burn fee too high");         // Max 10%

        feeConfig = FeeConfig({
            transferFee: transferFee,
            burnFee: burnFee,
            feeRecipient: feeRecipient,
            feesEnabled: enabled
        });

        emit FeeConfigUpdated(transferFee, burnFee, feeRecipient);
    }

    /**
     * @notice Check if account is blacklisted
     * @param account Account to check
     * @return Whether account is blacklisted
     */
    function isBlacklisted(address account) external view returns (bool) {
        return _blacklisted[account];
    }

    /**
     * @notice Check if address is authorized operator
     * @param operator Operator address
     * @return Whether operator is authorized
     */
    function isAuthorizedOperator(address operator) external view returns (bool) {
        return _authorizedOperators[operator];
    }

    /**
     * @notice Check if token is paused
     * @return Whether token is paused
     */
    function paused() external view returns (bool) {
        return _paused;
    }

    /**
     * @notice Get transfer limit for account
     * @param account Account address
     * @return Transfer limit per period
     */
    function getTransferLimit(address account) external view returns (uint256) {
        uint256 accountLimit = _transferLimits[account];
        return accountLimit > 0 ? accountLimit : _globalTransferLimit;
    }

    /**
     * @notice Get remaining transfer amount for account in current period
     * @param account Account address
     * @return Remaining transfer amount
     */
    function getRemainingTransferAmount(address account) external view returns (uint256) {
        uint256 limit = _transferLimits[account];
        if (limit == 0) limit = _globalTransferLimit;

        uint256 currentPeriodStart = (block.timestamp / _transferPeriod) * _transferPeriod;

        if (_lastTransferTime[account] < currentPeriodStart) {
            return limit;
        }

        uint256 used = _transferAmountInPeriod[account];
        return limit > used ? limit - used : 0;
    }

    /**
     * @notice Batch send to multiple recipients
     * @param recipients Array of recipient addresses
     * @param amounts Array of amounts to send
     * @param data Additional data
     */
    function batchSend(
        address[] memory recipients,
        uint256[] memory amounts,
        bytes memory data
    ) external whenNotPaused notBlacklisted(msg.sender) nonReentrant {
        require(recipients.length == amounts.length, "Arrays length mismatch");
        require(recipients.length <= 50, "Too many recipients");

        uint256 totalAmount = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalAmount += amounts[i];
        }

        _checkTransferLimit(msg.sender, totalAmount);

        for (uint256 i = 0; i < recipients.length; i++) {
            require(!_blacklisted[recipients[i]], "Recipient is blacklisted");
            send(recipients[i], amounts[i], data);
        }
    }

    // Internal functions

    function _checkTransferLimit(address sender, uint256 amount) internal {
        uint256 limit = _transferLimits[sender];
        if (limit == 0) limit = _globalTransferLimit;

        if (limit == type(uint256).max) return; // No limit

        uint256 currentPeriodStart = (block.timestamp / _transferPeriod) * _transferPeriod;

        // Reset if new period
        if (_lastTransferTime[sender] < currentPeriodStart) {
            _transferAmountInPeriod[sender] = 0;
        }

        require(_transferAmountInPeriod[sender] + amount <= limit, "Transfer limit exceeded");

        _transferAmountInPeriod[sender] += amount;
        _lastTransferTime[sender] = block.timestamp;
    }

    // Hook overrides for additional functionality

    function _beforeTokenTransfer(
        address operator,
        address from,
        address to,
        uint256 amount
    ) internal override {
        // Custom send hook
        if (from != address(0) && _sendHookEnabled[from]) {
            // Custom send logic can be added here
        }

        // Custom receive hook
        if (to != address(0) && _receiveHookEnabled[to]) {
            // Custom receive logic can be added here
        }

        super._beforeTokenTransfer(operator, from, to, amount);
    }

    // Required overrides

    function supportsInterface(bytes4 interfaceId) public view override(AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}