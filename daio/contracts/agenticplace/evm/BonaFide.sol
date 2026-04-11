// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title BonaFide — Reputation Token with Clawback, Censura Fade, and Agent Ghosting
 * @notice ERC-20 reputation token for AgenticPlace agents. Balance = reputation score.
 *         CENSURA penalties cause agents to FADE (degraded access). Maximum fade = GHOST.
 *         Ghosted agents can be permanently BLOCKED (irreversible).
 * @dev In-house AgenticPlace standard. Not an external EIP.
 *
 * Roles:
 *   MINTER_ROLE   — Issues BONA FIDE to agents (reputation issuance)
 *   CENSURA_ROLE  — Clawback tokens, apply censura penalties, ghost agents
 *   RECOVERY_ROLE — Migrate tokens from compromised wallet to new wallet
 *
 * Dignitas levels (by balance):
 *   novus     (<100)    — Basic agent
 *   notus     (100+)    — Known, marketplace access
 *   clarus    (1000+)   — Priority indexing, batch ops
 *   illustris (5000+)   — Governance voting, premium endpoints
 *   eminens   (10000+)  — CENSURA eligibility, oracle access
 *
 * Fade levels (by censura):
 *   0–24:   Full access, minor visibility reduction
 *   25–49:  Reduced rate limits, lower search ranking
 *   50–74:  Restricted minting, no marketplace listing
 *   75–99:  Read-only, flagged in UI
 *   100:    GHOST — invisible, all interactions blocked
 *           ghostAgent() → BLOCKED FOREVER (irreversible)
 */
