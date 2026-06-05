// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {AccessControlDefaultAdminRulesUpgradeable} from
    "@openzeppelin/contracts-upgradeable/access/extensions/AccessControlDefaultAdminRulesUpgradeable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import {ReentrancyGuardUpgradeable} from
    "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IOpenBDKValidatorRegistry} from "../interfaces/IOpenBDKValidatorRegistry.sol";

/**
 * @title OpenBDKValidatorRegistry
 * @notice Implementation of the openBDK Relayer-Validator registry
 * @dev Implements the v1 topology: 1 Relayer + 3 Validators with 2/3 vote consensus.
 *
 *      The math: n = 3f + 1 where f = 1 Byzantine fault
 *      → 4 nodes total (1 Relayer + 3 Validators)
 *      → 2/3 of 3 Validators = 2 must approve
 *      → 1 Validator can be malicious or offline; 1 redundant for maintenance
 *
 *      This is the MINIMUM VIABLE BFT deployment — Lamport's classical result.
 *
 *      Token gating:
 *      - Validators must hold >= minimumStake tokens locked in this contract
 *      - The stake aligns economic incentives with honest behavior
 *      - Slashing destroys stake for misbehavior
 *      - Block rewards + fee shares (70/20/10 split) compensate honest operators
 *
 *      The economic flywheel:
 *      More users → more fees → higher validator rewards → more operators want
 *      to validate → higher token demand → higher token value → more security
 *
 * @custom:security-contact security@openbdk.org
 */
