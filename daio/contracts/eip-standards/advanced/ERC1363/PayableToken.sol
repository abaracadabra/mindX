// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/interfaces/IERC165.sol";

/**
 * @title PayableToken
 * @notice Execute code on transfer - ERC1363 implementation with DAIO integration
 * @dev ERC1363 payable token that can execute code upon transfer/approval with governance oversight
 */
contract PayableToken is ERC20, AccessControl, ReentrancyGuard, Pausable, IERC165 {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant HOOK_MANAGER_ROLE = keccak256("HOOK_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // ERC1363 interface IDs
    bytes4 private constant _INTERFACE_ID_ERC1363_RECEIVER = 0x88a7ca5c;
    bytes4 private constant _INTERFACE_ID_ERC1363_SPENDER = 0x7b04a2d0;
    bytes4 private constant _INTERFACE_ID_ERC1363 = 0xb0202a11;

    // Hook execution configuration
    struct HookConfig {
        bool transferHookEnabled;      // Whether transfer hooks are enabled
        bool approvalHookEnabled;      // Whether approval hooks are enabled
        uint256 maxHookGasLimit;      // Maximum gas limit for hook execution
        uint256 hookFailureMode;      // 0=ignore, 1=revert, 2=log
        bool requireWhitelist;        // Whether recipients must be whitelisted for hooks
        uint256 cooldownPeriod;       // Cooldown between hook executions per recipient
    }

    struct RecipientProfile {
        bool isWhitelisted;           // Whether recipient is whitelisted for hooks
        bool hookEnabled;             // Whether hooks are enabled for this recipient
        uint256 lastHookExecution;    // Last hook execution timestamp
        uint256 totalHookExecutions; // Total number of hook executions
        uint256 failedHookExecutions; // Number of failed hook executions
        bool temporarilyDisabled;     // Whether hooks are temporarily disabled
        string recipientType;         // "CONTRACT", "EOA", "MULTISIG"
    }

    // DAIO integration
    struct DAIOIntegration {
        address treasuryContract;     // DAIO treasury contract
        address governanceContract;   // Governance contract for hook approvals
        uint256 titheRate;           // Tithe rate for hook execution fees (BPS)
        bool constitutionalCompliance; // Whether to enforce constitutional compliance
        uint256 maxSingleTransfer;   // Maximum single transfer amount
        bool emergencyHookDisable;   // Emergency disable all hooks
    }

    // Execution tracking
    struct HookExecution {
        address recipient;            // Hook recipient
        uint256 amount;              // Transfer amount
        bytes data;                  // Execution data
        uint256 gasUsed;             // Gas used for execution
        bool success;                // Whether execution was successful
        uint256 timestamp;           // Execution timestamp
        string errorReason;          // Error reason if failed
    }

    // State variables
    HookConfig public hookConfig;
    DAIOIntegration public daioIntegration;
    mapping(address => RecipientProfile) public recipientProfiles;
    mapping(address => bool) public authorizedHookContracts;

    // Execution history
    HookExecution[] public hookExecutions;
    mapping(address => uint256[]) public recipientExecutionHistory; // recipient -> execution indices
    uint256 public totalHookExecutions;
    uint256 public totalHookFailures;

    // Gas optimization
    uint256 private constant DEFAULT_GAS_LIMIT = 100000;
    uint256 private constant MAX_GAS_LIMIT = 500000;

    // Fee tracking
    mapping(address => uint256) public collectedHookFees; // recipient -> fees collected
    uint256 public totalFeesCollected;
    uint256 public totalTithePaid;

    // Events
    event TransferAndCall(
        address indexed from,
        address indexed to,
        uint256 value,
        bytes data,
        bool success
    );
    event ApproveAndCall(
        address indexed owner,
        address indexed spender,
        uint256 value,
        bytes data,
        bool success
    );
    event HookConfigurationUpdated(
        bool transferHookEnabled,
        bool approvalHookEnabled,
        uint256 maxGasLimit
    );
    event RecipientWhitelisted(
        address indexed recipient,
        bool whitelisted,
        string recipientType
    );
    event HookExecutionFailed(
        address indexed recipient,
        uint256 amount,
        string reason,
        uint256 gasUsed
    );
    event EmergencyHookDisabled(
        address indexed disabler,
        string reason
    );
    event HookFeesCollected(
        address indexed recipient,
        uint256 feeAmount,
        uint256 titheAmount
    );

    /**
     * @notice Initialize PayableToken with DAIO integration
     * @param name Token name
     * @param symbol Token symbol
     * @param initialSupply Initial token supply
     * @param treasuryContract DAIO treasury contract
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        uint256 initialSupply,
        address treasuryContract,
        address admin
    ) ERC20(name, symbol) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(BURNER_ROLE, admin);
        _grantRole(HOOK_MANAGER_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        // Initialize hook configuration
        hookConfig = HookConfig({
            transferHookEnabled: true,
            approvalHookEnabled: true,
            maxHookGasLimit: DEFAULT_GAS_LIMIT,
            hookFailureMode: 2, // Log failures by default
            requireWhitelist: false,
            cooldownPeriod: 0 // No cooldown by default
        });

        // Initialize DAIO integration
        daioIntegration = DAIOIntegration({
            treasuryContract: treasuryContract,
            governanceContract: address(0), // Set later
            titheRate: 1500, // 15% tithe rate
            constitutionalCompliance: true,
            maxSingleTransfer: type(uint256).max,
            emergencyHookDisable: false
        });

        // Mint initial supply to admin
        if (initialSupply > 0) {
            _mint(admin, initialSupply);
        }
    }

    /**
     * @notice Transfer tokens and call recipient contract
     * @param to Recipient address
     * @param value Amount to transfer
     * @param data Data to pass to recipient
     * @return success Whether transfer and call were successful
     */
    function transferAndCall(
        address to,
        uint256 value,
        bytes memory data
    ) public nonReentrant whenNotPaused returns (bool success) {
        require(to != address(0), "Transfer to zero address");
        require(value > 0, "Transfer amount must be positive");
        require(!daioIntegration.emergencyHookDisable, "Emergency hook disable active");

        // Check constitutional compliance
        if (daioIntegration.constitutionalCompliance) {
            require(value <= daioIntegration.maxSingleTransfer, "Transfer exceeds constitutional limit");
        }

        // Execute transfer
        transfer(to, value);

        // Execute hook if applicable
        bool hookSuccess = _executeTransferHook(to, value, data);

        emit TransferAndCall(msg.sender, to, value, data, hookSuccess);

        return hookSuccess;
    }

    /**
     * @notice Transfer tokens from spender and call recipient contract
     * @param from Token owner address
     * @param to Recipient address
     * @param value Amount to transfer
     * @param data Data to pass to recipient
     * @return success Whether transfer and call were successful
     */
    function transferFromAndCall(
        address from,
        address to,
        uint256 value,
        bytes memory data
    ) public nonReentrant whenNotPaused returns (bool success) {
        require(to != address(0), "Transfer to zero address");
        require(value > 0, "Transfer amount must be positive");
        require(!daioIntegration.emergencyHookDisable, "Emergency hook disable active");

        // Check constitutional compliance
        if (daioIntegration.constitutionalCompliance) {
            require(value <= daioIntegration.maxSingleTransfer, "Transfer exceeds constitutional limit");
        }

        // Execute transfer
        transferFrom(from, to, value);

        // Execute hook if applicable
        bool hookSuccess = _executeTransferHook(to, value, data);

        emit TransferAndCall(from, to, value, data, hookSuccess);

        return hookSuccess;
    }

    /**
     * @notice Approve spender and call spender contract
     * @param spender Spender address
     * @param value Amount to approve
     * @param data Data to pass to spender
     * @return success Whether approval and call were successful
     */
    function approveAndCall(
        address spender,
        uint256 value,
        bytes memory data
    ) public nonReentrant whenNotPaused returns (bool success) {
        require(spender != address(0), "Approve to zero address");
        require(!daioIntegration.emergencyHookDisable, "Emergency hook disable active");

        // Execute approval
        approve(spender, value);

        // Execute hook if applicable
        bool hookSuccess = _executeApprovalHook(spender, value, data);

        emit ApproveAndCall(msg.sender, spender, value, data, hookSuccess);

        return hookSuccess;
    }

    /**
     * @notice Configure hook execution parameters
     * @param transferHookEnabled Whether transfer hooks are enabled
     * @param approvalHookEnabled Whether approval hooks are enabled
     * @param maxGasLimit Maximum gas limit for hook execution
     * @param hookFailureMode Failure handling mode (0=ignore, 1=revert, 2=log)
     * @param requireWhitelist Whether to require whitelist for hooks
     * @param cooldownPeriod Cooldown period between hook executions
     */
    function configureHooks(
        bool transferHookEnabled,
        bool approvalHookEnabled,
        uint256 maxGasLimit,
        uint256 hookFailureMode,
        bool requireWhitelist,
        uint256 cooldownPeriod
    ) external onlyRole(HOOK_MANAGER_ROLE) {
        require(maxGasLimit <= MAX_GAS_LIMIT, "Gas limit too high");
        require(hookFailureMode <= 2, "Invalid failure mode");
        require(cooldownPeriod <= 3600, "Cooldown period too long"); // Max 1 hour

        hookConfig = HookConfig({
            transferHookEnabled: transferHookEnabled,
            approvalHookEnabled: approvalHookEnabled,
            maxHookGasLimit: maxGasLimit,
            hookFailureMode: hookFailureMode,
            requireWhitelist: requireWhitelist,
            cooldownPeriod: cooldownPeriod
        });

        emit HookConfigurationUpdated(transferHookEnabled, approvalHookEnabled, maxGasLimit);
    }

    /**
     * @notice Whitelist recipient for hook execution
     * @param recipient Recipient address
     * @param whitelisted Whether recipient is whitelisted
     * @param recipientType Type of recipient ("CONTRACT", "EOA", "MULTISIG")
     */
    function setRecipientWhitelist(
        address recipient,
        bool whitelisted,
        string memory recipientType
    ) external onlyRole(HOOK_MANAGER_ROLE) {
        require(recipient != address(0), "Invalid recipient address");

        recipientProfiles[recipient].isWhitelisted = whitelisted;
        recipientProfiles[recipient].hookEnabled = whitelisted;
        recipientProfiles[recipient].recipientType = recipientType;

        emit RecipientWhitelisted(recipient, whitelisted, recipientType);
    }

    /**
     * @notice Enable/disable hooks for specific recipient
     * @param recipient Recipient address
     * @param enabled Whether hooks are enabled for this recipient
     */
    function setRecipientHookEnabled(
        address recipient,
        bool enabled
    ) external onlyRole(HOOK_MANAGER_ROLE) {
        recipientProfiles[recipient].hookEnabled = enabled;
    }

    /**
     * @notice Emergency disable all hook executions
     * @param reason Reason for emergency disable
     */
    function emergencyDisableHooks(string memory reason) external onlyRole(EMERGENCY_ROLE) {
        daioIntegration.emergencyHookDisable = true;
        emit EmergencyHookDisabled(msg.sender, reason);
    }

    /**
     * @notice Re-enable hooks after emergency disable
     */
    function reenableHooks() external onlyRole(EMERGENCY_ROLE) {
        daioIntegration.emergencyHookDisable = false;
    }

    /**
     * @notice Mint tokens to address
     * @param to Address to mint to
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(amount > 0, "Amount must be positive");
        _mint(to, amount);
    }

    /**
     * @notice Burn tokens from address
     * @param from Address to burn from
     * @param amount Amount to burn
     */
    function burn(address from, uint256 amount) external onlyRole(BURNER_ROLE) {
        require(from != address(0), "Cannot burn from zero address");
        require(amount > 0, "Amount must be positive");
        _burn(from, amount);
    }

    /**
     * @notice Authorize contract for hook execution
     * @param contractAddr Contract address to authorize
     * @param authorized Whether contract is authorized
     */
    function setAuthorizedHookContract(
        address contractAddr,
        bool authorized
    ) external onlyRole(HOOK_MANAGER_ROLE) {
        require(contractAddr != address(0), "Invalid contract address");
        require(_isContract(contractAddr), "Address is not a contract");

        authorizedHookContracts[contractAddr] = authorized;
    }

    /**
     * @notice Collect hook execution fees and pay tithe
     * @param recipient Recipient to collect fees for
     */
    function collectHookFees(address recipient) external nonReentrant {
        uint256 fees = collectedHookFees[recipient];
        require(fees > 0, "No fees to collect");

        uint256 titheAmount = 0;

        // Calculate and pay tithe to DAIO treasury
        if (daioIntegration.treasuryContract != address(0) && daioIntegration.titheRate > 0) {
            titheAmount = (fees * daioIntegration.titheRate) / 10000;

            if (titheAmount > 0 && balanceOf(address(this)) >= titheAmount) {
                _transfer(address(this), daioIntegration.treasuryContract, titheAmount);
                totalTithePaid += titheAmount;
            }
        }

        // Reset collected fees
        collectedHookFees[recipient] = 0;

        emit HookFeesCollected(recipient, fees, titheAmount);
    }

    /**
     * @notice Get hook execution history for recipient
     * @param recipient Recipient address
     * @param offset Offset in history
     * @param limit Maximum number of results
     * @return executions Array of hook executions
     */
    function getHookExecutionHistory(
        address recipient,
        uint256 offset,
        uint256 limit
    ) external view returns (HookExecution[] memory executions) {
        uint256[] memory executionIndices = recipientExecutionHistory[recipient];
        uint256 totalExecutions = executionIndices.length;

        if (offset >= totalExecutions) {
            return new HookExecution[](0);
        }

        uint256 end = offset + limit;
        if (end > totalExecutions) {
            end = totalExecutions;
        }

        executions = new HookExecution[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            executions[i - offset] = hookExecutions[executionIndices[i]];
        }

        return executions;
    }

    /**
     * @notice Get recipient profile
     * @param recipient Recipient address
     * @return profile Recipient profile information
     */
    function getRecipientProfile(address recipient) external view returns (RecipientProfile memory profile) {
        return recipientProfiles[recipient];
    }

    /**
     * @notice Check if interface is supported
     * @param interfaceId Interface identifier
     * @return supported Whether interface is supported
     */
    function supportsInterface(bytes4 interfaceId) public view override(AccessControl, IERC165) returns (bool) {
        return
            interfaceId == _INTERFACE_ID_ERC1363 ||
            interfaceId == _INTERFACE_ID_ERC1363_RECEIVER ||
            interfaceId == _INTERFACE_ID_ERC1363_SPENDER ||
            super.supportsInterface(interfaceId);
    }

    // Internal Functions

    function _executeTransferHook(
        address to,
        uint256 value,
        bytes memory data
    ) internal returns (bool success) {
        if (!hookConfig.transferHookEnabled) return true;
        if (daioIntegration.emergencyHookDisable) return false;

        // Check if recipient can execute hooks
        if (!_canExecuteHook(to)) return true;

        // Check cooldown period
        RecipientProfile storage profile = recipientProfiles[to];
        if (hookConfig.cooldownPeriod > 0 &&
            block.timestamp < profile.lastHookExecution + hookConfig.cooldownPeriod) {
            return true; // Skip hook due to cooldown
        }

        // Check if recipient is a contract with ERC1363 receiver interface
        if (!_isContract(to)) return true;

        // Execute hook with gas limit
        try this.executeTransferHook{gas: hookConfig.maxHookGasLimit}(to, msg.sender, value, data) returns (bool hookSuccess) {
            success = hookSuccess;
        } catch Error(string memory reason) {
            success = false;
            _handleHookFailure(to, value, reason);
        } catch {
            success = false;
            _handleHookFailure(to, value, "Hook execution reverted");
        }

        // Update profile
        profile.lastHookExecution = block.timestamp;
        profile.totalHookExecutions++;
        if (!success) {
            profile.failedHookExecutions++;
        }

        // Record execution
        _recordHookExecution(to, value, data, success ? 0 : hookConfig.maxHookGasLimit, success, "");

        // Collect fees for hook execution
        if (success) {
            _collectHookExecutionFee(to, value);
        }

        return success;
    }

    function _executeApprovalHook(
        address spender,
        uint256 value,
        bytes memory data
    ) internal returns (bool success) {
        if (!hookConfig.approvalHookEnabled) return true;
        if (daioIntegration.emergencyHookDisable) return false;

        // Check if spender can execute hooks
        if (!_canExecuteHook(spender)) return true;

        // Check cooldown period
        RecipientProfile storage profile = recipientProfiles[spender];
        if (hookConfig.cooldownPeriod > 0 &&
            block.timestamp < profile.lastHookExecution + hookConfig.cooldownPeriod) {
            return true; // Skip hook due to cooldown
        }

        // Check if spender is a contract with ERC1363 spender interface
        if (!_isContract(spender)) return true;

        // Execute hook with gas limit
        try this.executeApprovalHook{gas: hookConfig.maxHookGasLimit}(spender, msg.sender, value, data) returns (bool hookSuccess) {
            success = hookSuccess;
        } catch Error(string memory reason) {
            success = false;
            _handleHookFailure(spender, value, reason);
        } catch {
            success = false;
            _handleHookFailure(spender, value, "Hook execution reverted");
        }

        // Update profile
        profile.lastHookExecution = block.timestamp;
        profile.totalHookExecutions++;
        if (!success) {
            profile.failedHookExecutions++;
        }

        // Record execution
        _recordHookExecution(spender, value, data, success ? 0 : hookConfig.maxHookGasLimit, success, "");

        return success;
    }

    /**
     * @notice Execute transfer hook (external for gas limit control)
     * @param to Recipient address
     * @param from Sender address
     * @param value Transfer amount
     * @param data Hook data
     * @return success Whether hook execution was successful
     */
    function executeTransferHook(
        address to,
        address from,
        uint256 value,
        bytes memory data
    ) external returns (bool success) {
        require(msg.sender == address(this), "Only self-call allowed");

        // Check if recipient supports ERC1363 receiver interface
        try IERC165(to).supportsInterface(_INTERFACE_ID_ERC1363_RECEIVER) returns (bool supported) {
            if (!supported) return true;
        } catch {
            return true;
        }

        // Call onTransferReceived
        try IERC1363Receiver(to).onTransferReceived(msg.sender, from, value, data) returns (bytes4 retval) {
            return retval == IERC1363Receiver.onTransferReceived.selector;
        } catch {
            return false;
        }
    }

    /**
     * @notice Execute approval hook (external for gas limit control)
     * @param spender Spender address
     * @param owner Owner address
     * @param value Approval amount
     * @param data Hook data
     * @return success Whether hook execution was successful
     */
    function executeApprovalHook(
        address spender,
        address owner,
        uint256 value,
        bytes memory data
    ) external returns (bool success) {
        require(msg.sender == address(this), "Only self-call allowed");

        // Check if spender supports ERC1363 spender interface
        try IERC165(spender).supportsInterface(_INTERFACE_ID_ERC1363_SPENDER) returns (bool supported) {
            if (!supported) return true;
        } catch {
            return true;
        }

        // Call onApprovalReceived
        try IERC1363Spender(spender).onApprovalReceived(owner, value, data) returns (bytes4 retval) {
            return retval == IERC1363Spender.onApprovalReceived.selector;
        } catch {
            return false;
        }
    }

    function _canExecuteHook(address recipient) internal view returns (bool) {
        RecipientProfile memory profile = recipientProfiles[recipient];

        // Check if recipient is temporarily disabled
        if (profile.temporarilyDisabled) return false;

        // Check whitelist requirements
        if (hookConfig.requireWhitelist && !profile.isWhitelisted) return false;

        // Check if hooks are enabled for this recipient
        if (!profile.hookEnabled) return false;

        return true;
    }

    function _handleHookFailure(address recipient, uint256 amount, string memory reason) internal {
        totalHookFailures++;

        emit HookExecutionFailed(recipient, amount, reason, hookConfig.maxHookGasLimit);

        // Handle based on failure mode
        if (hookConfig.hookFailureMode == 1) {
            revert(string(abi.encodePacked("Hook execution failed: ", reason)));
        }
        // Mode 0 (ignore) and 2 (log) both continue execution
        // Mode 2 already emitted event above

        // Temporarily disable hooks for recipients with high failure rates
        RecipientProfile storage profile = recipientProfiles[recipient];
        if (profile.failedHookExecutions >= 10 &&
            profile.failedHookExecutions * 100 / profile.totalHookExecutions >= 50) {
            profile.temporarilyDisabled = true;
        }
    }

    function _recordHookExecution(
        address recipient,
        uint256 amount,
        bytes memory data,
        uint256 gasUsed,
        bool success,
        string memory errorReason
    ) internal {
        uint256 executionIndex = hookExecutions.length;

        hookExecutions.push(HookExecution({
            recipient: recipient,
            amount: amount,
            data: data,
            gasUsed: gasUsed,
            success: success,
            timestamp: block.timestamp,
            errorReason: errorReason
        }));

        recipientExecutionHistory[recipient].push(executionIndex);
        totalHookExecutions++;
    }

    function _collectHookExecutionFee(address recipient, uint256 value) internal {
        // Collect small fee for hook execution (0.1% of transfer value)
        uint256 feeAmount = value / 1000;

        if (feeAmount > 0 && balanceOf(msg.sender) >= feeAmount) {
            _transfer(msg.sender, address(this), feeAmount);
            collectedHookFees[recipient] += feeAmount;
            totalFeesCollected += feeAmount;
        }
    }

    function _isContract(address account) internal view returns (bool) {
        return account.code.length > 0;
    }

    /**
     * @notice Update DAIO integration settings
     * @param treasuryContract New treasury contract
     * @param titheRate New tithe rate (BPS)
     * @param maxSingleTransfer New maximum single transfer
     * @param constitutionalCompliance Whether to enforce constitutional compliance
     */
    function updateDAIOIntegration(
        address treasuryContract,
        uint256 titheRate,
        uint256 maxSingleTransfer,
        bool constitutionalCompliance
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(titheRate <= 1500, "Tithe rate too high"); // Max 15%

        daioIntegration.treasuryContract = treasuryContract;
        daioIntegration.titheRate = titheRate;
        daioIntegration.maxSingleTransfer = maxSingleTransfer;
        daioIntegration.constitutionalCompliance = constitutionalCompliance;
    }

    /**
     * @notice Pause token operations
     */
    function pause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause token operations
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }

    /**
     * @notice Get hook execution statistics
     * @return totalExecutions Total hook executions
     * @return totalFailures Total hook failures
     * @return successRate Success rate (BPS)
     * @return feesCollected Total fees collected
     */
    function getHookStatistics() external view returns (
        uint256 totalExecutions,
        uint256 totalFailures,
        uint256 successRate,
        uint256 feesCollected
    ) {
        totalExecutions = totalHookExecutions;
        totalFailures = totalHookFailures;
        successRate = totalExecutions > 0 ?
            ((totalExecutions - totalFailures) * 10000) / totalExecutions : 0;
        feesCollected = totalFeesCollected;

        return (totalExecutions, totalFailures, successRate, feesCollected);
    }
}

// ERC1363 interfaces
interface IERC1363Receiver {
    function onTransferReceived(
        address operator,
        address from,
        uint256 value,
        bytes memory data
    ) external returns (bytes4);
}

interface IERC1363Spender {
    function onApprovalReceived(
        address owner,
        uint256 value,
        bytes memory data
    ) external returns (bytes4);
}