// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Diamond
 * @dev ERC2535 Diamond Standard implementation with DAIO integration
 *
 * The Diamond pattern allows for modular, upgradeable smart contracts
 * where functionality is split into facets (separate contracts) that
 * can be added, replaced, or removed without losing state.
 *
 * Key Features:
 * - Modular architecture with facets
 * - Upgradeable without state loss
 * - Gas-efficient function calls
 * - DAIO governance integration for upgrades
 * - Constitutional constraints on modifications
 *
 * @author DAIO Development Team
 */

import "@openzeppelin/contracts/utils/introspection/ERC165Storage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

// Required interfaces
interface IERC165 {
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

interface IDiamondCut {
    enum FacetCutAction {Add, Replace, Remove}

    struct FacetCut {
        address facetAddress;
        FacetCutAction action;
        bytes4[] functionSelectors;
    }

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
    ) external;

    event DiamondCut(FacetCut[] _diamondCut, address _init, bytes _calldata);
}

interface IDiamondLoupe {
    struct Facet {
        address facetAddress;
        bytes4[] functionSelectors;
    }

    /// @notice Gets all facet addresses and their four byte function selectors.
    /// @return facets_ Facet
    function facets() external view returns (Facet[] memory facets_);

    /// @notice Gets all the function selectors supported by a specific facet.
    /// @param _facet The facet address.
    /// @return facetFunctionSelectors_
    function facetFunctionSelectors(address _facet) external view returns (bytes4[] memory facetFunctionSelectors_);

    /// @notice Get all the facet addresses used by a diamond.
    /// @return facetAddresses_
    function facetAddresses() external view returns (address[] memory facetAddresses_);

    /// @notice Gets the facet that supports the given selector.
    /// @dev If facet is not found return address(0).
    /// @param _functionSelector The function selector.
    /// @return facetAddress_ The facet address.
    function facetAddress(bytes4 _functionSelector) external view returns (address facetAddress_);
}

interface IDAIO_Constitution_Enhanced {
    function validateDiamondCut(
        address diamond,
        IDiamondCut.FacetCut[] calldata _diamondCut,
        address _init,
        bytes calldata _calldata
    ) external view returns (bool valid, string memory reason);
}

interface IExecutiveGovernance {
    function hasExecutiveApproval(address account) external view returns (bool);
    function hasDiamondManagerRole(address account) external view returns (bool);
}

