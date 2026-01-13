// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IntelligentNFT.sol";
import "./interfaces/IIntelligentNFT.sol";

/**
 * @title IntelligentNFTFactory
 * @notice Factory contract for easy deployment of IntelligentNFT contracts
 * @dev Allows participants and agents to deploy iNFTs with minimal setup
 */
contract IntelligentNFTFactory {
    event INFTDeployed(
        address indexed deployedBy,
        address indexed contractAddress,
        string name,
        string symbol,
        uint256 timestamp
    );

    mapping(address => address[]) public deployedContracts;
    address[] public allContracts;

    /**
     * @notice Deploy a new IntelligentNFT contract
     * @param name Name of the NFT collection
     * @param symbol Symbol of the NFT collection
     * @param agenticPlace Optional AgenticPlace marketplace address (can be set later)
     * @return contractAddress Address of the deployed contract
     */
    function deployIntelligentNFT(
        string memory name,
        string memory symbol,
        address agenticPlace
    ) external returns (address) {
        IntelligentNFT newContract = new IntelligentNFT(name, symbol, msg.sender, agenticPlace);
        address contractAddress = address(newContract);
        
        deployedContracts[msg.sender].push(contractAddress);
        allContracts.push(contractAddress);
        
        emit INFTDeployed(
            msg.sender,
            contractAddress,
            name,
            symbol,
            block.timestamp
        );
        
        return contractAddress;
    }

    /**
     * @notice Get all contracts deployed by an address
     * @param deployer Address of the deployer
     * @return contracts Array of contract addresses
     */
    function getDeployedContracts(address deployer) 
        external 
        view 
        returns (address[] memory) 
    {
        return deployedContracts[deployer];
    }

    /**
     * @notice Get total number of deployed contracts
     * @return count Total number of contracts
     */
    function getTotalContracts() external view returns (uint256) {
        return allContracts.length;
    }
}
