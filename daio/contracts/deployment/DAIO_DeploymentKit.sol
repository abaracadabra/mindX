// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../DAIO_Core.sol";

/**
 * @title DAIO_DeploymentKit
 * @notice Modular deployment system for DAIO core + optional extensions
 * @dev Minimal, focused deployment without mindX dependencies
 */
contract DAIO_DeploymentKit {

    // Extension categories
    enum ExtensionCategory {
        MARKETPLACE,    // AgenticPlace, THOT trading
        IDENTITY,       // Enhanced identity systems, SoulBadger
        TREASURY,       // Advanced treasury features, bonding curves
        ANALYTICS,      // Governance analytics, reporting
        INTEGRATIONS,   // External system integrations
        EXPERIMENTAL    // Beta features, research contracts
    }

    // Pre-configured deployment templates
    enum DeploymentTemplate {
        MINIMAL,        // Just core DAIO governance
        STANDARD,       // Core + common extensions
        ENTERPRISE,     // Full feature set for organizations
        RESEARCH,       // Core + experimental features
        CUSTOM          // User-defined configuration
    }

    struct ExtensionConfig {
        string name;
        ExtensionCategory category;
        bool required;
        address implementation; // Pre-deployed implementation
        bytes initData;        // Initialization parameters
    }

    struct DeploymentPlan {
        DeploymentTemplate template;
        string deploymentName;
        address chairman;
        address ceo;
        ExtensionConfig[] selectedExtensions;
        mapping(ExtensionCategory => bool) enabledCategories;
        bytes32 configHash;
    }

    // Registry of available extensions
    mapping(ExtensionCategory => ExtensionConfig[]) public availableExtensions;
    mapping(string => address) public extensionImplementations;

    // Deployment history
    mapping(address => DAIO_Core[]) public deployedDAIOs;
    DAIO_Core[] public allDeployments;

    event DAIODeploymentCompleted(
        address indexed deployer,
        address indexed daioCoreAddress,
        DeploymentTemplate template,
        uint256 extensionsCount
    );

    constructor() {
        _registerStandardExtensions();
    }

    /**
     * @notice Deploy DAIO with selected template and extensions
     * @param template Pre-configured deployment template
     * @param deploymentName Human-readable deployment name
     * @param chairman Constitutional chairman address
     * @param ceoAddress CEO address
     * @param customExtensions Additional extensions for CUSTOM template
     * @return daioCoreAddress Address of deployed DAIO Core
     */
    function deployDAIO(
        DeploymentTemplate template,
        string memory deploymentName,
        address chairman,
        address ceoAddress,
        string[] memory customExtensions
    ) external returns (address daioCoreAddress) {
        require(chairman != address(0) && ceoAddress != address(0), "Invalid addresses");
        require(bytes(deploymentName).length > 0, "Deployment name required");

        // Deploy core DAIO
        DAIO_Core daioCore = new DAIO_Core();

        // Configure deployment
        bytes32 configHash = keccak256(abi.encode(template, deploymentName, chairman, ceoAddress, block.timestamp));

        bool success = daioCore.deployDAIOCore(
            deploymentName,
            chairman,
            ceoAddress,
            configHash
        );

        require(success, "Core deployment failed");

        // Add extensions based on template
        _addTemplateExtensions(daioCore, template, customExtensions);

        // Register deployment
        deployedDAIOs[msg.sender].push(daioCore);
        allDeployments.push(daioCore);

        emit DAIODeploymentCompleted(
            msg.sender,
            address(daioCore),
            template,
            _getExtensionCount(template)
        );

        return address(daioCore);
    }

    /**
     * @notice Get deployment templates with descriptions
     * @return templates Array of available templates
     */
    function getDeploymentTemplates() external pure returns (string[] memory templates) {
        templates = new string[](5);
        templates[0] = "MINIMAL: Core governance only - CEO + Seven Soldiers with constitutional constraints";
        templates[1] = "STANDARD: Core + Identity + Basic Treasury - Most common deployment";
        templates[2] = "ENTERPRISE: Full feature set - All extensions for complete organizational governance";
        templates[3] = "RESEARCH: Core + Experimental - Latest features for testing and research";
        templates[4] = "CUSTOM: User-selected extensions - Build your own configuration";
    }

    /**
     * @notice Get available extensions for a category
     * @param category Extension category to query
     * @return extensions Array of available extensions
     */
    function getAvailableExtensions(ExtensionCategory category) external view returns (ExtensionConfig[] memory) {
        return availableExtensions[category];
    }

    /**
     * @notice Preview deployment plan
     * @param template Template to preview
     * @param customExtensions Custom extensions for preview
     * @return extensionNames Extensions that would be deployed
     * @return estimatedGasCost Estimated gas cost
     */
    function previewDeployment(
        DeploymentTemplate template,
        string[] memory customExtensions
    ) external view returns (
        string[] memory extensionNames,
        uint256 estimatedGasCost
    ) {
        // Get extensions for template
        ExtensionConfig[] memory templateExtensions = _getTemplateExtensions(template);

        // Combine with custom extensions
        uint256 totalExtensions = templateExtensions.length + customExtensions.length;
        extensionNames = new string[](totalExtensions);

        // Add template extensions
        for (uint i = 0; i < templateExtensions.length; i++) {
            extensionNames[i] = templateExtensions[i].name;
        }

        // Add custom extensions
        for (uint i = 0; i < customExtensions.length; i++) {
            extensionNames[templateExtensions.length + i] = customExtensions[i];
        }

        // Estimate gas cost (rough calculation)
        estimatedGasCost = 15000000 + (totalExtensions * 3000000); // Base cost + extensions
    }

    /**
     * @notice Get user's deployed DAIOs
     * @param user User address
     * @return deployments Array of DAIO Core addresses
     */
    function getUserDeployments(address user) external view returns (DAIO_Core[] memory) {
        return deployedDAIOs[user];
    }

    /**
     * @notice Get deployment statistics
     * @return totalDeployments Total number of deployments
     * @return templateCounts Count per template type
     */
    function getDeploymentStats() external view returns (
        uint256 totalDeployments,
        uint256[5] memory templateCounts
    ) {
        totalDeployments = allDeployments.length;

        // Count templates (simplified - would need to track template type in deployment)
        // This is a placeholder implementation
        for (uint i = 0; i < allDeployments.length; i++) {
            templateCounts[0]++; // Simplified counting
        }
    }

    // Internal functions

    function _registerStandardExtensions() internal {
        // MARKETPLACE extensions
        availableExtensions[ExtensionCategory.MARKETPLACE].push(ExtensionConfig({
            name: "THOT_Marketplace",
            category: ExtensionCategory.MARKETPLACE,
            required: false,
            implementation: address(0), // Would be deployed separately
            initData: ""
        }));

        availableExtensions[ExtensionCategory.MARKETPLACE].push(ExtensionConfig({
            name: "AgenticPlace",
            category: ExtensionCategory.MARKETPLACE,
            required: false,
            implementation: address(0),
            initData: ""
        }));

        // IDENTITY extensions
        availableExtensions[ExtensionCategory.IDENTITY].push(ExtensionConfig({
            name: "SoulBadger",
            category: ExtensionCategory.IDENTITY,
            required: false,
            implementation: address(0),
            initData: ""
        }));

        availableExtensions[ExtensionCategory.IDENTITY].push(ExtensionConfig({
            name: "Enhanced_IDNFT",
            category: ExtensionCategory.IDENTITY,
            required: false,
            implementation: address(0),
            initData: ""
        }));

        // TREASURY extensions
        availableExtensions[ExtensionCategory.TREASURY].push(ExtensionConfig({
            name: "Bonding_Curves",
            category: ExtensionCategory.TREASURY,
            required: false,
            implementation: address(0),
            initData: ""
        }));

        availableExtensions[ExtensionCategory.TREASURY].push(ExtensionConfig({
            name: "Advanced_Treasury",
            category: ExtensionCategory.TREASURY,
            required: false,
            implementation: address(0),
            initData: ""
        }));
    }

    function _addTemplateExtensions(
        DAIO_Core daioCore,
        DeploymentTemplate template,
        string[] memory customExtensions
    ) internal {
        if (template == DeploymentTemplate.MINIMAL) {
            // No extensions - core only
            return;
        }

        if (template == DeploymentTemplate.STANDARD) {
            // Add common extensions
            _addExtensionIfAvailable(daioCore, "Enhanced_IDNFT", "identity");
            // Add more standard extensions as they're developed
        }

        if (template == DeploymentTemplate.ENTERPRISE) {
            // Add all stable extensions
            _addExtensionIfAvailable(daioCore, "THOT_Marketplace", "marketplace");
            _addExtensionIfAvailable(daioCore, "SoulBadger", "identity");
            _addExtensionIfAvailable(daioCore, "Bonding_Curves", "treasury");
        }

        if (template == DeploymentTemplate.RESEARCH) {
            // Add experimental extensions
            _addExtensionsByCategory(daioCore, ExtensionCategory.EXPERIMENTAL);
        }

        if (template == DeploymentTemplate.CUSTOM) {
            // Add user-specified extensions
            for (uint i = 0; i < customExtensions.length; i++) {
                _addExtensionIfAvailable(daioCore, customExtensions[i], "custom");
            }
        }
    }

    function _addExtensionIfAvailable(
        DAIO_Core daioCore,
        string memory extensionName,
        string memory category
    ) internal {
        address implementation = extensionImplementations[extensionName];
        if (implementation != address(0)) {
            daioCore.addExtension(
                extensionName,
                string(abi.encodePacked("Extension: ", extensionName)),
                implementation,
                category
            );
        }
    }

    function _addExtensionsByCategory(DAIO_Core daioCore, ExtensionCategory category) internal {
        ExtensionConfig[] memory extensions = availableExtensions[category];
        for (uint i = 0; i < extensions.length; i++) {
            if (extensions[i].implementation != address(0)) {
                _addExtensionIfAvailable(daioCore, extensions[i].name, "experimental");
            }
        }
    }

    function _getTemplateExtensions(DeploymentTemplate template) internal view returns (ExtensionConfig[] memory) {
        if (template == DeploymentTemplate.MINIMAL) {
            return new ExtensionConfig[](0);
        }

        // Simplified return - would implement full logic
        return availableExtensions[ExtensionCategory.IDENTITY];
    }

    function _getExtensionCount(DeploymentTemplate template) internal pure returns (uint256) {
        if (template == DeploymentTemplate.MINIMAL) return 0;
        if (template == DeploymentTemplate.STANDARD) return 2;
        if (template == DeploymentTemplate.ENTERPRISE) return 5;
        if (template == DeploymentTemplate.RESEARCH) return 3;
        return 1; // CUSTOM
    }
}