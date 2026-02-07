// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * Mock IDNFT for testing XMindAgentRegistry (implements IIDNFTMint surface)
 */
contract MockIDNFT {
    uint256 public nextTokenId = 1;
    mapping(address => bool) public minter;

    function setMinter(address account, bool allowed) external {
        minter[account] = allowed;
    }

    function mintAgentIdentity(
        address primaryWallet,
        string memory,
        string memory,
        string memory,
        string memory,
        string memory,
        bytes32,
        bool
    ) external returns (uint256) {
        require(minter[msg.sender], "MockIDNFT: not minter");
        uint256 tokenId = nextTokenId++;
        return tokenId;
    }
}
