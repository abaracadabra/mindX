// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/utils/introspection/IERC165.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";
import "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title TokenBoundAccount
 * @dev ERC6551 Token Bound Account implementation with DAIO integration
 *
 * Features:
 * - NFTs can own and control assets
 * - Execute transactions on behalf of NFT
 * - Hierarchical ownership (NFT -> TBA -> owned assets)
 * - DAIO governance integration for corporate NFT management
 * - Constitutional constraints on TBA actions
 * - Multi-signature support for high-value NFTs
 * - Emergency controls and recovery mechanisms
 *
 * @author DAIO Development Team
 */

// ERC6551 Core Interfaces
interface IERC6551Account {
    receive() external payable;

    function token()
        external
        view
        returns (
            uint256 chainId,
            address tokenContract,
            uint256 tokenId
        );

    function state() external view returns (uint256);

    function isValidSigner(address signer, bytes calldata context)
        external
        view
        returns (bytes4 magicValue);
}

interface IERC6551Executable {
    function execute(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation
    ) external payable returns (bytes memory);
}

interface IDAIO_Constitution_Enhanced {
    function validateTokenBoundAccountAction(
        address account,
        uint256 chainId,
        address tokenContract,
        uint256 tokenId,
        address to,
        uint256 value,
        bytes calldata data
    ) external view returns (bool valid, string memory reason);
}

interface IExecutiveGovernance {
    function hasExecutiveApproval(address account) external view returns (bool);
    function hasTokenBoundAccountManagerRole(address account) external view returns (bool);
}

