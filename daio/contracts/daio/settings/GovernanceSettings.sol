// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title GovernanceSettings
 * @notice Manages configurable governance parameters for DAIO
 * @dev Allows updating governance settings via proposals
 */
contract GovernanceSettings is Ownable {
    struct Settings {
        uint256 votingPeriod;        // Blocks for voting period
        uint256 quorumThreshold;     // Basis points (e.g., 5000 = 50%)
        uint256 approvalThreshold;   // Basis points (e.g., 5000 = 50%)
        uint256 timelockDelay;      // Blocks for timelock delay
        uint256 proposalThreshold;   // Minimum voting power to create proposal
        uint256 minVotingPower;      // Minimum voting power to vote
    }

    Settings public settings;
    
    // Project-specific settings
    mapping(string => Settings) public projectSettings;
    
    event SettingsUpdated(
        string indexed projectId,
        uint256 votingPeriod,
        uint256 quorumThreshold,
        uint256 approvalThreshold,
        uint256 timelockDelay
    );

    constructor(
        uint256 _votingPeriod,
        uint256 _quorumThreshold,
        uint256 _approvalThreshold,
        uint256 _timelockDelay,
        uint256 _proposalThreshold,
        uint256 _minVotingPower
    ) Ownable(msg.sender) {
        settings = Settings({
            votingPeriod: _votingPeriod,
            quorumThreshold: _quorumThreshold,
            approvalThreshold: _approvalThreshold,
            timelockDelay: _timelockDelay,
            proposalThreshold: _proposalThreshold,
            minVotingPower: _minVotingPower
        });
    }

    /**
     * @notice Update global governance settings
     */
    function updateSettings(
        uint256 _votingPeriod,
        uint256 _quorumThreshold,
        uint256 _approvalThreshold,
        uint256 _timelockDelay,
        uint256 _proposalThreshold,
        uint256 _minVotingPower
    ) external onlyOwner {
        require(_quorumThreshold <= 10000, "Invalid quorum threshold");
        require(_approvalThreshold <= 10000, "Invalid approval threshold");
        require(_votingPeriod > 0, "Invalid voting period");
        
        settings = Settings({
            votingPeriod: _votingPeriod,
            quorumThreshold: _quorumThreshold,
            approvalThreshold: _approvalThreshold,
            timelockDelay: _timelockDelay,
            proposalThreshold: _proposalThreshold,
            minVotingPower: _minVotingPower
        });

        emit SettingsUpdated("", _votingPeriod, _quorumThreshold, _approvalThreshold, _timelockDelay);
    }

    /**
     * @notice Update project-specific settings
     */
    function updateProjectSettings(
        string memory projectId,
        uint256 _votingPeriod,
        uint256 _quorumThreshold,
        uint256 _approvalThreshold,
        uint256 _timelockDelay,
        uint256 _proposalThreshold,
        uint256 _minVotingPower
    ) external onlyOwner {
        require(_quorumThreshold <= 10000, "Invalid quorum threshold");
        require(_approvalThreshold <= 10000, "Invalid approval threshold");
        require(_votingPeriod > 0, "Invalid voting period");
        
        projectSettings[projectId] = Settings({
            votingPeriod: _votingPeriod,
            quorumThreshold: _quorumThreshold,
            approvalThreshold: _approvalThreshold,
            timelockDelay: _timelockDelay,
            proposalThreshold: _proposalThreshold,
            minVotingPower: _minVotingPower
        });

        emit SettingsUpdated(projectId, _votingPeriod, _quorumThreshold, _approvalThreshold, _timelockDelay);
    }

    /**
     * @notice Get settings for a project (returns project-specific or global)
     */
    function getSettings(string memory projectId) external view returns (Settings memory) {
        Settings memory project = projectSettings[projectId];
        // If project has custom settings, return them; otherwise return global
        if (project.votingPeriod > 0) {
            return project;
        }
        return settings;
    }
}