library LibDiamond {
    bytes32 constant DIAMOND_STORAGE_POSITION = keccak256("diamond.standard.diamond.storage");

    struct FacetAddressAndPosition {
        address facetAddress;
        uint96 functionSelectorPosition; // position in facetFunctionSelectors.functionSelectors array
    }

    struct FacetFunctionSelectors {
        bytes4[] functionSelectors;
        uint256 facetAddressPosition; // position of facetAddress in facetAddresses array
    }

    struct DiamondStorage {
        // maps function selector to the facet address and
        // the position of the selector in the facetFunctionSelectors.selectors array
        mapping(bytes4 => FacetAddressAndPosition) selectorToFacetAndPosition;

        // maps facet addresses to function selectors
        mapping(address => FacetFunctionSelectors) facetFunctionSelectors;

        // facet addresses
        address[] facetAddresses;

        // Used to query if a contract implements an interface.
        mapping(bytes4 => bool) supportedInterfaces;

        // owner of the contract
        address contractOwner;

        // DAIO integration
        IDAIO_Constitution_Enhanced constitution;
        IExecutiveGovernance governance;

        // Upgrade tracking
        uint256 upgradeCount;
        mapping(uint256 => UpgradeInfo) upgrades;

        // Facet metadata
        mapping(address => FacetMetadata) facetMetadata;

        // Emergency controls
        bool emergencyPaused;
        mapping(address => bool) emergencyFacets; // Facets that can operate during emergency
    }

    struct UpgradeInfo {
        address[] addedFacets;
        address[] replacedFacets;
        address[] removedFacets;
        uint256 timestamp;
        address initiator;
        string reason;
    }

    struct FacetMetadata {
        string name;
        string version;
        string description;
        bool critical; // Critical facets require higher approval
        uint256 addedTimestamp;
        address addedBy;
    }

    function diamondStorage() internal pure returns (DiamondStorage storage ds) {
        bytes32 position = DIAMOND_STORAGE_POSITION;
        assembly {
            ds.slot := position
        }
    }

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event FacetMetadataSet(address indexed facet, string name, string version, bool critical);
    event EmergencyPause(bool paused);

    function setContractOwner(address _newOwner) internal {
        DiamondStorage storage ds = diamondStorage();
        address previousOwner = ds.contractOwner;
        ds.contractOwner = _newOwner;
        emit OwnershipTransferred(previousOwner, _newOwner);
    }

    function contractOwner() internal view returns (address contractOwner_) {
        contractOwner_ = diamondStorage().contractOwner;
    }

    function enforceIsContractOwner() internal view {
        require(msg.sender == diamondStorage().contractOwner, "LibDiamond: Must be contract owner");
    }

    function enforceGovernanceApproval() internal view {
        DiamondStorage storage ds = diamondStorage();
        require(
            msg.sender == ds.contractOwner ||
            ds.governance.hasExecutiveApproval(msg.sender) ||
            ds.governance.hasDiamondManagerRole(msg.sender),
            "LibDiamond: Must have governance approval"
        );
    }

    function enforceNotEmergencyPaused() internal view {
        DiamondStorage storage ds = diamondStorage();
        require(!ds.emergencyPaused, "LibDiamond: Emergency paused");
    }

    function setFacetMetadata(
        address facet,
        string memory name,
        string memory version,
        string memory description,
        bool critical
    ) internal {
        DiamondStorage storage ds = diamondStorage();
        ds.facetMetadata[facet] = FacetMetadata({
            name: name,
            version: version,
            description: description,
            critical: critical,
            addedTimestamp: block.timestamp,
            addedBy: msg.sender
        });
        emit FacetMetadataSet(facet, name, version, critical);
    }

    function emergencyPause(bool paused) internal {
        DiamondStorage storage ds = diamondStorage();
        ds.emergencyPaused = paused;
        emit EmergencyPause(paused);
    }
}

