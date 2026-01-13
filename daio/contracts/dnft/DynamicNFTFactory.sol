// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DynamicNFT.sol";
import "./interfaces/IDynamicNFT.sol";

/**
 * @title DynamicNFTFactory
 * @notice Factory contract for easy deployment of DynamicNFT contracts
 * @dev Allows participants and agents to deploy dNFTs with minimal setup
 */
contract DynamicNFTFactory {
    event DNFTDeployed(
        address indexed deployedBy,
        address indexed contractAddress,
        string name,
        string symbol,
        uint256 timestamp
    );

    mapping(address => address[]) public deployedContracts;
    address[] public allContracts;

    /**
     * @notice Deploy a new DynamicNFT contract
     * @param name Name of the NFT collection
     * @param symbol Symbol of the NFT collection
     * @return contractAddress Address of the deployed contract
     */
    function deployDynamicNFT(
        string memory name,
        string memory symbol,
        address agenticPlace
    ) external returns (address) {
        DynamicNFT newContract = new DynamicNFT(name, symbol, msg.sender, agenticPlace);
        address contractAddress = address(newContract);
        
        deployedContracts[msg.sender].push(contractAddress);
        allContracts.push(contractAddress);
        
        emit DNFTDeployed(
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