contract OpenBDKValidatorRegistry is
    Initializable,
    AccessControlDefaultAdminRulesUpgradeable,
    UUPSUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable,
    IOpenBDKValidatorRegistry
{
    using SafeERC20 for IERC20;

    // ============ Errors ============

    error InsufficientStake();
    error AlreadyRegistered();
    error NotRegistered();
    error NotActiveValidator();
    error MaxValidatorsReached();
    error OnlyRelayer();
    error OnlyConsensus();
    error NoRewardsToClaim();
    error UnbondingPeriodActive();
    error InvalidRelayer();

    // ============ Constants ============

    /// @notice Maximum active validators in v1 topology
    uint256 public constant MAX_ACTIVE_VALIDATORS_V1 = 3;

    /// @notice Required votes for consensus (2/3 of 3 = 2)
    uint256 public constant CONSENSUS_THRESHOLD = 2;

    // ============ Roles ============

    bytes32 public constant CONSENSUS_ROLE = keccak256("CONSENSUS_ROLE");
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");

    // ============ ERC-7201 Storage ============

    /// @custom:storage-location erc7201:openbdk.storage.ValidatorRegistry
    struct ValidatorRegistryStorage {
        IERC20 stakingToken;                          // THRUST or governance token
        uint256 minimumStake;                         // Minimum tokens to qualify
        uint256 unbondingPeriod;                      // Blocks tokens are locked after exit
        uint256 maxActiveValidators;                  // Currently 3 in v1
        address currentRelayer;                       // Block proposer (the +1 in 3f+1)

        mapping(address => Validator) validators;     // operator => Validator data
        address[] activeValidatorSet;                 // Currently active validators
        mapping(address => uint256) unbondingEndsAt;  // operator => block number
    }

    bytes32 private constant ValidatorRegistryStorageLocation =
        0x77cd069e7a52e8a190d87ce9d92c16a483ece1fa3679ded68639878d42cbc600;

    function _getStorage() private pure returns (ValidatorRegistryStorage storage $) {
        assembly {
            $.slot := ValidatorRegistryStorageLocation
        }
    }

    // ============ Initializer ============

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(
        address _admin,
        address _stakingToken,
        address _initialRelayer,
        uint256 _minimumStake,
        uint256 _unbondingPeriod
    ) public initializer {
        __AccessControlDefaultAdminRules_init(3 days, _admin);
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();

        ValidatorRegistryStorage storage $ = _getStorage();
        $.stakingToken = IERC20(_stakingToken);
        $.minimumStake = _minimumStake;
        $.unbondingPeriod = _unbondingPeriod;
        $.maxActiveValidators = MAX_ACTIVE_VALIDATORS_V1;
        $.currentRelayer = _initialRelayer;
    }

    function _authorizeUpgrade(address) internal override onlyRole(DEFAULT_ADMIN_ROLE) {}

    // ============ Modifiers ============

    modifier onlyRelayer() {
        if (msg.sender != _getStorage().currentRelayer) revert OnlyRelayer();
        _;
    }

    // ============ Validator lifecycle ============

    /**
     * @notice Register as a Validator candidate by staking minimum tokens
     * @dev Tokens are pulled from msg.sender; status becomes Candidate
     */
    function registerValidator() external override whenNotPaused nonReentrant {
        ValidatorRegistryStorage storage $ = _getStorage();

        if ($.validators[msg.sender].status != ValidatorStatus.None) revert AlreadyRegistered();
        if ($.stakingToken.balanceOf(msg.sender) < $.minimumStake) revert InsufficientStake();

        // Pull stake from user
        $.stakingToken.safeTransferFrom(msg.sender, address(this), $.minimumStake);

        $.validators[msg.sender] = Validator({
            operator: msg.sender,
            stakedAmount: $.minimumStake,
            activeSince: 0,
            rewardsAccumulated: 0,
            fidesScore: 100,                          // Initial BONAFIDE reputation
            status: ValidatorStatus.Candidate
        });

        emit ValidatorRegistered(msg.sender, $.minimumStake);
    }

    /**
     * @notice Activate a registered Validator into the active set
     * @dev v1: Only the Relayer can activate. v2+: governance vote.
     *      Maximum 3 active validators in v1.
     */
    function activateValidator(address validator)
        external override onlyRelayer whenNotPaused
    {
        ValidatorRegistryStorage storage $ = _getStorage();

        if ($.validators[validator].status != ValidatorStatus.Candidate) revert NotRegistered();
        if ($.activeValidatorSet.length >= $.maxActiveValidators) revert MaxValidatorsReached();

        $.validators[validator].status = ValidatorStatus.Active;
        $.validators[validator].activeSince = block.number;
        $.activeValidatorSet.push(validator);

        emit ValidatorActivated(validator, msg.sender);
    }

    /**
     * @notice Voluntarily exit the validator set
     * @dev Tokens unlock after unbondingPeriod blocks
     */
    function exitValidator() external override nonReentrant {
        ValidatorRegistryStorage storage $ = _getStorage();
        Validator storage v = $.validators[msg.sender];

        if (v.status != ValidatorStatus.Active && v.status != ValidatorStatus.Candidate) {
            revert NotRegistered();
        }

        // Remove from active set
        if (v.status == ValidatorStatus.Active) {
            _removeFromActiveSet(msg.sender);
        }

        v.status = ValidatorStatus.Exited;
        $.unbondingEndsAt[msg.sender] = block.number + $.unbondingPeriod;

        emit ValidatorExited(msg.sender, $.unbondingEndsAt[msg.sender]);
    }

    /**
     * @notice Withdraw stake after unbonding period completes
     */
    function withdrawStake() external nonReentrant {
        ValidatorRegistryStorage storage $ = _getStorage();
        Validator storage v = $.validators[msg.sender];

        if (v.status != ValidatorStatus.Exited) revert NotRegistered();
        if (block.number < $.unbondingEndsAt[msg.sender]) revert UnbondingPeriodActive();

        uint256 amount = v.stakedAmount + v.rewardsAccumulated;
        v.stakedAmount = 0;
        v.rewardsAccumulated = 0;

        $.stakingToken.safeTransfer(msg.sender, amount);
    }

    // ============ Rewards ============

    /**
     * @notice Distribute block rewards to approving validators
     * @dev Called by ConsensusManager after block finalization
     *      Default split: 70% validators / 20% relayer / 10% burn (handled by caller)
     */
    function distributeRewards(address[] calldata approvers, uint256 blockReward)
        external override onlyRole(CONSENSUS_ROLE)
    {
        if (approvers.length == 0) return;

        uint256 perValidator = blockReward / approvers.length;
        ValidatorRegistryStorage storage $ = _getStorage();

        for (uint256 i = 0; i < approvers.length; i++) {
            $.validators[approvers[i]].rewardsAccumulated += perValidator;
            // Increase Fides score for honest participation (BONAFIDE integration)
            $.validators[approvers[i]].fidesScore += 1;
        }

        emit RewardsDistributed(approvers, blockReward);
    }

    /**
     * @notice Claim accumulated rewards (does not touch staked principal)
     */
    function claimRewards() external override nonReentrant returns (uint256) {
        ValidatorRegistryStorage storage $ = _getStorage();
        Validator storage v = $.validators[msg.sender];

        uint256 amount = v.rewardsAccumulated;
        if (amount == 0) revert NoRewardsToClaim();

        v.rewardsAccumulated = 0;
        $.stakingToken.safeTransfer(msg.sender, amount);

        emit RewardsClaimed(msg.sender, amount);
        return amount;
    }

    // ============ Slashing ============

    /**
     * @notice Slash a misbehaving validator
     * @dev Called by ConsensusManager when equivocation or invalid voting is detected
     *      v1: 10% slash for downtime, up to 100% for double-signing (BONAFIDE Censura)
     */
    function slash(address validator, uint256 amount, string calldata reason)
        external override onlyRole(CONSENSUS_ROLE)
    {
        ValidatorRegistryStorage storage $ = _getStorage();
        Validator storage v = $.validators[validator];

        uint256 slashAmount = amount > v.stakedAmount ? v.stakedAmount : amount;
        v.stakedAmount -= slashAmount;
        v.fidesScore = v.fidesScore > 10 ? v.fidesScore - 10 : 0;

        // If stake falls below minimum, deactivate
        if (v.stakedAmount < $.minimumStake && v.status == ValidatorStatus.Active) {
            v.status = ValidatorStatus.Slashed;
            _removeFromActiveSet(validator);
        }

        emit ValidatorSlashed(validator, slashAmount, reason);
    }

    // ============ Relayer rotation ============

    /**
     * @notice Rotate the Relayer role
     * @dev Triggered by:
     *      - Governance vote (GOVERNANCE_ROLE)
     *      - Automatic rotation after N consecutive proposal failures (CONSENSUS_ROLE)
     *      The new Relayer must be an Active Validator (provable participation)
     */
    function rotateRelayer(address newRelayer)
        external override
    {
        ValidatorRegistryStorage storage $ = _getStorage();

        // Either governance or consensus can rotate
        require(
            hasRole(GOVERNANCE_ROLE, msg.sender) || hasRole(CONSENSUS_ROLE, msg.sender),
            "Unauthorized rotation"
        );

        // New Relayer must be an active validator
        if ($.validators[newRelayer].status != ValidatorStatus.Active) revert InvalidRelayer();

        address oldRelayer = $.currentRelayer;
        $.currentRelayer = newRelayer;

        emit RelayerRotated(oldRelayer, newRelayer);
    }

    // ============ Internal helpers ============

    function _removeFromActiveSet(address validator) internal {
        ValidatorRegistryStorage storage $ = _getStorage();
        uint256 length = $.activeValidatorSet.length;
        for (uint256 i = 0; i < length; i++) {
            if ($.activeValidatorSet[i] == validator) {
                $.activeValidatorSet[i] = $.activeValidatorSet[length - 1];
                $.activeValidatorSet.pop();
                break;
            }
        }
    }

    // ============ View functions ============

    function isActiveValidator(address validator) external view override returns (bool) {
        return _getStorage().validators[validator].status == ValidatorStatus.Active;
    }

    function getActiveValidatorSet() external view override returns (address[] memory) {
        return _getStorage().activeValidatorSet;
    }

    function getValidator(address operator) external view override returns (Validator memory) {
        return _getStorage().validators[operator];
    }

    function currentRelayer() external view override returns (address) {
        return _getStorage().currentRelayer;
    }

    function minimumStake() external view override returns (uint256) {
        return _getStorage().minimumStake;
    }

    function activeValidatorCount() external view override returns (uint256) {
        return _getStorage().activeValidatorSet.length;
    }
}
