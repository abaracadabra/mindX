// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

/**
 * @title dNFT - Dynamic NFT
 * @dev Dynamic THINK implementation as ERC1155
 * @notice Not intelligent (no prompt/persona/model/THOT), just dynamic metadata updates
 */
contract dNFT is ERC1155, AccessControl {
    using Strings for uint256;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

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

    constructor() ERC1155("") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    function createThinkBatch(
        address recipient,
        string memory prompt,
        string memory agentPrompt,
        uint8 dimensions,
        uint16 batchSize,
        uint256 amount
    ) external onlyRole(MINTER_ROLE) returns (uint256) {
        _thinkIdCounter++;
        uint256 thinkId = _thinkIdCounter;

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

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC1155, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
