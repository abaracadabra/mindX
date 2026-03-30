// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./Diamond.sol";

/**
 * @title DiamondCutFacet
 * @dev Implementation of the diamondCut external function with DAIO governance integration
 *
 * This facet provides the core upgrade functionality for diamonds, allowing:
 * - Adding new facets and functions
 * - Replacing existing functions with new implementations
 * - Removing functions and facets
 * - Constitutional validation of all changes
 * - Governance approval requirements for critical upgrades
 *
 * @author DAIO Development Team
 */

contract DiamondCutFacet is IDiamondCut {
    using LibDiamond for LibDiamond.DiamondStorage;

    /// @notice Add/replace/remove any number of functions and optionally execute
    ///         a function with delegatecall
    /// @param _diamondCut Contains the facet addresses and function selectors
    /// @param _init The address of the contract or facet to execute _calldata
    /// @param _calldata A function call, including function selector and arguments
    ///                  _calldata is executed with delegatecall on _init
    function diamondCut(
        FacetCut[] calldata _diamondCut,
        address _init,
        bytes calldata _calldata
    ) external override {
        // Enforce governance approval for diamond modifications
        LibDiamond.enforceGovernanceApproval();

        // Enforce not emergency paused (critical operations only)
        LibDiamond.enforceNotEmergencyPaused();

        // Validate critical facet changes require higher approval
        _validateCriticalChanges(_diamondCut);

        // Perform the diamond cut with constitutional validation
        LibDiamondCut.diamondCut(_diamondCut, _init, _calldata);
    }

    /**
     * @dev Validate that critical facet changes have proper approval
     */
    function _validateCriticalChanges(FacetCut[] calldata _diamondCut) internal view {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        bool hasCriticalChanges = false;

        for (uint256 i = 0; i < _diamondCut.length; i++) {
            FacetCut memory cut = _diamondCut[i];

            // Check if we're modifying a critical facet
            if (cut.action == FacetCutAction.Replace || cut.action == FacetCutAction.Remove) {
                if (ds.facetMetadata[cut.facetAddress].critical) {
                    hasCriticalChanges = true;
                    break;
                }
            }

            // Check if we're adding a critical facet (determined by special selectors)
            if (cut.action == FacetCutAction.Add) {
                for (uint256 j = 0; j < cut.functionSelectors.length; j++) {
                    if (_isCriticalSelector(cut.functionSelectors[j])) {
                        hasCriticalChanges = true;
                        break;
                    }
                }
                if (hasCriticalChanges) break;
            }
        }

        // If critical changes detected, require executive governance approval
        if (hasCriticalChanges) {
            require(
                ds.governance.hasExecutiveApproval(msg.sender),
                "DiamondCut: Critical changes require executive approval"
            );
        }
    }

    /**
     * @dev Check if a function selector is considered critical
     */
    function _isCriticalSelector(bytes4 selector) internal pure returns (bool) {
        // Critical selectors that affect core diamond functionality
        return selector == IDiamondCut.diamondCut.selector ||
               selector == bytes4(keccak256("transferOwnership(address)")) ||
               selector == bytes4(keccak256("emergencyPause()")) ||
               selector == bytes4(keccak256("emergencyUnpause()")) ||
               selector == bytes4(keccak256("setEmergencyFacet(address,bool)"));
    }

    /**
     * @dev Batch diamond cut with metadata setting
     */
    function diamondCutWithMetadata(
        FacetCut[] calldata _diamondCut,
        address _init,
        bytes calldata _calldata,
        FacetMetadataInput[] calldata _metadata
    ) external {
        // Perform the main diamond cut
        diamondCut(_diamondCut, _init, _calldata);

        // Set metadata for new facets
        for (uint256 i = 0; i < _metadata.length; i++) {
            FacetMetadataInput memory meta = _metadata[i];
            LibDiamond.setFacetMetadata(
                meta.facetAddress,
                meta.name,
                meta.version,
                meta.description,
                meta.critical
            );
        }
    }

    struct FacetMetadataInput {
        address facetAddress;
        string name;
        string version;
        string description;
        bool critical;
    }

    /**
     * @dev Emergency diamond cut (only during emergency pause)
     * Limited to adding emergency facets only
     */
    function emergencyDiamondCut(
        FacetCut[] calldata _diamondCut,
        address _init,
        bytes calldata _calldata
    ) external {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Only allow during emergency pause
        require(ds.emergencyPaused, "DiamondCut: Not in emergency mode");

        // Require executive governance
        require(
            ds.governance.hasExecutiveApproval(msg.sender),
            "DiamondCut: Emergency changes require executive approval"
        );

        // Only allow adding emergency facets
        for (uint256 i = 0; i < _diamondCut.length; i++) {
            require(
                _diamondCut[i].action == FacetCutAction.Add,
                "DiamondCut: Emergency mode only allows adding facets"
            );
        }

        // Perform the cut (bypasses normal constitutional validation during emergency)
        LibDiamondCut.diamondCut(_diamondCut, _init, _calldata);

        // Mark all added facets as emergency facets
        for (uint256 i = 0; i < _diamondCut.length; i++) {
            ds.emergencyFacets[_diamondCut[i].facetAddress] = true;
        }
    }

    /**
     * @dev Preview diamond cut (view function to check validity)
     */
    function previewDiamondCut(
        FacetCut[] calldata _diamondCut,
        address _init,
        bytes calldata _calldata
    ) external view returns (
        bool isValid,
        string memory reason,
        uint256 gasEstimate
    ) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Check constitutional validation
        (bool valid, string memory constitutionReason) = ds.constitution.validateDiamondCut(
            address(this),
            _diamondCut,
            _init,
            _calldata
        );

        if (!valid) {
            return (false, constitutionReason, 0);
        }

        // Check governance approval (simulate)
        bool hasApproval = msg.sender == ds.contractOwner ||
                          ds.governance.hasExecutiveApproval(msg.sender) ||
                          ds.governance.hasDiamondManagerRole(msg.sender);

        if (!hasApproval) {
            return (false, "Insufficient governance approval", 0);
        }

        // Check critical changes
        bool hasCriticalChanges = false;
        for (uint256 i = 0; i < _diamondCut.length; i++) {
            if (ds.facetMetadata[_diamondCut[i].facetAddress].critical) {
                hasCriticalChanges = true;
                break;
            }
        }

        if (hasCriticalChanges && !ds.governance.hasExecutiveApproval(msg.sender)) {
            return (false, "Critical changes require executive approval", 0);
        }

        // Estimate gas (simplified calculation)
        uint256 estimatedGas = 21000; // Base transaction cost
        for (uint256 i = 0; i < _diamondCut.length; i++) {
            estimatedGas += _diamondCut[i].functionSelectors.length * 30000; // Rough estimate per selector
        }

        if (_init != address(0) && _calldata.length > 0) {
            estimatedGas += 50000; // Initialization cost
        }

        return (true, "Valid diamond cut", estimatedGas);
    }

    /**
     * @dev Get diamond cut history
     */
    function getDiamondCutHistory(
        uint256 offset,
        uint256 limit
    ) external view returns (
        uint256[] memory upgradeIds,
        address[] memory initiators,
        uint256[] memory timestamps,
        uint256 totalUpgrades
    ) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        uint256 total = ds.upgradeCount;
        uint256 end = offset + limit;
        if (end > total) end = total;

        uint256 length = end > offset ? end - offset : 0;

        upgradeIds = new uint256[](length);
        initiators = new address[](length);
        timestamps = new uint256[](length);

        for (uint256 i = 0; i < length; i++) {
            uint256 upgradeId = offset + i;
            LibDiamond.UpgradeInfo storage upgrade = ds.upgrades[upgradeId];

            upgradeIds[i] = upgradeId;
            initiators[i] = upgrade.initiator;
            timestamps[i] = upgrade.timestamp;
        }

        return (upgradeIds, initiators, timestamps, total);
    }

    /**
     * @dev Validate selector conflicts before adding
     */
    function validateNewSelectors(
        bytes4[] calldata selectors
    ) external view returns (
        bool isValid,
        bytes4[] memory conflicts,
        address[] memory existingFacets
    ) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        bytes4[] memory conflictList = new bytes4[](selectors.length);
        address[] memory facetList = new address[](selectors.length);
        uint256 conflictCount = 0;

        for (uint256 i = 0; i < selectors.length; i++) {
            address existingFacet = ds.selectorToFacetAndPosition[selectors[i]].facetAddress;
            if (existingFacet != address(0)) {
                conflictList[conflictCount] = selectors[i];
                facetList[conflictCount] = existingFacet;
                conflictCount++;
            }
        }

        // Resize arrays to actual conflict count
        conflicts = new bytes4[](conflictCount);
        existingFacets = new address[](conflictCount);

        for (uint256 i = 0; i < conflictCount; i++) {
            conflicts[i] = conflictList[i];
            existingFacets[i] = facetList[i];
        }

        return (conflictCount == 0, conflicts, existingFacets);
    }

    /**
     * @dev Get facet upgrade impact analysis
     */
    function getUpgradeImpact(
        FacetCut[] calldata _diamondCut
    ) external view returns (
        uint256 functionsAdded,
        uint256 functionsReplaced,
        uint256 functionsRemoved,
        address[] memory affectedFacets,
        bool affectsCriticalFacets
    ) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        uint256 added = 0;
        uint256 replaced = 0;
        uint256 removed = 0;
        bool criticalAffected = false;

        address[] memory tempFacets = new address[](_diamondCut.length);
        uint256 facetCount = 0;

        for (uint256 i = 0; i < _diamondCut.length; i++) {
            FacetCut memory cut = _diamondCut[i];

            // Track affected facets
            tempFacets[facetCount] = cut.facetAddress;
            facetCount++;

            // Check if critical
            if (ds.facetMetadata[cut.facetAddress].critical) {
                criticalAffected = true;
            }

            // Count function changes
            if (cut.action == FacetCutAction.Add) {
                added += cut.functionSelectors.length;
            } else if (cut.action == FacetCutAction.Replace) {
                replaced += cut.functionSelectors.length;
            } else if (cut.action == FacetCutAction.Remove) {
                removed += cut.functionSelectors.length;
            }
        }

        // Resize facets array
        affectedFacets = new address[](facetCount);
        for (uint256 i = 0; i < facetCount; i++) {
            affectedFacets[i] = tempFacets[i];
        }

        return (added, replaced, removed, affectedFacets, criticalAffected);
    }
}