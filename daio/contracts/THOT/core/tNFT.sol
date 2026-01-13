// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title tNFT - THINK NFT with Decision-Making
 * @notice THINK NFT that can make decisions and process external data
 */
contract tNFT is ERC1155, Ownable {
    using Strings for uint256;

    enum DecisionState { IDLE, PROCESSING, COMPLETED, FAILED }

    struct ThinkData {
        string prompt;          // Main user prompt
        string agentPrompt;     // AI/Agent Execution prompt
        uint40 lastUpdate;      // Timestamp of last state update
        bool active;            // Is the NFT active?
        uint8 dimensions;       // Think dimensions (e.g., embedding size)
        uint16 batchSize;       // Size of processing batch
        DecisionState state;    // Current decision-making state
        string lastDecision;    // Last computed decision outcome
    }

    mapping(uint256 => ThinkData) private _thinkData;
    uint256 private _thinkIdCounter;

    event ThinkCreated(uint256 indexed thinkId, string prompt, uint8 dimensions, uint16 batchSize);
    event ThinkUpdated(uint256 indexed thinkId, string newPrompt, uint40 timestamp);
    event DecisionMade(uint256 indexed thinkId, string decision, uint40 timestamp);

    constructor() ERC1155("") Ownable(msg.sender) {
        _thinkIdCounter = 1;
    }

    /**
     * @dev Creates a new Think NFT batch.
     * @param recipient Recipient address.
     * @param prompt User-defined prompt.
     * @param agentPrompt Agent execution prompt.
     * @param dimensions Dimensionality (e.g., embedding size).
     * @param batchSize Size of processing batch.
     * @param amount Number of NFTs to mint.
     */
    function createThinkBatch(
        address recipient,
        string memory prompt,
        string memory agentPrompt,
        uint8 dimensions,
        uint16 batchSize,
        uint256 amount
    ) external onlyOwner returns (uint256) {
        uint256 thinkId = _thinkIdCounter++;

        _thinkData[thinkId] = ThinkData({
            prompt: prompt,
            agentPrompt: agentPrompt,
            lastUpdate: uint40(block.timestamp),
            active: true,
            dimensions: dimensions,
            batchSize: batchSize,
            state: DecisionState.IDLE,
            lastDecision: ""
        });

        _mint(recipient, thinkId, amount, "");

        emit ThinkCreated(thinkId, prompt, dimensions, batchSize);
        return thinkId;
    }

    /**
     * @dev Updates Think data.
     * @param thinkId The NFT ID.
     * @param newPrompt New prompt.
     * @param newAgentPrompt New agent prompt.
     */
    function updateThink(
        uint256 thinkId,
        string memory newPrompt,
        string memory newAgentPrompt
    ) external {
        require(balanceOf(msg.sender, thinkId) > 0, "Not token owner");
        require(_thinkData[thinkId].active, "THINK not active");

        ThinkData storage think = _thinkData[thinkId];
        think.prompt = newPrompt;
        think.agentPrompt = newAgentPrompt;
        think.lastUpdate = uint40(block.timestamp);

        emit ThinkUpdated(thinkId, newPrompt, uint40(block.timestamp));
    }

    /**
     * @dev Triggers the decision-making process.
     * @param thinkId The NFT ID.
     * @param externalData Arbitrary external input data.
     */
    function executeDecision(uint256 thinkId, string memory externalData) external {
        require(balanceOf(msg.sender, thinkId) > 0, "Not token owner");
        require(_thinkData[thinkId].active, "THINK not active");
        require(_thinkData[thinkId].state == DecisionState.IDLE, "Already processing");

        ThinkData storage think = _thinkData[thinkId];

        // Simulate decision-making (in real cases, call external AI or Oracles)
        think.state = DecisionState.PROCESSING;
        think.lastDecision = string(abi.encodePacked("Decision based on: ", externalData));
        think.state = DecisionState.COMPLETED;
        think.lastUpdate = uint40(block.timestamp);

        emit DecisionMade(thinkId, think.lastDecision, uint40(block.timestamp));
    }

    /**
     * @dev Retrieves Think data.
     * @param thinkId The NFT ID.
     */
    function getThinkData(uint256 thinkId) external view returns (ThinkData memory) {
        require(_thinkData[thinkId].active, "THINK not active");
        return _thinkData[thinkId];
    }

    /**
     * @dev Generates a dynamic metadata URI.
     */
    function uri(uint256 thinkId) public view override returns (string memory) {
        require(_thinkData[thinkId].active, "THINK not active");

        string memory stateStr = _stateToString(_thinkData[thinkId].state);
        return string(abi.encodePacked(
            "https://api.think.storage/",
            thinkId.toString(),
            "?state=",
            stateStr
        ));
    }

    /**
     * @dev Internal function to convert state enum to string.
     */
    function _stateToString(DecisionState state) private pure returns (string memory) {
        if (state == DecisionState.IDLE) return "IDLE";
        if (state == DecisionState.PROCESSING) return "PROCESSING";
        if (state == DecisionState.COMPLETED) return "COMPLETED";
        return "FAILED";
    }
}