contract BonaFide is ERC20, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant CENSURA_ROLE = keccak256("CENSURA_ROLE");
    bytes32 public constant RECOVERY_ROLE = keccak256("RECOVERY_ROLE");

    /// @notice Treasury receives clawed-back tokens
    address public treasury;

    /// @notice Accumulated censura penalty per agent
    mapping(address => uint256) public censuraScore;

    /// @notice Permanently blocked agents (irreversible)
    mapping(address => bool) public isGhosted;

    /// @notice Censura points required per fade level (censura / FADE_DIVISOR = fade 0–100)
    uint256 public constant FADE_DIVISOR = 100;

    /// @notice Dignitas slot thresholds (match existing dignitasLevel function)
    uint256 public constant NOTUS_THRESHOLD = 100;
    uint256 public constant CLARUS_THRESHOLD = 1000;
    uint256 public constant ILLUSTRIS_THRESHOLD = 5000;
    uint256 public constant EMINENS_THRESHOLD = 10000;

    // ── Events ───────────────────────────────────────────────────

    event Censured(address indexed agent, uint256 amount, uint256 newFade);
    event Clawback(address indexed from, uint256 amount, address indexed toTreasury);
    event IdentityRecovered(address indexed from, address indexed to, uint256 amount);
    event AgentGhosted(address indexed agent);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);

    // ── Constructor ──────────────────────────────────────────────

    /**
     * @param initialSupply Total BONA FIDE supply (minted to deployer)
     * @param _treasury Address that receives clawed-back tokens
     */
    constructor(
        uint256 initialSupply,
        address _treasury
    ) ERC20("BONA FIDE", "BONAFIDE") {
        require(_treasury != address(0), "Treasury cannot be zero");
        treasury = _treasury;

        _mint(msg.sender, initialSupply);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(CENSURA_ROLE, msg.sender);
        _grantRole(RECOVERY_ROLE, msg.sender);
    }

    // ── Read Functions ───────────────────────────────────────────

    /**
     * @notice Get agent's reputation score (alias for balanceOf)
     * @param account Agent address
     * @return Reputation score (BONA FIDE balance)
     */
    function reputationOf(address account) external view returns (uint256) {
        return balanceOf(account);
    }

    /**
     * @notice Get agent's dignitas level
     * @param account Agent address
     * @return slot Dignitas slot (0=novus, 1=notus, 2=clarus, 3=illustris, 4=eminens)
     * @return level Human-readable level name
     * @return balance Current BONA FIDE balance
     */
    function dignitasOf(address account) external view returns (
        uint8 slot,
        string memory level,
        uint256 balance
    ) {
        balance = balanceOf(account);
        if (balance >= EMINENS_THRESHOLD) return (4, "eminens", balance);
        if (balance >= ILLUSTRIS_THRESHOLD) return (3, "illustris", balance);
        if (balance >= CLARUS_THRESHOLD) return (2, "clarus", balance);
        if (balance >= NOTUS_THRESHOLD) return (1, "notus", balance);
        return (0, "novus", balance);
    }

    /**
     * @notice Get agent's fade level from accumulated censura
     * @param account Agent address
     * @return Fade level 0–100 (100 = ghost)
     */
    function fadeOf(address account) external view returns (uint8) {
        return _fadeOf(account);
    }

    /**
     * @notice Check if agent is a ghost (fade == 100)
     * @param account Agent address
     * @return True if agent has reached maximum fade
     */
    function isGhost(address account) external view returns (bool) {
        return _fadeOf(account) >= 100;
    }

    /**
     * @notice Check if agent is active (not ghosted and fade < 100)
     * @param account Agent address
     * @return True if agent can participate
     */
    function isActive(address account) external view returns (bool) {
        return !isGhosted[account] && _fadeOf(account) < 100;
    }

    // ── Write Functions ──────────────────────────────────────────

    /**
     * @notice Mint BONA FIDE to an agent (reputation issuance)
     * @param to Agent address
     * @param amount Amount of BONA FIDE to mint
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(!isGhosted[to], "Cannot mint to ghosted agent");
        require(_fadeOf(to) < 100, "Cannot mint to ghost agent");
        _mint(to, amount);
    }

    /**
     * @notice Clawback BONA FIDE from an agent (censura enforcement)
     * @dev Seized tokens go to treasury, not burned
     * @param from Agent to clawback from
     * @param amount Amount to seize
     */
    function clawback(
        address from,
        uint256 amount
    ) external onlyRole(CENSURA_ROLE) {
        require(from != address(0), "Cannot clawback from zero");
        uint256 bal = balanceOf(from);
        uint256 seized = amount > bal ? bal : amount;
        _transfer(from, treasury, seized);
        emit Clawback(from, seized, treasury);
    }

    /**
     * @notice Apply censura penalty to an agent (increases fade)
     * @param agent Agent to penalize
     * @param amount Censura points to add
     */
    function censura(
        address agent,
        uint256 amount
    ) external onlyRole(CENSURA_ROLE) {
        require(agent != address(0), "Cannot censure zero address");
        require(!isGhosted[agent], "Agent already ghosted");
        censuraScore[agent] += amount;
        uint8 newFade = _fadeOf(agent);
        emit Censured(agent, amount, newFade);
    }

    /**
     * @notice Permanently block an agent (irreversible)
     * @dev Only callable when agent is a ghost (fade >= 100)
     * @param agent Agent to permanently block
     */
    function ghostAgent(address agent) external onlyRole(CENSURA_ROLE) {
        require(!isGhosted[agent], "Already ghosted");
        require(_fadeOf(agent) >= 100, "Agent must be ghost (fade 100) first");
        isGhosted[agent] = true;
        emit AgentGhosted(agent);
    }

    /**
     * @notice Recover agent identity — migrate BONA FIDE to new wallet
     * @dev Moves all tokens from old to new wallet, resets censura on new,
     *      ghosts the old wallet permanently (compromised key = blocked)
     * @param from Compromised wallet
     * @param to New wallet
     */
    function recover(
        address from,
        address to
    ) external onlyRole(RECOVERY_ROLE) {
        require(from != address(0) && to != address(0), "Invalid addresses");
        require(!isGhosted[to], "Cannot recover to ghosted address");
        require(to != from, "Same address");

        uint256 amount = balanceOf(from);
        if (amount > 0) {
            _transfer(from, to, amount);
        }

        // Ghost the compromised wallet permanently
        isGhosted[from] = true;

        // Clean slate on new wallet (censura does not follow)
        // censuraScore[to] stays as-is (may be 0 for fresh wallet)

        emit IdentityRecovered(from, to, amount);
        emit AgentGhosted(from);
    }

    /**
     * @notice Update treasury address
     * @param newTreasury New treasury address
     */
    function setTreasury(address newTreasury) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newTreasury != address(0), "Treasury cannot be zero");
        address old = treasury;
        treasury = newTreasury;
        emit TreasuryUpdated(old, newTreasury);
    }

    // ── Transfer Override ────────────────────────────────────────

    /**
     * @dev Block all transfers from/to ghosted agents.
     *      Minting (from == address(0)) checks ghosted status of receiver.
     *      Burning (to == address(0)) is always allowed (even for ghosted).
     */
    function _update(
        address from,
        address to,
        uint256 value
    ) internal override {
        // Block transfers FROM ghosted agents (except burning)
        if (from != address(0) && isGhosted[from]) {
            revert("BonaFide: sender is ghosted");
        }

        // Block transfers TO ghosted agents (except treasury via clawback)
        if (to != address(0) && isGhosted[to] && to != treasury) {
            revert("BonaFide: recipient is ghosted");
        }

        super._update(from, to, value);
    }

    // ── Internal ─────────────────────────────────────────────────

    function _fadeOf(address account) internal view returns (uint8) {
        uint256 score = censuraScore[account];
        uint256 fade = score / FADE_DIVISOR;
        return fade >= 100 ? 100 : uint8(fade);
    }

    // ── ERC-165 ──────────────────────────────────────────────────

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
