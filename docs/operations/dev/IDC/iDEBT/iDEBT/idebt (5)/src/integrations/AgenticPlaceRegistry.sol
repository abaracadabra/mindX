// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";

import { IAgenticPlace } from "../interfaces/IAgenticPlace.sol";

/// @title AgenticPlaceRegistry
/// @notice ERC-8004-style identity & reputation registry for agents serving
///         iDEBT holders (underwriters, advisors, automated heirs, etc.).
///         Backed off-chain by agenticplace.pythai.net.
/// @dev    Reputation uses an additive BONAFIDE score with decay over time to
///         avoid reputation inflation. Slashing drains stake-equivalent score.
contract AgenticPlaceRegistry is IAgenticPlace, AccessControl {
    bytes32 public constant ATTESTER_ROLE = keccak256("ATTESTER_ROLE");
    bytes32 public constant SLASHER_ROLE  = keccak256("SLASHER_ROLE");

    uint256 public constant DECAY_INTERVAL = 30 days;
    uint256 public decayBps = 100; // 1% per DECAY_INTERVAL

    mapping(bytes32 => Agent)  private _agents;
    mapping(address => bytes32) public agentOwnedBy;

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ATTESTER_ROLE, admin);
        _grantRole(SLASHER_ROLE, admin);
    }

    // -------------------------------------------------------------- //
    //                          REGISTRATION                          //
    // -------------------------------------------------------------- //

    function register(bytes32 agentId, string calldata endpoint) external {
        if (_agents[agentId].registeredAt != 0) revert AgentExists();
        _agents[agentId] = Agent({
            agentId:      agentId,
            owner:        msg.sender,
            reputation:   1e18,     // start at 1.0
            registeredAt: uint64(block.timestamp),
            lastActivity: uint64(block.timestamp),
            endpoint:     endpoint
        });
        agentOwnedBy[msg.sender] = agentId;
        emit AgentRegistered(agentId, msg.sender, endpoint);
    }

    function updateEndpoint(bytes32 agentId, string calldata endpoint) external {
        Agent storage a = _agents[agentId];
        if (a.owner != msg.sender) revert NotAuthorized();
        a.endpoint = endpoint;
        a.lastActivity = uint64(block.timestamp);
    }

    // -------------------------------------------------------------- //
    //                           REPUTATION                           //
    // -------------------------------------------------------------- //

    function attest(bytes32 agentId, uint128 delta) external onlyRole(ATTESTER_ROLE) {
        Agent storage a = _agents[agentId];
        if (a.registeredAt == 0) revert UnknownAgent();
        _applyDecay(a);
        a.reputation += delta;
        a.lastActivity = uint64(block.timestamp);
        emit AgentAttested(agentId, delta, msg.sender);
    }

    function slash(bytes32 agentId, uint128 amount, string calldata reason)
        external
        onlyRole(SLASHER_ROLE)
    {
        Agent storage a = _agents[agentId];
        if (a.registeredAt == 0) revert UnknownAgent();
        _applyDecay(a);
        a.reputation = amount >= a.reputation ? 0 : a.reputation - amount;
        a.lastActivity = uint64(block.timestamp);
        emit AgentSlashed(agentId, amount, reason);
    }

    function setDecay(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bps <= 5_000, "decay too high");
        decayBps = bps;
    }

    // -------------------------------------------------------------- //
    //                              VIEWS                             //
    // -------------------------------------------------------------- //

    function agentOf(bytes32 agentId) external view returns (Agent memory a) {
        a = _agents[agentId];
        if (a.registeredAt == 0) return a;
        a.reputation = _projectedReputation(a);
    }

    function reputationOf(bytes32 agentId) external view returns (uint128) {
        Agent memory a = _agents[agentId];
        if (a.registeredAt == 0) return 0;
        return _projectedReputation(a);
    }

    // -------------------------------------------------------------- //
    //                            INTERNAL                            //
    // -------------------------------------------------------------- //

    function _applyDecay(Agent storage a) internal {
        a.reputation = _projectedReputation(a);
        a.lastActivity = uint64(block.timestamp);
    }

    function _projectedReputation(Agent memory a) internal view returns (uint128) {
        if (a.reputation == 0) return 0;
        uint256 elapsed = block.timestamp - a.lastActivity;
        uint256 periods = elapsed / DECAY_INTERVAL;
        if (periods == 0) return a.reputation;
        uint256 rep = a.reputation;
        // Apply up to 64 periods of decay; beyond that cap to avoid gas blow-up.
        if (periods > 64) periods = 64;
        for (uint256 i = 0; i < periods; ++i) {
            rep = rep - (rep * decayBps) / 10_000;
            if (rep == 0) break;
        }
        return uint128(rep);
    }
}
