// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Diamond.sol";

/**
 * @title DiamondLoupeFacet
 * @dev Implementation of the diamond loupe interface for diamond introspection
 *
 * The loupe facet provides functions to inspect the diamond:
 * - What facets are installed
 * - What functions each facet provides
 * - Which facet provides a specific function
 * - Enhanced DAIO-specific introspection capabilities
 *
 * @author DAIO Development Team
 */

contract DiamondLoupeFacet is IDiamondLoupe {
    // SPDX-License-Identifier: MIT

    /// @notice Gets all facet addresses and their four byte function selectors.
    /// @return facets_ Facet
    function facets() external view override returns (Facet[] memory facets_) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        uint256 numFacets = ds.facetAddresses.length;
        facets_ = new Facet[](numFacets);

        for (uint256 i; i < numFacets; i++) {
            address facetAddress_ = ds.facetAddresses[i];
            facets_[i].facetAddress = facetAddress_;
            facets_[i].functionSelectors = ds.facetFunctionSelectors[facetAddress_].functionSelectors;
        }
    }

    /// @notice Gets all the function selectors provided by a facet.
    /// @param _facet The facet address.
    /// @return facetFunctionSelectors_
    function facetFunctionSelectors(address _facet) external view override returns (bytes4[] memory facetFunctionSelectors_) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        facetFunctionSelectors_ = ds.facetFunctionSelectors[_facet].functionSelectors;
    }

    /// @notice Get all the facet addresses used by a diamond.
    /// @return facetAddresses_
    function facetAddresses() external view override returns (address[] memory facetAddresses_) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        facetAddresses_ = ds.facetAddresses;
    }

    /// @notice Gets the facet that supports the given selector.
    /// @dev If facet is not found return address(0).
    /// @param _functionSelector The function selector.
    /// @return facetAddress_ The facet address.
    function facetAddress(bytes4 _functionSelector) external view override returns (address facetAddress_) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        facetAddress_ = ds.selectorToFacetAndPosition[_functionSelector].facetAddress;
    }

    // Enhanced DAIO-specific introspection functions

    /**
     * @dev Get detailed facet information with metadata
     */
    function facetsWithMetadata() external view returns (FacetWithMetadata[] memory facetsWithMetadata_) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        uint256 numFacets = ds.facetAddresses.length;
        facetsWithMetadata_ = new FacetWithMetadata[](numFacets);

        for (uint256 i; i < numFacets; i++) {
            address facetAddress_ = ds.facetAddresses[i];
            LibDiamond.FacetMetadata storage metadata = ds.facetMetadata[facetAddress_];

            facetsWithMetadata_[i] = FacetWithMetadata({
                facetAddress: facetAddress_,
                functionSelectors: ds.facetFunctionSelectors[facetAddress_].functionSelectors,
                name: metadata.name,
                version: metadata.version,
                description: metadata.description,
                critical: metadata.critical,
                addedTimestamp: metadata.addedTimestamp,
                addedBy: metadata.addedBy
            });
        }
    }

    struct FacetWithMetadata {
        address facetAddress;
        bytes4[] functionSelectors;
        string name;
        string version;
        string description;
        bool critical;
        uint256 addedTimestamp;
        address addedBy;
    }

    /**
     * @dev Get functions grouped by interface
     */
    function functionsByInterface() external view returns (InterfaceInfo[] memory interfaces) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Collect all unique interfaces by analyzing function selectors
        InterfaceInfo[] memory tempInterfaces = new InterfaceInfo[](20); // Max expected interfaces
        uint256 interfaceCount = 0;

        for (uint256 i = 0; i < ds.facetAddresses.length; i++) {
            address facetAddress_ = ds.facetAddresses[i];
            bytes4[] memory selectors = ds.facetFunctionSelectors[facetAddress_].functionSelectors;

            for (uint256 j = 0; j < selectors.length; j++) {
                bytes4 selector = selectors[j];
                string memory interfaceName = _getInterfaceName(selector);

                // Find or create interface group
                uint256 interfaceIndex = interfaceCount;
                for (uint256 k = 0; k < interfaceCount; k++) {
                    if (keccak256(abi.encodePacked(tempInterfaces[k].name)) == keccak256(abi.encodePacked(interfaceName))) {
                        interfaceIndex = k;
                        break;
                    }
                }

                if (interfaceIndex == interfaceCount) {
                    // New interface
                    tempInterfaces[interfaceCount] = InterfaceInfo({
                        name: interfaceName,
                        selectors: new bytes4[](1),
                        facets: new address[](1),
                        selectorCount: 1
                    });
                    tempInterfaces[interfaceCount].selectors[0] = selector;
                    tempInterfaces[interfaceCount].facets[0] = facetAddress_;
                    interfaceCount++;
                } else {
                    // Add to existing interface
                    _addToInterface(tempInterfaces[interfaceIndex], selector, facetAddress_);
                }
            }
        }

        // Resize to actual count
        interfaces = new InterfaceInfo[](interfaceCount);
        for (uint256 i = 0; i < interfaceCount; i++) {
            interfaces[i] = tempInterfaces[i];
        }
    }

    struct InterfaceInfo {
        string name;
        bytes4[] selectors;
        address[] facets;
        uint256 selectorCount;
    }

    /**
     * @dev Get critical facets (require executive approval to modify)
     */
    function getCriticalFacets() external view returns (CriticalFacetInfo[] memory criticalFacets) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Count critical facets first
        uint256 criticalCount = 0;
        for (uint256 i = 0; i < ds.facetAddresses.length; i++) {
            if (ds.facetMetadata[ds.facetAddresses[i]].critical) {
                criticalCount++;
            }
        }

        criticalFacets = new CriticalFacetInfo[](criticalCount);
        uint256 index = 0;

        for (uint256 i = 0; i < ds.facetAddresses.length; i++) {
            address facetAddress_ = ds.facetAddresses[i];
            LibDiamond.FacetMetadata storage metadata = ds.facetMetadata[facetAddress_];

            if (metadata.critical) {
                criticalFacets[index] = CriticalFacetInfo({
                    facetAddress: facetAddress_,
                    name: metadata.name,
                    version: metadata.version,
                    addedBy: metadata.addedBy,
                    functionCount: ds.facetFunctionSelectors[facetAddress_].functionSelectors.length
                });
                index++;
            }
        }
    }

    struct CriticalFacetInfo {
        address facetAddress;
        string name;
        string version;
        address addedBy;
        uint256 functionCount;
    }

    /**
     * @dev Get emergency facets (can operate during emergency pause)
     */
    function getEmergencyFacets() external view returns (address[] memory emergencyFacets) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Count emergency facets
        uint256 emergencyCount = 0;
        for (uint256 i = 0; i < ds.facetAddresses.length; i++) {
            if (ds.emergencyFacets[ds.facetAddresses[i]]) {
                emergencyCount++;
            }
        }

        emergencyFacets = new address[](emergencyCount);
        uint256 index = 0;

        for (uint256 i = 0; i < ds.facetAddresses.length; i++) {
            address facetAddress_ = ds.facetAddresses[i];
            if (ds.emergencyFacets[facetAddress_]) {
                emergencyFacets[index] = facetAddress_;
                index++;
            }
        }
    }

    /**
     * @dev Get diamond analytics
     */
    function getDiamondAnalytics() external view returns (DiamondAnalytics memory analytics) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        uint256 totalFunctions = 0;
        uint256 criticalFacets = 0;
        uint256 emergencyFacets = 0;

        for (uint256 i = 0; i < ds.facetAddresses.length; i++) {
            address facetAddress_ = ds.facetAddresses[i];
            totalFunctions += ds.facetFunctionSelectors[facetAddress_].functionSelectors.length;

            if (ds.facetMetadata[facetAddress_].critical) {
                criticalFacets++;
            }

            if (ds.emergencyFacets[facetAddress_]) {
                emergencyFacets++;
            }
        }

        analytics = DiamondAnalytics({
            totalFacets: ds.facetAddresses.length,
            totalFunctions: totalFunctions,
            criticalFacets: criticalFacets,
            emergencyFacets: emergencyFacets,
            upgradeCount: ds.upgradeCount,
            isEmergencyPaused: ds.emergencyPaused,
            owner: ds.contractOwner,
            constitutionAddress: address(ds.constitution),
            governanceAddress: address(ds.governance)
        });
    }

    struct DiamondAnalytics {
        uint256 totalFacets;
        uint256 totalFunctions;
        uint256 criticalFacets;
        uint256 emergencyFacets;
        uint256 upgradeCount;
        bool isEmergencyPaused;
        address owner;
        address constitutionAddress;
        address governanceAddress;
    }

    /**
     * @dev Find function selector by name (approximate match)
     */
    function findFunctionByName(string calldata functionName) external view returns (
        bytes4[] memory selectors,
        address[] memory facets,
        string[] memory matches
    ) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // This is a simplified implementation
        // In practice, you'd want a more sophisticated function name registry
        bytes4 targetSelector = bytes4(keccak256(bytes(functionName)));

        address facetAddr = ds.selectorToFacetAndPosition[targetSelector].facetAddress;

        if (facetAddr != address(0)) {
            selectors = new bytes4[](1);
            facets = new address[](1);
            matches = new string[](1);

            selectors[0] = targetSelector;
            facets[0] = facetAddr;
            matches[0] = functionName;
        } else {
            // Return empty arrays
            selectors = new bytes4[](0);
            facets = new address[](0);
            matches = new string[](0);
        }
    }

    /**
     * @dev Get facet upgrade history
     */
    function getFacetHistory(address facet) external view returns (FacetHistoryEntry[] memory history) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Count relevant upgrades
        uint256 relevantUpgrades = 0;
        for (uint256 i = 0; i < ds.upgradeCount; i++) {
            LibDiamond.UpgradeInfo storage upgrade = ds.upgrades[i];
            if (_facetInUpgrade(facet, upgrade)) {
                relevantUpgrades++;
            }
        }

        history = new FacetHistoryEntry[](relevantUpgrades);
        uint256 historyIndex = 0;

        for (uint256 i = 0; i < ds.upgradeCount; i++) {
            LibDiamond.UpgradeInfo storage upgrade = ds.upgrades[i];
            if (_facetInUpgrade(facet, upgrade)) {
                string memory action = "Unknown";
                if (_addressInArray(facet, upgrade.addedFacets)) action = "Added";
                else if (_addressInArray(facet, upgrade.replacedFacets)) action = "Replaced";
                else if (_addressInArray(facet, upgrade.removedFacets)) action = "Removed";

                history[historyIndex] = FacetHistoryEntry({
                    upgradeId: i,
                    timestamp: upgrade.timestamp,
                    initiator: upgrade.initiator,
                    action: action,
                    reason: upgrade.reason
                });
                historyIndex++;
            }
        }
    }

    struct FacetHistoryEntry {
        uint256 upgradeId;
        uint256 timestamp;
        address initiator;
        string action;
        string reason;
    }

    /**
     * @dev Check if diamond supports a specific interface (ERC165)
     */
    function supportsInterface(bytes4 interfaceId) external view returns (bool) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        return ds.supportedInterfaces[interfaceId];
    }

    /**
     * @dev Get all supported interfaces
     */
    function getSupportedInterfaces() external view returns (bytes4[] memory interfaces) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Common interfaces to check
        bytes4[] memory commonInterfaces = new bytes4[](10);
        commonInterfaces[0] = type(IERC165).interfaceId;
        commonInterfaces[1] = type(IDiamondCut).interfaceId;
        commonInterfaces[2] = type(IDiamondLoupe).interfaceId;
        commonInterfaces[3] = 0x80ac58cd; // ERC721
        commonInterfaces[4] = 0x5b5e139f; // ERC721Metadata
        commonInterfaces[5] = 0x01ffc9a7; // ERC165
        commonInterfaces[6] = 0x7f5828d0; // ERC173 (Ownership)
        commonInterfaces[7] = 0x36372b07; // ERC20
        commonInterfaces[8] = 0xd9b67a26; // ERC1155
        commonInterfaces[9] = 0x4e2312e0; // ERC1155Receiver

        uint256 supportedCount = 0;
        bytes4[] memory tempSupported = new bytes4[](commonInterfaces.length);

        for (uint256 i = 0; i < commonInterfaces.length; i++) {
            if (ds.supportedInterfaces[commonInterfaces[i]]) {
                tempSupported[supportedCount] = commonInterfaces[i];
                supportedCount++;
            }
        }

        interfaces = new bytes4[](supportedCount);
        for (uint256 i = 0; i < supportedCount; i++) {
            interfaces[i] = tempSupported[i];
        }
    }

    // Helper functions

    function _getInterfaceName(bytes4 selector) internal pure returns (string memory) {
        // Map common selectors to interface names
        if (selector == IDiamondCut.diamondCut.selector) return "IDiamondCut";
        if (selector == IDiamondLoupe.facets.selector ||
            selector == IDiamondLoupe.facetAddresses.selector ||
            selector == IDiamondLoupe.facetAddress.selector ||
            selector == IDiamondLoupe.facetFunctionSelectors.selector) return "IDiamondLoupe";
        if (selector == bytes4(keccak256("balanceOf(address)"))) return "IERC20/IERC721";
        if (selector == bytes4(keccak256("transferFrom(address,address,uint256)"))) return "IERC20/IERC721";
        if (selector == bytes4(keccak256("transfer(address,uint256)"))) return "IERC20";
        if (selector == bytes4(keccak256("approve(address,uint256)"))) return "IERC20/IERC721";
        if (selector == bytes4(keccak256("ownerOf(uint256)"))) return "IERC721";
        if (selector == bytes4(keccak256("tokenURI(uint256)"))) return "IERC721Metadata";

        return "Unknown";
    }

    function _addToInterface(InterfaceInfo memory interface_, bytes4 selector, address facet) internal pure {
        // This is a simplified implementation
        // In practice, you'd need dynamic array handling
    }

    function _facetInUpgrade(address facet, LibDiamond.UpgradeInfo storage upgrade) internal view returns (bool) {
        return _addressInArray(facet, upgrade.addedFacets) ||
               _addressInArray(facet, upgrade.replacedFacets) ||
               _addressInArray(facet, upgrade.removedFacets);
    }

    function _addressInArray(address target, address[] storage array) internal view returns (bool) {
        for (uint256 i = 0; i < array.length; i++) {
            if (array[i] == target) return true;
        }
        return false;
    }
}