// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title THINK - THOT Intelligence Network Knowledge
 * @dev ERC1155 implementation for batch THOT creation and management
 */
contract THINK is ERC1155, Ownable {
    using Strings for uint256;

    struct ThinkData {
        string prompt;
        string agentPrompt;
        uint40 lastUpdate;
        bool active;
        uint8 dimensions;
        uint16 batchSize;
    }

    mapping(uint256 => ThinkData) private _thinkData;
    uint256 private _thinkIdCounter;

    event ThinkCreated(
        uint256 indexed thinkId,
        string prompt,
        uint8 dimensions,
        uint16 batchSize
    );

    event ThinkUpdated(
        uint256 indexed thinkId,
        string newPrompt,
        uint40 timestamp
    );

    constructor() ERC1155("") Ownable(msg.sender) {
        _thinkIdCounter = 1;
    }

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
            batchSize: batchSize
        });

        _mint(recipient, thinkId, amount, "");
        
        emit ThinkCreated(thinkId, prompt, dimensions, batchSize);
        return thinkId;
    }

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

    function getThinkData(uint256 thinkId) 
        external 
        view 
        returns (ThinkData memory) 
    {
        require(_thinkData[thinkId].active, "THINK not active");
        return _thinkData[thinkId];
    }

    function uri(uint256 thinkId) 
        public 
        view 
        virtual 
        override 
        returns (string memory) 
    {
        require(_thinkData[thinkId].active, "THINK not active");
        return string(abi.encodePacked(
            "https://api.think.storage/",
            thinkId.toString()
        ));
    }
}