contract TokenBoundAccount is
    IERC165,
    IERC6551Account,
    IERC6551Executable,
    AccessControl,
    ReentrancyGuard
{
    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    bytes32 public constant GUARDIAN_ROLE = keccak256("GUARDIAN_ROLE");

    uint8 public constant OPERATION_CALL = 0;
    uint8 public constant OPERATION_DELEGATECALL = 1;
    uint8 public constant OPERATION_CREATE = 2;
    uint8 public constant OPERATION_CREATE2 = 3;

    bytes4 constant ERC6551_ACCOUNT_INTERFACE_ID = 0x6faff5f1;
    bytes4 constant ERC6551_EXECUTABLE_INTERFACE_ID = 0x51945447;

    // =============================================================
    //                         STORAGE
    // =============================================================

    // ERC6551 Core
    uint256 private _state;

    // DAIO Integration
    IDAIO_Constitution_Enhanced public immutable constitution;
    IExecutiveGovernance public immutable governance;

    // Access Control
    mapping(address => bool) public authorizedOperators;
    mapping(address => bool) public emergencyContacts;

    // Multi-signature for high-value operations
    struct MultisigConfig {
        bool enabled;
        uint256 threshold;
        address[] signers;
        mapping(address => bool) isSigner;
    }
    MultisigConfig public multisigConfig;

    // Transaction limits and controls
    uint256 public dailyTransactionLimit;
    uint256 public dailyValueLimit;
    uint256 public totalValueTransferredToday;
    uint256 public transactionCountToday;
    uint256 public lastResetDay;

    // Emergency controls
    bool public locked;
    uint256 public lockUntil;

    // Asset management
    struct AssetManager {
        bool canManageERC20;
        bool canManageERC721;
        bool canManageERC1155;
        bool canManageEther;
        uint256[] allowedTokenIds; // For ERC721/ERC1155 restrictions
        mapping(uint256 => bool) isAllowedTokenId;
        address[] allowedContracts;
        mapping(address => bool) isAllowedContract;
    }

    mapping(address => AssetManager) public assetManagers;

    // Events
    event TokenBoundAccountCreated(uint256 chainId, address tokenContract, uint256 tokenId);
    event Executed(address indexed to, uint256 value, bytes data, uint8 operation, bytes result);
    event OperatorAuthorized(address indexed operator, bool authorized);
    event MultisigConfigured(bool enabled, uint256 threshold, address[] signers);
    event EmergencyLock(uint256 lockUntil);
    event EmergencyUnlock();
    event AssetManagerConfigured(address indexed manager, bool canManageERC20, bool canManageERC721, bool canManageERC1155);
    event DailyLimitsUpdated(uint256 transactionLimit, uint256 valueLimit);

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address constitutionAddress,
        address governanceAddress
    ) {
        constitution = IDAIO_Constitution_Enhanced(constitutionAddress);
        governance = IExecutiveGovernance(governanceAddress);

        // Initialize with reasonable defaults
        dailyTransactionLimit = 100;
        dailyValueLimit = 10 ether;

        _state = 1; // Initialize state counter
    }

    /**
     * @dev Initialize the token bound account (called by factory or registry)
     */
    function initialize(bytes calldata initData) external {
        require(_state == 1, "Already initialized");

        (uint256 chainId, address tokenContract, uint256 tokenId) = token();
        require(tokenContract != address(0), "Invalid token");

        // Get token owner and set up initial permissions
        address tokenOwner = IERC721(tokenContract).ownerOf(tokenId);
        _grantRole(DEFAULT_ADMIN_ROLE, tokenOwner);
        _grantRole(OPERATOR_ROLE, tokenOwner);

        // Parse initialization data if provided
        if (initData.length > 0) {
            (
                bool enableMultisig,
                uint256 multisigThreshold,
                address[] memory signers,
                uint256 _dailyTransactionLimit,
                uint256 _dailyValueLimit
            ) = abi.decode(initData, (bool, uint256, address[], uint256, uint256));

            if (enableMultisig) {
                _configureMultisig(multisigThreshold, signers);
            }

            if (_dailyTransactionLimit > 0) {
                dailyTransactionLimit = _dailyTransactionLimit;
            }

            if (_dailyValueLimit > 0) {
                dailyValueLimit = _dailyValueLimit;
            }
        }

        _state++;
        emit TokenBoundAccountCreated(chainId, tokenContract, tokenId);
    }

    // =============================================================
    //                    ERC6551 IMPLEMENTATION
    // =============================================================

    /**
     * @dev Returns the token that owns this account
     */
    function token()
        public
        view
        override
        returns (
            uint256 chainId,
            address tokenContract,
            uint256 tokenId
        )
    {
        bytes memory footer = new bytes(0x60);

        assembly {
            extcodecopy(address(), add(footer, 0x20), 0x4d, 0x60)
        }

        return abi.decode(footer, (uint256, address, uint256));
    }

    /**
     * @dev Returns the current account state
     */
    function state() external view override returns (uint256) {
        return _state;
    }

    /**
     * @dev Check if a signer is valid for this account
     */
    function isValidSigner(address signer, bytes calldata context)
        external
        view
        override
        returns (bytes4 magicValue)
    {
        // Check if signer is the token owner
        (uint256 chainId, address tokenContract, uint256 tokenId) = token();
        address tokenOwner = IERC721(tokenContract).ownerOf(tokenId);

        if (signer == tokenOwner) {
            return IERC6551Account.isValidSigner.selector;
        }

        // Check if signer has operator role
        if (hasRole(OPERATOR_ROLE, signer)) {
            return IERC6551Account.isValidSigner.selector;
        }

        // Check if signer is authorized operator
        if (authorizedOperators[signer]) {
            return IERC6551Account.isValidSigner.selector;
        }

        return bytes4(0);
    }

    /**
     * @dev Execute a transaction
     */
    function execute(
        address to,
        uint256 value,
        bytes calldata data,
        uint8 operation
    ) external payable override nonReentrant returns (bytes memory result) {
        require(!locked || block.timestamp >= lockUntil, "Account locked");
        require(_isValidCaller(), "Unauthorized caller");

        // Validate with DAIO constitution
        (uint256 chainId, address tokenContract, uint256 tokenId) = token();
        (bool valid, string memory reason) = constitution.validateTokenBoundAccountAction(
            address(this),
            chainId,
            tokenContract,
            tokenId,
            to,
            value,
            data
        );
        require(valid, reason);

        // Check daily limits
        _checkDailyLimits(value);

        // Check multisig requirements
        if (multisigConfig.enabled && _requiresMultisig(to, value, data)) {
            revert("Multisig approval required");
        }

        // Execute based on operation type
        if (operation == OPERATION_CALL) {
            result = _executeCall(to, value, data);
        } else if (operation == OPERATION_DELEGATECALL) {
            result = _executeDelegateCall(to, data);
        } else if (operation == OPERATION_CREATE) {
            result = _executeCreate(value, data);
        } else if (operation == OPERATION_CREATE2) {
            result = _executeCreate2(value, data);
        } else {
            revert("Invalid operation");
        }

        // Update state and limits
        _state++;
        _updateDailyLimits(value);

        emit Executed(to, value, data, operation, result);
        return result;
    }

    // =============================================================
    //                     BATCH OPERATIONS
    // =============================================================

    struct BatchCall {
        address to;
        uint256 value;
        bytes data;
        uint8 operation;
    }

    /**
     * @dev Execute multiple transactions in a batch
     */
    function executeBatch(BatchCall[] calldata calls) external payable nonReentrant returns (bytes[] memory results) {
        require(!locked || block.timestamp >= lockUntil, "Account locked");
        require(_isValidCaller(), "Unauthorized caller");

        uint256 totalValue = 0;
        for (uint256 i = 0; i < calls.length; i++) {
            totalValue += calls[i].value;
        }

        _checkDailyLimits(totalValue);

        results = new bytes[](calls.length);

        for (uint256 i = 0; i < calls.length; i++) {
            BatchCall memory call = calls[i];

            // Validate each call
            (uint256 chainId, address tokenContract, uint256 tokenId) = token();
            (bool valid, string memory reason) = constitution.validateTokenBoundAccountAction(
                address(this),
                chainId,
                tokenContract,
                tokenId,
                call.to,
                call.value,
                call.data
            );
            require(valid, string(abi.encodePacked("Call ", i, ": ", reason)));

            // Execute call
            if (call.operation == OPERATION_CALL) {
                results[i] = _executeCall(call.to, call.value, call.data);
            } else if (call.operation == OPERATION_DELEGATECALL) {
                results[i] = _executeDelegateCall(call.to, call.data);
            } else {
                revert("Unsupported operation in batch");
            }

            emit Executed(call.to, call.value, call.data, call.operation, results[i]);
        }

        _state++;
        _updateDailyLimits(totalValue);

        return results;
    }

    // =============================================================
    //                    ASSET MANAGEMENT
    // =============================================================

    /**
     * @dev Transfer ERC20 tokens
     */
    function transferERC20(
        address token,
        address to,
        uint256 amount
    ) external {
        require(_isValidCaller(), "Unauthorized caller");
        require(_canManageAsset(msg.sender, token, 0, true, false, false), "Asset management not allowed");

        IERC20(token).transfer(to, amount);
        _state++;
    }

    /**
     * @dev Transfer ERC721 token
     */
    function transferERC721(
        address token,
        address to,
        uint256 tokenId
    ) external {
        require(_isValidCaller(), "Unauthorized caller");
        require(_canManageAsset(msg.sender, token, tokenId, false, true, false), "Asset management not allowed");

        IERC721(token).safeTransferFrom(address(this), to, tokenId);
        _state++;
    }

    /**
     * @dev Transfer ERC1155 tokens
     */
    function transferERC1155(
        address token,
        address to,
        uint256 tokenId,
        uint256 amount,
        bytes calldata data
    ) external {
        require(_isValidCaller(), "Unauthorized caller");
        require(_canManageAsset(msg.sender, token, tokenId, false, false, true), "Asset management not allowed");

        IERC1155(token).safeTransferFrom(address(this), to, tokenId, amount, data);
        _state++;
    }

    /**
     * @dev Transfer Ether
     */
    function transferEther(address payable to, uint256 amount) external nonReentrant {
        require(_isValidCaller(), "Unauthorized caller");
        require(_canManageAsset(msg.sender, address(0), 0, false, false, false), "Ether management not allowed");
        require(address(this).balance >= amount, "Insufficient balance");

        _checkDailyLimits(amount);

        (bool success,) = to.call{value: amount}("");
        require(success, "Ether transfer failed");

        _updateDailyLimits(amount);
        _state++;
    }

    // =============================================================
    //                   ACCESS CONTROL
    // =============================================================

    /**
     * @dev Authorize an operator
     */
    function authorizeOperator(address operator, bool authorized) external onlyRole(DEFAULT_ADMIN_ROLE) {
        authorizedOperators[operator] = authorized;
        if (authorized) {
            _grantRole(OPERATOR_ROLE, operator);
        } else {
            _revokeRole(OPERATOR_ROLE, operator);
        }
        emit OperatorAuthorized(operator, authorized);
    }

    /**
     * @dev Configure asset management permissions for an address
     */
    function configureAssetManager(
        address manager,
        bool canManageERC20,
        bool canManageERC721,
        bool canManageERC1155,
        bool canManageEther,
        uint256[] calldata allowedTokenIds,
        address[] calldata allowedContracts
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        AssetManager storage assetManager = assetManagers[manager];
        assetManager.canManageERC20 = canManageERC20;
        assetManager.canManageERC721 = canManageERC721;
        assetManager.canManageERC1155 = canManageERC1155;
        assetManager.canManageEther = canManageEther;

        // Set allowed token IDs
        for (uint256 i = 0; i < allowedTokenIds.length; i++) {
            assetManager.allowedTokenIds.push(allowedTokenIds[i]);
            assetManager.isAllowedTokenId[allowedTokenIds[i]] = true;
        }

        // Set allowed contracts
        for (uint256 i = 0; i < allowedContracts.length; i++) {
            assetManager.allowedContracts.push(allowedContracts[i]);
            assetManager.isAllowedContract[allowedContracts[i]] = true;
        }

        emit AssetManagerConfigured(manager, canManageERC20, canManageERC721, canManageERC1155);
    }

    // =============================================================
    //                   MULTISIG SUPPORT
    // =============================================================

    /**
     * @dev Configure multisig settings
     */
    function configureMultisig(
        uint256 threshold,
        address[] calldata signers
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _configureMultisig(threshold, signers);
    }

    function _configureMultisig(
        uint256 threshold,
        address[] memory signers
    ) internal {
        require(threshold > 0 && threshold <= signers.length, "Invalid threshold");

        multisigConfig.enabled = true;
        multisigConfig.threshold = threshold;

        // Clear existing signers
        for (uint256 i = 0; i < multisigConfig.signers.length; i++) {
            multisigConfig.isSigner[multisigConfig.signers[i]] = false;
        }
        delete multisigConfig.signers;

        // Set new signers
        for (uint256 i = 0; i < signers.length; i++) {
            multisigConfig.signers.push(signers[i]);
            multisigConfig.isSigner[signers[i]] = true;
        }

        emit MultisigConfigured(true, threshold, signers);
    }

    /**
     * @dev Disable multisig
     */
    function disableMultisig() external onlyRole(DEFAULT_ADMIN_ROLE) {
        multisigConfig.enabled = false;
        emit MultisigConfigured(false, 0, new address[](0));
    }

    // =============================================================
    //                  EMERGENCY CONTROLS
    // =============================================================

    /**
     * @dev Emergency lock the account
     */
    function emergencyLock(uint256 lockDuration) external {
        require(
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender) ||
            hasRole(GUARDIAN_ROLE, msg.sender) ||
            emergencyContacts[msg.sender] ||
            governance.hasExecutiveApproval(msg.sender),
            "Unauthorized"
        );

        locked = true;
        lockUntil = block.timestamp + lockDuration;
        emit EmergencyLock(lockUntil);
    }

    /**
     * @dev Unlock the account
     */
    function unlock() external onlyRole(DEFAULT_ADMIN_ROLE) {
        locked = false;
        lockUntil = 0;
        emit EmergencyUnlock();
    }

    /**
     * @dev Update daily limits
     */
    function updateDailyLimits(
        uint256 transactionLimit,
        uint256 valueLimit
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        dailyTransactionLimit = transactionLimit;
        dailyValueLimit = valueLimit;
        emit DailyLimitsUpdated(transactionLimit, valueLimit);
    }

    // =============================================================
    //                   INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @dev Check if caller is authorized
     */
    function _isValidCaller() internal view returns (bool) {
        if (hasRole(OPERATOR_ROLE, msg.sender)) return true;
        if (authorizedOperators[msg.sender]) return true;

        (uint256 chainId, address tokenContract, uint256 tokenId) = token();
        address tokenOwner = IERC721(tokenContract).ownerOf(tokenId);
        if (msg.sender == tokenOwner) return true;

        return false;
    }

    /**
     * @dev Check if operation requires multisig approval
     */
    function _requiresMultisig(address to, uint256 value, bytes calldata data) internal view returns (bool) {
        // High-value transfers require multisig
        if (value > 1 ether) return true;

        // Certain contract interactions require multisig
        // This is a simplified check - implement based on specific needs
        if (to.code.length > 0 && value > 0.1 ether) return true;

        return false;
    }

    /**
     * @dev Check daily limits
     */
    function _checkDailyLimits(uint256 value) internal view {
        uint256 today = block.timestamp / 1 days;

        if (lastResetDay < today) {
            // Limits reset - check against limits directly
            require(1 <= dailyTransactionLimit, "Daily transaction limit would be exceeded");
            require(value <= dailyValueLimit, "Daily value limit would be exceeded");
        } else {
            // Check current usage
            require(transactionCountToday + 1 <= dailyTransactionLimit, "Daily transaction limit exceeded");
            require(totalValueTransferredToday + value <= dailyValueLimit, "Daily value limit exceeded");
        }
    }

    /**
     * @dev Update daily usage tracking
     */
    function _updateDailyLimits(uint256 value) internal {
        uint256 today = block.timestamp / 1 days;

        if (lastResetDay < today) {
            totalValueTransferredToday = value;
            transactionCountToday = 1;
            lastResetDay = today;
        } else {
            totalValueTransferredToday += value;
            transactionCountToday++;
        }
    }

    /**
     * @dev Check asset management permissions
     */
    function _canManageAsset(
        address manager,
        address tokenContract,
        uint256 tokenId,
        bool isERC20,
        bool isERC721,
        bool isERC1155
    ) internal view returns (bool) {
        if (hasRole(DEFAULT_ADMIN_ROLE, manager)) return true;

        AssetManager storage assetManager = assetManagers[manager];

        if (isERC20 && !assetManager.canManageERC20) return false;
        if (isERC721 && !assetManager.canManageERC721) return false;
        if (isERC1155 && !assetManager.canManageERC1155) return false;
        if (!isERC20 && !isERC721 && !isERC1155 && !assetManager.canManageEther) return false;

        // Check contract allowlist
        if (tokenContract != address(0) &&
            assetManager.allowedContracts.length > 0 &&
            !assetManager.isAllowedContract[tokenContract]) {
            return false;
        }

        // Check token ID allowlist for NFTs
        if ((isERC721 || isERC1155) &&
            assetManager.allowedTokenIds.length > 0 &&
            !assetManager.isAllowedTokenId[tokenId]) {
            return false;
        }

        return true;
    }

    /**
     * @dev Execute a regular call
     */
    function _executeCall(address to, uint256 value, bytes calldata data) internal returns (bytes memory) {
        (bool success, bytes memory result) = to.call{value: value}(data);
        if (!success) {
            assembly {
                revert(add(result, 32), mload(result))
            }
        }
        return result;
    }

    /**
     * @dev Execute a delegate call
     */
    function _executeDelegateCall(address to, bytes calldata data) internal returns (bytes memory) {
        (bool success, bytes memory result) = to.delegatecall(data);
        if (!success) {
            assembly {
                revert(add(result, 32), mload(result))
            }
        }
        return result;
    }

    /**
     * @dev Execute contract creation
     */
    function _executeCreate(uint256 value, bytes calldata data) internal returns (bytes memory) {
        address created;
        assembly {
            created := create(value, add(data.offset, 0x20), data.length)
        }
        require(created != address(0), "Contract creation failed");
        return abi.encode(created);
    }

    /**
     * @dev Execute CREATE2 contract creation
     */
    function _executeCreate2(uint256 value, bytes calldata data) internal returns (bytes memory) {
        require(data.length >= 32, "Invalid CREATE2 data");

        bytes32 salt = bytes32(data[:32]);
        bytes memory bytecode = data[32:];

        address created;
        assembly {
            created := create2(value, add(bytecode, 0x20), mload(bytecode), salt)
        }
        require(created != address(0), "CREATE2 failed");
        return abi.encode(created);
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get multisig configuration
     */
    function getMultisigConfig() external view returns (
        bool enabled,
        uint256 threshold,
        address[] memory signers
    ) {
        return (multisigConfig.enabled, multisigConfig.threshold, multisigConfig.signers);
    }

    /**
     * @dev Get daily usage stats
     */
    function getDailyUsage() external view returns (
        uint256 transactionCount,
        uint256 valueTransferred,
        uint256 transactionLimit,
        uint256 valueLimit,
        uint256 resetDay
    ) {
        return (
            transactionCountToday,
            totalValueTransferredToday,
            dailyTransactionLimit,
            dailyValueLimit,
            lastResetDay
        );
    }

    /**
     * @dev Check if account owns a specific token
     */
    function ownsToken(address tokenContract, uint256 tokenId) external view returns (bool) {
        if (tokenContract.code.length == 0) return false;

        try IERC721(tokenContract).ownerOf(tokenId) returns (address owner) {
            return owner == address(this);
        } catch {
            return false;
        }
    }

    // =============================================================
    //                   INTERFACE SUPPORT
    // =============================================================

    /**
     * @dev See {IERC165-supportsInterface}.
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(IERC165, AccessControl)
        returns (bool)
    {
        return
            interfaceId == ERC6551_ACCOUNT_INTERFACE_ID ||
            interfaceId == ERC6551_EXECUTABLE_INTERFACE_ID ||
            super.supportsInterface(interfaceId);
    }

    // =============================================================
    //                    RECEIVE/FALLBACK
    // =============================================================

    receive() external payable override {
        // Allow the account to receive Ether
    }

    fallback() external payable {
        // Handle unknown function calls
        revert("Function not found");
    }
}