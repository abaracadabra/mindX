// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IOpenBDKValidatorRegistry
 * @notice Interface for the openBDK Relayer-Validator registry
 * @dev openBDK v1 topology: 1 Relayer + 3 Validators, 2/3 vote consensus
 *      Validator privilege requires minimum token stake (token-gated)
 *
 *      Architecture:
 *      - The Relayer proposes blocks (the +1 in 3f+1) but does NOT vote
 *      - 3 Validators form the consensus committee (2/3 = 2 of 3 must approve)
 *      - 1 Validator can be Byzantine without halting consensus
 *      - 1 Validator can be down for maintenance without halting consensus
 *
 *      This is the minimum viable BFT deployment per Lamport's 3f+1 theorem.
 *
 * @custom:security-contact security@openbdk.org
 */
interface IOpenBDKValidatorRegistry {
    enum ValidatorStatus {
        None,        // Never registered
        Candidate,   // Staked but not active
        Active,      // In active validator set
        Slashed,     // Penalized for misbehavior
        Exited       // Voluntarily withdrew
    }

    struct Validator {
        address operator;            // Node operator address
        uint256 stakedAmount;        // Tokens locked in staking
        uint256 activeSince;         // Block number when activated
        uint256 rewardsAccumulated;  // Earned but unclaimed rewards
        uint256 fidesScore;          // BONAFIDE reputation score
        ValidatorStatus status;
    }

    /// @notice Register as a Validator candidate by staking minimum tokens
    function registerValidator() external;

    /// @notice Relayer activates a registered Validator into the active set
    /// @dev Only callable by the current Relayer; max 3 active in v1
    function activateValidator(address validator) external;

    /// @notice Voluntarily exit the validator set; tokens unlock after unbondingPeriod
    function exitValidator() external;

    /// @notice Distribute block rewards to approving validators
    /// @dev Called by the consensus contract after block finalization
    function distributeRewards(address[] calldata approvers, uint256 blockReward) external;

    /// @notice Slash a misbehaving validator by confiscating staked tokens
    function slash(address validator, uint256 amount, string calldata reason) external;

    /// @notice Claim accumulated rewards
    function claimRewards() external returns (uint256);

    /// @notice Rotate the Relayer role; triggered after N consecutive proposal failures
    function rotateRelayer(address newRelayer) external;

    // ============ View functions ============

    function isActiveValidator(address validator) external view returns (bool);
    function getActiveValidatorSet() external view returns (address[] memory);
    function getValidator(address operator) external view returns (Validator memory);
    function currentRelayer() external view returns (address);
    function minimumStake() external view returns (uint256);
    function activeValidatorCount() external view returns (uint256);

    // ============ Events ============

    event ValidatorRegistered(address indexed operator, uint256 stakedAmount);
    event ValidatorActivated(address indexed operator, address indexed activatedBy);
    event ValidatorExited(address indexed operator, uint256 unbondingEnd);
    event ValidatorSlashed(address indexed operator, uint256 amount, string reason);
    event RewardsDistributed(address[] approvers, uint256 totalReward);
    event RewardsClaimed(address indexed operator, uint256 amount);
    event RelayerRotated(address indexed oldRelayer, address indexed newRelayer);
}