contract Diamond is AccessControl, ReentrancyGuard {
    using LibDiamond for LibDiamond.DiamondStorage;

    bytes32 public constant DIAMOND_MANAGER_ROLE = keccak256("DIAMOND_MANAGER_ROLE");
    bytes32 public constant FACET_MANAGER_ROLE = keccak256("FACET_MANAGER_ROLE");

    constructor(
        address _contractOwner,
        address _diamondCutFacet,
        address constitutionAddress,
        address governanceAddress
    ) {
        LibDiamond.setContractOwner(_contractOwner);

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, _contractOwner);
        _grantRole(DIAMOND_MANAGER_ROLE, _contractOwner);

        // Initialize DAIO integration
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        ds.constitution = IDAIO_Constitution_Enhanced(constitutionAddress);
        ds.governance = IExecutiveGovernance(governanceAddress);

        // Add the diamondCut external function from the diamondCutFacet
        IDiamondCut.FacetCut[] memory cut = new IDiamondCut.FacetCut[](1);
        bytes4[] memory functionSelectors = new bytes4[](1);
        functionSelectors[0] = IDiamondCut.diamondCut.selector;
        cut[0] = IDiamondCut.FacetCut({
            facetAddress: _diamondCutFacet,
            action: IDiamondCut.FacetCutAction.Add,
            functionSelectors: functionSelectors
        });
        LibDiamond.diamondCut(cut, address(0), "");

        // Set facet metadata for diamond cut facet
        LibDiamond.setFacetMetadata(
            _diamondCutFacet,
            "DiamondCutFacet",
            "1.0.0",
            "Core diamond upgrade functionality",
            true // Critical facet
        );
    }

    // Find facet for function that is called and execute the
    // function if a facet is found and return any value.
    fallback() external payable {
        LibDiamond.DiamondStorage storage ds;
        bytes32 position = LibDiamond.DIAMOND_STORAGE_POSITION;
        // get diamond storage
        assembly {
            ds.slot := position
        }

        // Check emergency pause
        require(!ds.emergencyPaused || ds.emergencyFacets[ds.selectorToFacetAndPosition[msg.sig].facetAddress],
            "Diamond: Emergency paused");

        // get facet from function selector
        address facet = ds.selectorToFacetAndPosition[msg.sig].facetAddress;
        require(facet != address(0), "Diamond: Function does not exist");

        // Execute external function from facet using delegatecall and return any value.
        assembly {
            // copy function selector and any arguments
            calldatacopy(0, 0, calldatasize())
            // execute function call using the facet
            let result := delegatecall(gas(), facet, 0, calldatasize(), 0, 0)
            // get any return value
            returndatacopy(0, 0, returndatasize())
            // return any return value or error back to the caller
            switch result
                case 0 { revert(0, returndatasize()) }
                default { return(0, returndatasize()) }
        }
    }

    receive() external payable {}

    // Administrative functions
    function emergencyPause() external onlyRole(DIAMOND_MANAGER_ROLE) {
        LibDiamond.emergencyPause(true);
    }

    function emergencyUnpause() external onlyRole(DIAMOND_MANAGER_ROLE) {
        LibDiamond.emergencyPause(false);
    }

    function setEmergencyFacet(address facet, bool isEmergencyFacet) external onlyRole(DIAMOND_MANAGER_ROLE) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        ds.emergencyFacets[facet] = isEmergencyFacet;
    }

    function transferOwnership(address newOwner) external {
        LibDiamond.enforceIsContractOwner();
        LibDiamond.setContractOwner(newOwner);
    }

    function owner() external view returns (address) {
        return LibDiamond.contractOwner();
    }

    // DAIO governance integration
    function getDiamondMetrics() external view returns (
        uint256 facetCount,
        uint256 upgradeCount,
        bool emergencyPaused,
        address constitution,
        address governance
    ) {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        return (
            ds.facetAddresses.length,
            ds.upgradeCount,
            ds.emergencyPaused,
            address(ds.constitution),
            address(ds.governance)
        );
    }

    function getFacetMetadata(address facet) external view returns (
        string memory name,
        string memory version,
        string memory description,
        bool critical,
        uint256 addedTimestamp,
        address addedBy
    ) {
        LibDiamond.FacetMetadata storage metadata = LibDiamond.diamondStorage().facetMetadata[facet];
        return (
            metadata.name,
            metadata.version,
            metadata.description,
            metadata.critical,
            metadata.addedTimestamp,
            metadata.addedBy
        );
    }

    function getUpgradeInfo(uint256 upgradeId) external view returns (
        address[] memory addedFacets,
        address[] memory replacedFacets,
        address[] memory removedFacets,
        uint256 timestamp,
        address initiator,
        string memory reason
    ) {
        LibDiamond.UpgradeInfo storage upgrade = LibDiamond.diamondStorage().upgrades[upgradeId];
        return (
            upgrade.addedFacets,
            upgrade.replacedFacets,
            upgrade.removedFacets,
            upgrade.timestamp,
            upgrade.initiator,
            upgrade.reason
        );
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        return ds.supportedInterfaces[interfaceId] || super.supportsInterface(interfaceId);
    }
}

