// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "../core/THOT.sol";

/**
 * @title TransmuteAgent
 * @notice Converts raw information into structured THOT knowledge
 * @dev Agent contract for THOT creation from raw data
 */
contract TransmuteAgent is Ownable {
    THOT private _thotContract;

    event DataTransmuted(bytes32 indexed inputHash, bytes32 transformedHash, uint256 thotId);

    constructor(address thotAddress) Ownable(msg.sender) {
        require(thotAddress != address(0), "Invalid THOT contract address");
        _thotContract = THOT(thotAddress);
    }

    /**
     * @dev Transmutes input data into a THOT.
     * @param inputData Raw input data.
     * @return thotId The ID of the created THOT
     */
    function transmuteData(string memory inputData) external onlyOwner returns (uint256) {
        bytes32 inputHash = keccak256(abi.encodePacked(inputData));
        bytes32 transformedHash = keccak256(abi.encodePacked(_processData(inputData)));

        uint256 thotId = _thotContract.mintTHOT(string(abi.encodePacked(transformedHash)));

        emit DataTransmuted(inputHash, transformedHash, thotId);
        return thotId;
    }

    /**
     * @dev Batch transmute multiple data inputs.
     * @param inputDataArray Array of raw input data.
     * @return thotIds Array of created THOT IDs
     */
    function batchTransmute(string[] memory inputDataArray) external onlyOwner returns (uint256[] memory) {
        uint256[] memory thotIds = new uint256[](inputDataArray.length);

        for (uint256 i = 0; i < inputDataArray.length; i++) {
            bytes32 inputHash = keccak256(abi.encodePacked(inputDataArray[i]));
            bytes32 transformedHash = keccak256(abi.encodePacked(_processData(inputDataArray[i])));
            thotIds[i] = _thotContract.mintTHOT(string(abi.encodePacked(transformedHash)));
            emit DataTransmuted(inputHash, transformedHash, thotIds[i]);
        }

        return thotIds;
    }

    /**
     * @dev Transmute data with full THOT parameters
     * @param recipient Address to receive the THOT
     * @param inputData Raw input data
     * @param dimensions THOT dimensions (64, 512, or 768)
     * @param parallelUnits Processing units
     * @param metadataURI Additional metadata URI
     * @return thotId The ID of the created THOT
     */
    function transmuteDataFull(
        address recipient,
        string memory inputData,
        uint32 dimensions,
        uint8 parallelUnits,
        string memory metadataURI
    ) external onlyOwner returns (uint256) {
        bytes32 inputHash = keccak256(abi.encodePacked(inputData));
        bytes32 transformedHash = keccak256(abi.encodePacked(_processData(inputData)));

        uint256 thotId = _thotContract.mintTHOT(
            recipient,
            transformedHash,
            dimensions,
            parallelUnits,
            metadataURI
        );

        emit DataTransmuted(inputHash, transformedHash, thotId);
        return thotId;
    }

    /**
     * @dev Internal function to process data.
     * @param data The raw data to be processed.
     * @return The processed output.
     */
    function _processData(string memory data) private pure returns (string memory) {
        return string(abi.encodePacked("Distilled:", data));
    }

    /**
     * @dev Set THOT contract address
     * @param thotAddress New THOT contract address
     */
    function setTHOTContract(address thotAddress) external onlyOwner {
        require(thotAddress != address(0), "Invalid THOT contract address");
        _thotContract = THOT(thotAddress);
    }
}
