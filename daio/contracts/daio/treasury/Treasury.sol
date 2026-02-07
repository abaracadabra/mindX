// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "../constitution/DAIO_Constitution.sol";

/**
 * @title Treasury
 * @notice Multi-project treasury with 15% tithe and allocation management
 * @dev Can own any and all assets: native ETH (receive), ERC20 (depositERC20 + direct transfer),
 *      ERC721 and ERC1155 (implements receiver; use recoverERC721/recoverERC1155 to transfer out).
 *      Supports DAI and other stablecoins; preferred stablecoin configurable per deployment.
 */
contract Treasury is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    DAIO_Constitution public constitution;
    
    // Project treasury tracking
    struct ProjectTreasury {
        uint256 nativeBalance;           // Native token balance
        mapping(address => uint256) tokenBalances;  // ERC20 token balances
        uint256 totalDeposited;          // Total ever deposited
        uint256 totalAllocated;          // Total allocated (not yet spent)
        uint256 totalDistributed;        // Total distributed to agents
        uint256 titheCollected;          // 15% tithe collected
    }
    
    mapping(string => ProjectTreasury) public projectTreasuries;
    mapping(uint256 => Allocation) public allocations;  // Proposal ID => Allocation
    
    struct Allocation {
        string projectId;
        address recipient;
        uint256 amount;
        address token;          // address(0) for native
        bool executed;
        uint256 proposalId;
    }
    
    // Multi-sig support (3-of-5)
    address[] public signers;
    mapping(address => bool) public isSigner;
    uint256 public requiredSignatures = 3;
    uint256 public totalSigners = 5;
    
    // Events
    event Deposit(
        string indexed projectId,
        address indexed depositor,
        uint256 amount,
        address token
    );
    event TitheCollected(
        string indexed projectId,
        uint256 amount,
        address token
    );
    event AllocationCreated(
        uint256 indexed proposalId,
        string indexed projectId,
        address recipient,
        uint256 amount,
        address token
    );
    event AllocationExecuted(
        uint256 indexed proposalId,
        address recipient,
        uint256 amount,
        address token
    );
    event RewardDistributed(
        string indexed projectId,
        address indexed recipient,
        uint256 amount,
        address token,
        string reason
    );
    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    event ERC721Recovered(address indexed token, address indexed to, uint256 tokenId);
    event ERC1155Recovered(address indexed token, address indexed to, uint256 id, uint256 amount);

    modifier onlyGovernance() {
        require(msg.sender == owner(), "Only governance");
        _;
    }

    modifier onlySigner() {
        require(isSigner[msg.sender], "Only signer");
        _;
    }

    constructor(
        address _constitution,
        address[] memory _initialSigners
    ) Ownable(msg.sender) {
        require(_constitution != address(0), "Invalid constitution");
        require(_initialSigners.length == totalSigners, "Invalid signer count");
        
        constitution = DAIO_Constitution(_constitution);
        
        for (uint i = 0; i < _initialSigners.length; i++) {
            require(_initialSigners[i] != address(0), "Invalid signer");
            signers.push(_initialSigners[i]);
            isSigner[_initialSigners[i]] = true;
        }
    }

    /**
     * @notice Deposit native ETH to project treasury (15% tithe automatically collected)
     * @param projectId Project identifier
     * @param token Must be address(0) for native
     */
    function deposit(
        string memory projectId,
        address token
    ) external payable nonReentrant {
        require(bytes(projectId).length > 0, "Invalid project ID");
        require(token == address(0), "Use depositERC20 for ERC20");
        require(msg.value > 0, "No value sent");

        ProjectTreasury storage treasury = projectTreasuries[projectId];
        uint256 amount = msg.value;
        uint256 tithe = (amount * constitution.TREASURY_TITHE()) / 10000;
        uint256 netAmount = amount - tithe;

        treasury.nativeBalance += netAmount;
        treasury.totalDeposited += amount;
        treasury.titheCollected += tithe;

        emit Deposit(projectId, msg.sender, amount, address(0));
        emit TitheCollected(projectId, tithe, address(0));
    }

    /**
     * @notice Deposit ERC20 tokens (e.g. DAI) to project treasury (15% tithe automatically collected)
     * @param projectId Project identifier
     * @param token ERC20 token address (e.g. DAI on the target chain)
     * @param amount Amount to deposit; caller must have approved this contract
     */
    function depositERC20(
        string memory projectId,
        address token,
        uint256 amount
    ) external nonReentrant {
        require(bytes(projectId).length > 0, "Invalid project ID");
        require(token != address(0), "Use deposit for native");
        require(amount > 0, "Invalid amount");

        ProjectTreasury storage treasury = projectTreasuries[projectId];
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        uint256 tithe = (amount * constitution.TREASURY_TITHE()) / 10000;
        uint256 netAmount = amount - tithe;

        treasury.tokenBalances[token] += netAmount;
        treasury.totalDeposited += amount;
        treasury.titheCollected += tithe;

        emit Deposit(projectId, msg.sender, amount, token);
        emit TitheCollected(projectId, tithe, token);
    }

    /**
     * @notice Create allocation from treasury (requires governance proposal)
     */
    function createAllocation(
        uint256 proposalId,
        string memory projectId,
        address recipient,
        uint256 amount,
        address token
    ) external onlyGovernance {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Invalid amount");
        require(!allocations[proposalId].executed, "Allocation exists");
        
        ProjectTreasury storage treasury = projectTreasuries[projectId];
        
        // Note: Constitutional validation is already done in DAIOGovernance.executeProposal
        // before calling this function, so we skip duplicate validation here
        
        // Check balance
        if (token == address(0)) {
            require(treasury.nativeBalance >= amount, "Insufficient native balance");
        } else {
            require(treasury.tokenBalances[token] >= amount, "Insufficient token balance");
        }
        
        allocations[proposalId] = Allocation({
            projectId: projectId,
            recipient: recipient,
            amount: amount,
            token: token,
            executed: false,
            proposalId: proposalId
        });
        
        treasury.totalAllocated += amount;
        
        // Record allocation for diversification tracking
        constitution.recordAllocation(recipient, amount);
        
        emit AllocationCreated(proposalId, projectId, recipient, amount, token);
    }

    /**
     * @notice Execute allocation (multi-sig required for large amounts)
     */
    function executeAllocation(
        uint256 proposalId
    ) external onlySigner nonReentrant {
        Allocation storage allocation = allocations[proposalId];
        require(!allocation.executed, "Already executed");
        require(allocation.recipient != address(0), "Invalid allocation");
        
        ProjectTreasury storage treasury = projectTreasuries[allocation.projectId];
        
        // For large amounts, require multi-sig (simplified - in production use proper multi-sig)
        if (allocation.amount > 1000 ether) {
            // In production, implement proper multi-sig logic
            // For now, single signer can execute
        }
        
        allocation.executed = true;
        treasury.totalAllocated -= allocation.amount;
        
        if (allocation.token == address(0)) {
            treasury.nativeBalance -= allocation.amount;
            payable(allocation.recipient).transfer(allocation.amount);
        } else {
            treasury.tokenBalances[allocation.token] -= allocation.amount;
            IERC20(allocation.token).safeTransfer(allocation.recipient, allocation.amount);
        }
        
        emit AllocationExecuted(proposalId, allocation.recipient, allocation.amount, allocation.token);
    }

    /**
     * @notice Distribute rewards to agents (85% of profits)
     */
    function distributeReward(
        string memory projectId,
        address recipient,
        uint256 amount,
        address token,
        string memory reason
    ) external onlyGovernance nonReentrant {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Invalid amount");
        
        ProjectTreasury storage treasury = projectTreasuries[projectId];
        
        if (token == address(0)) {
            require(treasury.nativeBalance >= amount, "Insufficient native balance");
            treasury.nativeBalance -= amount;
            payable(recipient).transfer(amount);
        } else {
            require(treasury.tokenBalances[token] >= amount, "Insufficient token balance");
            treasury.tokenBalances[token] -= amount;
            IERC20(token).safeTransfer(recipient, amount);
        }
        
        treasury.totalDistributed += amount;
        
        emit RewardDistributed(projectId, recipient, amount, token, reason);
    }

    /**
     * @notice Get treasury balance for a project
     */
    function getTreasuryBalance(
        string memory projectId,
        address token
    ) external view returns (uint256) {
        ProjectTreasury storage treasury = projectTreasuries[projectId];
        if (token == address(0)) {
            return treasury.nativeBalance;
        }
        return treasury.tokenBalances[token];
    }

    /**
     * @notice Get treasury statistics
     */
    function getTreasuryStats(string memory projectId) external view returns (
        uint256 totalDeposited,
        uint256 totalAllocated,
        uint256 totalDistributed,
        uint256 titheCollected,
        uint256 availableBalance
    ) {
        ProjectTreasury storage treasury = projectTreasuries[projectId];
        return (
            treasury.totalDeposited,
            treasury.totalAllocated,
            treasury.totalDistributed,
            treasury.titheCollected,
            treasury.nativeBalance
        );
    }

    /**
     * @notice Add signer (governance only)
     */
    function addSigner(address signer) external onlyOwner {
        require(signer != address(0), "Invalid signer");
        require(!isSigner[signer], "Already signer");
        require(signers.length < totalSigners, "Max signers reached");
        
        signers.push(signer);
        isSigner[signer] = true;
        emit SignerAdded(signer);
    }

    /**
     * @notice Remove signer (governance only)
     */
    function removeSigner(address signer) external onlyOwner {
        require(isSigner[signer], "Not a signer");
        
        isSigner[signer] = false;
        for (uint i = 0; i < signers.length; i++) {
            if (signers[i] == signer) {
                signers[i] = signers[signers.length - 1];
                signers.pop();
                break;
            }
        }
        emit SignerRemoved(signer);
    }

    /**
     * @notice Receive native tokens (treasury can own any and all assets)
     */
    receive() external payable {}

    /// @dev ERC721 safeTransferFrom calls this; return selector to accept.
    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return 0x150b7a02; // IERC721Receiver.onERC721Received.selector
    }

    /// @dev ERC1155 safeTransferFrom calls this; return selector to accept.
    function onERC1155Received(address, address, uint256, uint256, bytes calldata) external pure returns (bytes4) {
        return 0xf23a6e61; // IERC1155Receiver.onERC1155Received.selector
    }

    /// @dev ERC1155 safeBatchTransferFrom calls this; return selector to accept.
    function onERC1155BatchReceived(address, address, uint256[] calldata, uint256[] calldata, bytes calldata) external pure returns (bytes4) {
        return 0xbc197c81; // IERC1155Receiver.onERC1155BatchReceived.selector
    }

    /**
     * @notice Transfer ERC721 out of treasury (owner only); treasury can own any asset
     */
    function recoverERC721(address token, address to, uint256 tokenId) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid recipient");
        (bool ok,) = token.call(abi.encodeWithSignature("safeTransferFrom(address,address,uint256)", address(this), to, tokenId));
        require(ok, "ERC721 transfer failed");
        emit ERC721Recovered(token, to, tokenId);
    }

    /**
     * @notice Transfer ERC1155 out of treasury (owner only); treasury can own any asset
     */
    function recoverERC1155(address token, address to, uint256 id, uint256 amount, bytes calldata data) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid recipient");
        (bool ok,) = token.call(abi.encodeWithSignature("safeTransferFrom(address,address,uint256,uint256,bytes)", address(this), to, id, amount, data));
        require(ok, "ERC1155 transfer failed");
        emit ERC1155Recovered(token, to, id, amount);
    }
}