// Additional library for diamond cuts with DAIO integration
library LibDiamondCut {
    using LibDiamond for LibDiamond.DiamondStorage;

    event DiamondCut(IDiamondCut.FacetCut[] _diamondCut, address _init, bytes _calldata);
    event FacetUpgrade(address indexed facet, IDiamondCut.FacetCutAction action, uint256 selectorCount);

    // Internal function version of diamondCut
    function diamondCut(
        IDiamondCut.FacetCut[] memory _diamondCut,
        address _init,
        bytes memory _calldata
    ) internal {
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // Validate with DAIO constitution
        (bool valid, string memory reason) = ds.constitution.validateDiamondCut(
            address(this),
            _diamondCut,
            _init,
            _calldata
        );
        require(valid, reason);

        // Track upgrade info
        uint256 upgradeId = ds.upgradeCount++;
        LibDiamond.UpgradeInfo storage upgradeInfo = ds.upgrades[upgradeId];
        upgradeInfo.timestamp = block.timestamp;
        upgradeInfo.initiator = msg.sender;

        for (uint256 facetIndex; facetIndex < _diamondCut.length; facetIndex++) {
            IDiamondCut.FacetCutAction action = _diamondCut[facetIndex].action;

            if (action == IDiamondCut.FacetCutAction.Add) {
                addFunctions(_diamondCut[facetIndex].facetAddress, _diamondCut[facetIndex].functionSelectors);
                upgradeInfo.addedFacets.push(_diamondCut[facetIndex].facetAddress);
            } else if (action == IDiamondCut.FacetCutAction.Replace) {
                replaceFunctions(_diamondCut[facetIndex].facetAddress, _diamondCut[facetIndex].functionSelectors);
                upgradeInfo.replacedFacets.push(_diamondCut[facetIndex].facetAddress);
            } else if (action == IDiamondCut.FacetCutAction.Remove) {
                removeFunctions(_diamondCut[facetIndex].facetAddress, _diamondCut[facetIndex].functionSelectors);
                upgradeInfo.removedFacets.push(_diamondCut[facetIndex].facetAddress);
            } else {
                revert("LibDiamondCut: Incorrect FacetCutAction");
            }

            emit FacetUpgrade(
                _diamondCut[facetIndex].facetAddress,
                action,
                _diamondCut[facetIndex].functionSelectors.length
            );
        }

        emit DiamondCut(_diamondCut, _init, _calldata);
        initializeDiamondCut(_init, _calldata);
    }

    function addFunctions(address _facetAddress, bytes4[] memory _functionSelectors) internal {
        require(_functionSelectors.length > 0, "LibDiamondCut: No selectors in facet to cut");
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        require(_facetAddress != address(0), "LibDiamondCut: Add facet can't be address(0)");

        uint96 selectorPosition = uint96(ds.facetFunctionSelectors[_facetAddress].functionSelectors.length);

        // add new facet address if it does not exist
        if (selectorPosition == 0) {
            addFacet(ds, _facetAddress);
        }

        for (uint256 selectorIndex; selectorIndex < _functionSelectors.length; selectorIndex++) {
            bytes4 selector = _functionSelectors[selectorIndex];
            address oldFacetAddress = ds.selectorToFacetAndPosition[selector].facetAddress;
            require(oldFacetAddress == address(0), "LibDiamondCut: Can't add function that already exists");
            addFunction(ds, selector, selectorPosition, _facetAddress);
            selectorPosition++;
        }
    }

    function replaceFunctions(address _facetAddress, bytes4[] memory _functionSelectors) internal {
        require(_functionSelectors.length > 0, "LibDiamondCut: No selectors in facet to cut");
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();
        require(_facetAddress != address(0), "LibDiamondCut: Add facet can't be address(0)");

        uint96 selectorPosition = uint96(ds.facetFunctionSelectors[_facetAddress].functionSelectors.length);

        // add new facet address if it does not exist
        if (selectorPosition == 0) {
            addFacet(ds, _facetAddress);
        }

        for (uint256 selectorIndex; selectorIndex < _functionSelectors.length; selectorIndex++) {
            bytes4 selector = _functionSelectors[selectorIndex];
            address oldFacetAddress = ds.selectorToFacetAndPosition[selector].facetAddress;
            require(oldFacetAddress != _facetAddress, "LibDiamondCut: Can't replace function with same function");
            removeFunction(ds, oldFacetAddress, selector);
            addFunction(ds, selector, selectorPosition, _facetAddress);
            selectorPosition++;
        }
    }

    function removeFunctions(address _facetAddress, bytes4[] memory _functionSelectors) internal {
        require(_functionSelectors.length > 0, "LibDiamondCut: No selectors in facet to cut");
        LibDiamond.DiamondStorage storage ds = LibDiamond.diamondStorage();

        // if function does not exist then do nothing and return
        require(_facetAddress == address(0), "LibDiamondCut: Remove facet address must be address(0)");

        for (uint256 selectorIndex; selectorIndex < _functionSelectors.length; selectorIndex++) {
            bytes4 selector = _functionSelectors[selectorIndex];
            address oldFacetAddress = ds.selectorToFacetAndPosition[selector].facetAddress;
            removeFunction(ds, oldFacetAddress, selector);
        }
    }

    function addFacet(LibDiamond.DiamondStorage storage ds, address _facetAddress) internal {
        enforceHasContractCode(_facetAddress, "LibDiamondCut: New facet has no code");
        ds.facetFunctionSelectors[_facetAddress].facetAddressPosition = ds.facetAddresses.length;
        ds.facetAddresses.push(_facetAddress);
    }

    function addFunction(LibDiamond.DiamondStorage storage ds, bytes4 _selector, uint96 _selectorPosition, address _facetAddress) internal {
        ds.selectorToFacetAndPosition[_selector].functionSelectorPosition = _selectorPosition;
        ds.facetFunctionSelectors[_facetAddress].functionSelectors.push(_selector);
        ds.selectorToFacetAndPosition[_selector].facetAddress = _facetAddress;
    }

    function removeFunction(LibDiamond.DiamondStorage storage ds, address _facetAddress, bytes4 _selector) internal {
        require(_facetAddress != address(0), "LibDiamondCut: Can't remove function that doesn't exist");

        // an immutable function is a function defined directly in a diamond
        require(_facetAddress != address(this), "LibDiamondCut: Can't remove immutable function");

        // replace selector with last selector, then delete last selector
        uint256 selectorPosition = ds.selectorToFacetAndPosition[_selector].functionSelectorPosition;
        uint256 lastSelectorPosition = ds.facetFunctionSelectors[_facetAddress].functionSelectors.length - 1;

        // if not the same then replace _selector with lastSelector
        if (selectorPosition != lastSelectorPosition) {
            bytes4 lastSelector = ds.facetFunctionSelectors[_facetAddress].functionSelectors[lastSelectorPosition];
            ds.facetFunctionSelectors[_facetAddress].functionSelectors[selectorPosition] = lastSelector;
            ds.selectorToFacetAndPosition[lastSelector].functionSelectorPosition = uint96(selectorPosition);
        }

        // delete the last selector
        ds.facetFunctionSelectors[_facetAddress].functionSelectors.pop();
        delete ds.selectorToFacetAndPosition[_selector];

        // if no more selectors for facet address then delete the facet address
        if (lastSelectorPosition == 0) {
            // replace facet address with last facet address and delete last facet address
            uint256 lastFacetAddressPosition = ds.facetAddresses.length - 1;
            uint256 facetAddressPosition = ds.facetFunctionSelectors[_facetAddress].facetAddressPosition;
            if (facetAddressPosition != lastFacetAddressPosition) {
                address lastFacetAddress = ds.facetAddresses[lastFacetAddressPosition];
                ds.facetAddresses[facetAddressPosition] = lastFacetAddress;
                ds.facetFunctionSelectors[lastFacetAddress].facetAddressPosition = facetAddressPosition;
            }
            ds.facetAddresses.pop();
            delete ds.facetFunctionSelectors[_facetAddress].facetAddressPosition;
            delete ds.facetFunctionSelectors[_facetAddress];
        }
    }

    function initializeDiamondCut(address _init, bytes memory _calldata) internal {
        if (_init == address(0)) {
            require(_calldata.length == 0, "LibDiamondCut: _init is address(0) but_calldata is not empty");
        } else {
            require(_calldata.length > 0, "LibDiamondCut: _calldata is empty but _init is not address(0)");
            if (_init != address(this)) {
                enforceHasContractCode(_init, "LibDiamondCut: _init address has no code");
            }
            (bool success, bytes memory error) = _init.delegatecall(_calldata);
            if (!success) {
                if (error.length > 0) {
                    // bubble up the error
                    revert(string(error));
                } else {
                    revert("LibDiamondCut: _init function reverted");
                }
            }
        }
    }

    function enforceHasContractCode(address _contract, string memory _errorMessage) internal view {
        uint256 contractSize;
        assembly {
            contractSize := extcodesize(_contract)
        }
        require(contractSize > 0, _errorMessage);
    }
}