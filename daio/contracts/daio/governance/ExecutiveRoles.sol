// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ExecutiveRoles
 * @notice Manages CEO and Seven Soldiers executive roles with hierarchical authority
 * @dev Implements weighted voting power and role-based access control for DAIO governance
 */
contract ExecutiveRoles is Ownable, AccessControl, ReentrancyGuard {

    // Executive role enumeration
    enum ExecutiveRole {
        NONE,           // 0 - No role assigned
        CEO,            // 1 - Chief Executive Officer
        CISO,           // 2 - Chief Information Security Officer
        CRO,            // 3 - Chief Risk Officer
        CFO,            // 4 - Chief Financial Officer
        CPO,            // 5 - Chief Product Officer
        COO,            // 6 - Chief Operations Officer
        CTO,            // 7 - Chief Technology Officer
        CLO             // 8 - Chief Legal Officer
    }

    // Executive structure
    struct Executive {
        address account;        // Wallet address of executive
        ExecutiveRole role;     // Specific executive role
        uint256 weight;         // Voting weight (basis points, e.g., 1000 = 10%)
        bool active;            // Whether executive is currently active
        bool hasVetoPower;      // Special veto power (CISO, CRO)
        uint256 appointedAt;    // Timestamp when appointed
        uint256 termLength;     // Term length in seconds (0 = indefinite)
        string metadata;        // IPFS hash or JSON metadata
    }

    // Role-based access control
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");
    bytes32 public constant CEO_ROLE = keccak256("CEO_ROLE");
    bytes32 public constant EXECUTIVE_ROLE = keccak256("EXECUTIVE_ROLE");

    // Storage
    mapping(address => Executive) public executives;
    mapping(ExecutiveRole => address) public roleHolders;  // Role => current holder
    mapping(ExecutiveRole => uint256) public roleWeights; // Default weights per role

    address[] public allExecutives;  // Array of all executive addresses
    uint256 public totalActiveWeight;    // Sum of all active executive weights
    uint256 public constant MAX_EXECUTIVES = 8;  // CEO + 7 soldiers
    uint256 public constant WEIGHT_PRECISION = 10000;  // 100% = 10000 basis points

    // Events
    event ExecutiveAppointed(
        address indexed account,
        ExecutiveRole indexed role,
        uint256 weight,
        bool hasVetoPower,
        uint256 termLength
    );
    event ExecutiveRemoved(
        address indexed account,
        ExecutiveRole indexed role
    );
    event ExecutiveActivated(address indexed account, ExecutiveRole indexed role);
    event ExecutiveDeactivated(address indexed account, ExecutiveRole indexed role);
    event RoleWeightUpdated(ExecutiveRole indexed role, uint256 oldWeight, uint256 newWeight);
    event EmergencyOverride(address indexed ceo, string reason);

    constructor(address _governance) Ownable(msg.sender) {
        require(_governance != address(0), "Invalid governance address");

        // Grant roles
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, _governance);

        // Initialize default role weights (basis points)
        _setDefaultRoleWeights();
    }

    /**
     * @notice Set default voting weights for each executive role
     */
    function _setDefaultRoleWeights() internal {
        roleWeights[ExecutiveRole.CEO] = 0;      // CEO has emergency override, not regular voting
        roleWeights[ExecutiveRole.CISO] = 1200;  // 12% - Higher weight for security
        roleWeights[ExecutiveRole.CRO] = 1200;   // 12% - Higher weight for risk
        roleWeights[ExecutiveRole.CFO] = 1000;   // 10%
        roleWeights[ExecutiveRole.CPO] = 1000;   // 10%
        roleWeights[ExecutiveRole.COO] = 1000;   // 10%
        roleWeights[ExecutiveRole.CTO] = 1000;   // 10%
        roleWeights[ExecutiveRole.CLO] = 800;    // 8% - Lower weight
        // Total: 76% (excluding CEO), 2/3 majority = ~50.7%
    }

    /**
     * @notice Appoint a new executive to a specific role
     * @param account Address of the executive
     * @param role Executive role to assign
     * @param termLength Term length in seconds (0 for indefinite)
     * @param metadata Additional metadata (IPFS hash, etc.)
     */
    function appointExecutive(
        address account,
        ExecutiveRole role,
        uint256 termLength,
        string memory metadata
    ) external onlyRole(GOVERNANCE_ROLE) nonReentrant {
        require(account != address(0), "Invalid account");
        require(role != ExecutiveRole.NONE, "Invalid role");
        require(roleHolders[role] == address(0), "Role already occupied");
        require(executives[account].role == ExecutiveRole.NONE, "Account already has role");
        require(allExecutives.length < MAX_EXECUTIVES, "Maximum executives reached");

        // Set veto power for security and risk roles
        bool hasVeto = (role == ExecutiveRole.CISO || role == ExecutiveRole.CRO);
        uint256 weight = roleWeights[role];

        // Create executive record
        executives[account] = Executive({
            account: account,
            role: role,
            weight: weight,
            active: true,
            hasVetoPower: hasVeto,
            appointedAt: block.timestamp,
            termLength: termLength,
            metadata: metadata
        });

        // Update mappings
        roleHolders[role] = account;
        allExecutives.push(account);

        // Update total weight (CEO doesn't count in regular voting)
        if (role != ExecutiveRole.CEO) {
            totalActiveWeight += weight;
        }

        // Grant appropriate access control roles
        _grantRole(EXECUTIVE_ROLE, account);
        if (role == ExecutiveRole.CEO) {
            _grantRole(CEO_ROLE, account);
        }

        emit ExecutiveAppointed(account, role, weight, hasVeto, termLength);
    }

    /**
     * @notice Remove an executive from their role
     * @param account Address of the executive to remove
     */
    function removeExecutive(address account) external onlyRole(GOVERNANCE_ROLE) nonReentrant {
        Executive storage exec = executives[account];
        require(exec.role != ExecutiveRole.NONE, "Not an executive");

        ExecutiveRole role = exec.role;
        uint256 weight = exec.weight;

        // Update total weight
        if (role != ExecutiveRole.CEO && exec.active) {
            totalActiveWeight -= weight;
        }

        // Clean up mappings
        roleHolders[role] = address(0);

        // Remove from allExecutives array
        for (uint i = 0; i < allExecutives.length; i++) {
            if (allExecutives[i] == account) {
                allExecutives[i] = allExecutives[allExecutives.length - 1];
                allExecutives.pop();
                break;
            }
        }

        // Revoke access control roles
        _revokeRole(EXECUTIVE_ROLE, account);
        if (role == ExecutiveRole.CEO) {
            _revokeRole(CEO_ROLE, account);
        }

        emit ExecutiveRemoved(account, role);

        // Clear executive record
        delete executives[account];
    }

    /**
     * @notice Activate or deactivate an executive
     * @param account Address of the executive
     * @param active Whether to activate (true) or deactivate (false)
     */
    function setExecutiveActive(address account, bool active) external onlyRole(GOVERNANCE_ROLE) {
        Executive storage exec = executives[account];
        require(exec.role != ExecutiveRole.NONE, "Not an executive");

        if (exec.active != active) {
            exec.active = active;

            // Update total weight (CEO doesn't count in regular voting)
            if (exec.role != ExecutiveRole.CEO) {
                if (active) {
                    totalActiveWeight += exec.weight;
                    emit ExecutiveActivated(account, exec.role);
                } else {
                    totalActiveWeight -= exec.weight;
                    emit ExecutiveDeactivated(account, exec.role);
                }
            } else {
                // CEO activation/deactivation
                if (active) {
                    emit ExecutiveActivated(account, exec.role);
                } else {
                    emit ExecutiveDeactivated(account, exec.role);
                }
            }
        }
    }

    /**
     * @notice Update the voting weight for a specific role
     * @param role Executive role to update
     * @param newWeight New voting weight in basis points
     */
    function updateRoleWeight(ExecutiveRole role, uint256 newWeight) external onlyRole(GOVERNANCE_ROLE) {
        require(role != ExecutiveRole.NONE && role != ExecutiveRole.CEO, "Invalid role");
        require(newWeight <= WEIGHT_PRECISION, "Weight exceeds maximum");

        uint256 oldWeight = roleWeights[role];
        roleWeights[role] = newWeight;

        // Update executive's weight if role is currently held
        address holder = roleHolders[role];
        if (holder != address(0)) {
            Executive storage exec = executives[holder];
            if (exec.active) {
                totalActiveWeight = totalActiveWeight - oldWeight + newWeight;
            }
            exec.weight = newWeight;
        }

        emit RoleWeightUpdated(role, oldWeight, newWeight);
    }

    /**
     * @notice CEO emergency override mechanism
     * @param reason Reason for emergency override
     */
    function emergencyOverride(string memory reason) external onlyRole(CEO_ROLE) {
        require(bytes(reason).length > 0, "Reason required");
        emit EmergencyOverride(msg.sender, reason);
        // Note: Actual override logic implemented in ExecutiveGovernance
    }

    /**
     * @notice Check if an address is an active executive
     * @param account Address to check
     * @return bool Whether the address is an active executive
     */
    function isActiveExecutive(address account) external view returns (bool) {
        return executives[account].role != ExecutiveRole.NONE && executives[account].active;
    }

    /**
     * @notice Get executive details for an address
     * @param account Address to query
     * @return Executive struct
     */
    function getExecutive(address account) external view returns (Executive memory) {
        return executives[account];
    }

    /**
     * @notice Get the current holder of a specific role
     * @param role Executive role to query
     * @return address Current role holder (address(0) if vacant)
     */
    function getRoleHolder(ExecutiveRole role) external view returns (address) {
        return roleHolders[role];
    }

    /**
     * @notice Get all active executive addresses
     * @return address[] Array of active executive addresses
     */
    function getActiveExecutives() external view returns (address[] memory) {
        address[] memory active = new address[](allExecutives.length);
        uint256 count = 0;

        for (uint i = 0; i < allExecutives.length; i++) {
            if (executives[allExecutives[i]].active) {
                active[count] = allExecutives[i];
                count++;
            }
        }

        // Resize array to actual count
        assembly {
            mstore(active, count)
        }

        return active;
    }

    /**
     * @notice Calculate 2/3 majority threshold for Seven Soldiers voting
     * @return uint256 Required voting weight for 2/3 majority
     */
    function calculateMajorityThreshold() external view returns (uint256) {
        // 2/3 of total active weight (excluding CEO)
        return (totalActiveWeight * 2) / 3;
    }

    /**
     * @notice Check if Seven Soldiers have quorum (majority of executives active)
     * @return bool Whether quorum is met
     */
    function hasQuorum() external view returns (bool) {
        uint256 activeCount = 0;
        for (uint i = 0; i < allExecutives.length; i++) {
            if (executives[allExecutives[i]].active &&
                executives[allExecutives[i]].role != ExecutiveRole.CEO) {
                activeCount++;
            }
        }
        return activeCount >= 4; // Majority of 7 soldiers = 4
    }

    /**
     * @notice Check if term has expired for an executive
     * @param account Executive address to check
     * @return bool Whether term has expired
     */
    function isTermExpired(address account) external view returns (bool) {
        Executive memory exec = executives[account];
        if (exec.termLength == 0) return false; // Indefinite term
        return block.timestamp >= exec.appointedAt + exec.termLength;
    }

    /**
     * @notice Batch check term expiration for all executives
     * @return address[] Array of executives with expired terms
     */
    function getExpiredExecutives() external view returns (address[] memory) {
        address[] memory expired = new address[](allExecutives.length);
        uint256 count = 0;

        for (uint i = 0; i < allExecutives.length; i++) {
            address exec = allExecutives[i];
            Executive memory execData = executives[exec];
            if (execData.termLength > 0 &&
                block.timestamp >= execData.appointedAt + execData.termLength) {
                expired[count] = exec;
                count++;
            }
        }

        // Resize array
        assembly {
            mstore(expired, count)
        }

        return expired;
    }

    /**
     * @notice Get voting statistics for Seven Soldiers consensus
     * @return totalWeight Total voting weight of active Seven Soldiers
     * @return majorityThreshold Required weight for 2/3 majority
     * @return activeExecutiveCount Number of active Seven Soldiers
     */
    function getVotingStats() external view returns (
        uint256 totalWeight,
        uint256 majorityThreshold,
        uint256 activeExecutiveCount
    ) {
        totalWeight = totalActiveWeight;
        majorityThreshold = (totalWeight * 2) / 3;

        for (uint i = 0; i < allExecutives.length; i++) {
            if (executives[allExecutives[i]].active &&
                executives[allExecutives[i]].role != ExecutiveRole.CEO) {
                activeExecutiveCount++;
            }
        }
    }
}