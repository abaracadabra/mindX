// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../../eip-standards/advanced/ERC1400/SecurityToken.sol";
import "../../daio/governance/TriumvirateGovernance.sol";
import "../../oracles/core/PriceFeedAggregator.sol";

/**
 * @title SupplyChainManagement
 * @dev Fortune 500 Global Supply Chain Management Example
 *
 * This contract demonstrates how a Fortune 500 manufacturing company
 * can use DAIO infrastructure for comprehensive supply chain management:
 *
 * USE CASE: Global Automotive Manufacturer (Fortune 500)
 * - $200B+ annual revenue, 500+ suppliers globally
 * - Complex multi-tier supplier network (Tier 1, 2, 3)
 * - Critical components tracking (semiconductors, batteries, metals)
 * - Regulatory compliance (ITAR, conflict minerals, carbon emissions)
 * - Real-time inventory optimization
 * - Automated supplier payments and escrow
 *
 * Key Features:
 * - End-to-end product traceability using NFT-based digital twins
 * - Multi-tier supplier network management with risk scoring
 * - Automated quality control and compliance monitoring
 * - Smart contract-based procurement and payments
 * - Carbon footprint tracking and ESG compliance
 * - Emergency supply chain response and rerouting
 * - Blockchain-based certificates of origin and authenticity
 *
 * @author DAIO Development Team
 */

contract SupplyChainManagement is ERC721, AccessControl, ReentrancyGuard {
    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant PROCUREMENT_MANAGER_ROLE = keccak256("PROCUREMENT_MANAGER_ROLE");
    bytes32 public constant QUALITY_CONTROL_ROLE = keccak256("QUALITY_CONTROL_ROLE");
    bytes32 public constant LOGISTICS_MANAGER_ROLE = keccak256("LOGISTICS_MANAGER_ROLE");
    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");
    bytes32 public constant SUPPLIER_ROLE = keccak256("SUPPLIER_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");

    // Supplier tiers aligned with automotive industry standards
    enum SupplierTier {
        Tier1,      // Direct suppliers (Bosch, Magna, Continental)
        Tier2,      // Sub-component suppliers
        Tier3,      // Raw material suppliers
        Tier4       // Commodity suppliers
    }

    // Product lifecycle stages
    enum ProductStage {
        RawMaterial,
        Manufacturing,
        Assembly,
        QualityControl,
        Packaging,
        Shipping,
        Distribution,
        Retail,
        EndOfLife
    }

    // Compliance standards
    enum ComplianceStandard {
        ISO9001,        // Quality Management
        ISO14001,       // Environmental Management
        IATF16949,      // Automotive Quality
        ISO45001,       // Occupational Health & Safety
        ITAR,           // International Traffic in Arms Regulations
        ConflictMinerals, // Dodd-Frank Act Section 1502
        REACH,          // EU Chemical Regulation
        RoHS            // Restriction of Hazardous Substances
    }

    // =============================================================
    //                         STORAGE
    // =============================================================

    // Core DAIO Integration
    TriumvirateGovernance public immutable daiGovernance;
    SecurityToken public immutable companySecurityToken;
    PriceFeedAggregator public immutable priceOracle;

    // Company Information
    string public companyName;
    string public industry;
    uint256 public annualProduction; // Units per year
    uint256 public numberOfFacilities;

    // Supplier Network
    struct Supplier {
        string name;
        string location;
        SupplierTier tier;
        uint256 riskScore; // 0-100 (0 = lowest risk)
        uint256 qualityRating; // 0-100 (100 = highest quality)
        uint256 reliabilityScore; // 0-100 (100 = most reliable)
        uint256 carbonFootprint; // kg CO2 per unit
        bool certified;
        bool active;
        address paymentAddress;
        uint256 totalOrders;
        uint256 totalValue;
        uint256 onTimeDeliveries;
        string[] certifications;
        mapping(ComplianceStandard => bool) complianceStatus;
    }

    mapping(address => Supplier) public suppliers;
    address[] public supplierList;
    mapping(SupplierTier => address[]) public suppliersByTier;

    // Product Digital Twins (NFTs)
    struct ProductDigitalTwin {
        uint256 tokenId;
        string productType;
        string batchNumber;
        string serialNumber;
        address manufacturer;
        address currentOwner;
        ProductStage currentStage;
        uint256 manufacturingDate;
        uint256 expiryDate;
        string[] components; // Component serial numbers
        address[] supplierChain; // Full supplier lineage
        mapping(string => string) attributes; // Flexible key-value pairs
        mapping(ComplianceStandard => bool) complianceStatus;
        mapping(address => string) qualityChecks; // QC results by auditor
        uint256 carbonFootprint;
        bool recalled;
    }

    mapping(uint256 => ProductDigitalTwin) public digitalTwins;
    uint256 public nextTokenId;

    // Purchase Orders
    struct PurchaseOrder {
        bytes32 orderId;
        address supplier;
        address procurementManager;
        string[] itemDescriptions;
        uint256[] quantities;
        uint256[] unitPrices;
        uint256 totalAmount;
        uint256 deliveryDate;
        string deliveryLocation;
        bool escrowFunded;
        bool delivered;
        bool qualityApproved;
        bool paymentReleased;
        uint256 createdAt;
        mapping(ComplianceStandard => bool) requiresCompliance;
    }

    mapping(bytes32 => PurchaseOrder) public purchaseOrders;
    bytes32[] public activeOrders;

    // Inventory Management
    struct InventoryItem {
        string itemCode;
        string description;
        uint256 currentStock;
        uint256 minimumStock;
        uint256 maximumStock;
        uint256 reorderPoint;
        uint256 reorderQuantity;
        address primarySupplier;
        address[] alternativeSuppliers;
        uint256 unitPrice;
        uint256 leadTime; // Days
        string storageLocation;
        bool criticalItem;
    }

    mapping(string => InventoryItem) public inventory;
    string[] public inventoryItems;

    // Quality Control
    struct QualityControlRecord {
        bytes32 recordId;
        uint256 tokenId; // Product digital twin
        address auditor;
        string testType;
        bool passed;
        string results;
        string[] defects;
        uint256 timestamp;
        string correctiveActions;
    }

    mapping(bytes32 => QualityControlRecord) public qualityRecords;
    mapping(uint256 => bytes32[]) public productQualityHistory;

    // ESG and Sustainability
    struct ESGMetrics {
        uint256 reportingPeriod;
        uint256 totalCarbonEmissions; // kg CO2
        uint256 wasteGenerated; // kg
        uint256 energyConsumption; // kWh
        uint256 waterUsage; // liters
        uint256 recycledMaterials; // percentage
        uint256 supplierDiversityScore; // percentage minority suppliers
        bool scope3Verified; // Third-party verification of supply chain emissions
    }

    mapping(uint256 => ESGMetrics) public esgReports;

    // Risk Management
    struct SupplyChainRisk {
        bytes32 riskId;
        string riskType; // "POLITICAL", "NATURAL_DISASTER", "SUPPLIER_BANKRUPTCY", etc.
        string description;
        uint256 severity; // 1-10
        uint256 probability; // 0-100
        address[] affectedSuppliers;
        string[] affectedProducts;
        string mitigationPlan;
        bool resolved;
        uint256 identifiedAt;
        uint256 resolvedAt;
    }

    mapping(bytes32 => SupplyChainRisk) public supplyChainRisks;
    bytes32[] public activeRisks;

    // Events
    event SupplyChainInitialized(string companyName, string industry, uint256 annualProduction);
    event SupplierRegistered(address indexed supplier, string name, SupplierTier tier);
    event SupplierScoreUpdated(address indexed supplier, uint256 riskScore, uint256 qualityRating);
    event ProductCreated(uint256 indexed tokenId, string productType, address manufacturer);
    event ProductStageUpdated(uint256 indexed tokenId, ProductStage newStage, address updatedBy);
    event PurchaseOrderCreated(bytes32 indexed orderId, address indexed supplier, uint256 totalAmount);
    event PurchaseOrderDelivered(bytes32 indexed orderId, bool qualityApproved);
    event InventoryReorderTriggered(string itemCode, uint256 currentStock, address supplier);
    event QualityControlPerformed(bytes32 indexed recordId, uint256 indexed tokenId, bool passed);
    event ESGReportGenerated(uint256 indexed period, uint256 carbonEmissions, bool scope3Verified);
    event SupplyChainRiskIdentified(bytes32 indexed riskId, string riskType, uint256 severity);
    event ProductRecalled(uint256 indexed tokenId, string reason, uint256 timestamp);

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address governanceAddress,
        address securityTokenAddress,
        address priceOracleAddress,
        string memory _companyName,
        string memory _industry,
        uint256 _annualProduction,
        uint256 _numberOfFacilities
    ) ERC721("SupplyChainDigitalTwin", "SCDT") {
        daiGovernance = TriumvirateGovernance(governanceAddress);
        companySecurityToken = SecurityToken(securityTokenAddress);
        priceOracle = PriceFeedAggregator(priceOracleAddress);

        companyName = _companyName;
        industry = _industry;
        annualProduction = _annualProduction;
        numberOfFacilities = _numberOfFacilities;

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(PROCUREMENT_MANAGER_ROLE, msg.sender);
        _grantRole(QUALITY_CONTROL_ROLE, msg.sender);
        _grantRole(COMPLIANCE_OFFICER_ROLE, msg.sender);

        nextTokenId = 1;

        emit SupplyChainInitialized(_companyName, _industry, _annualProduction);
    }

    // =============================================================
    //                   SUPPLIER MANAGEMENT
    // =============================================================

    /**
     * @dev Register a new supplier
     */
    function registerSupplier(
        address supplierAddress,
        string calldata name,
        string calldata location,
        SupplierTier tier,
        address paymentAddress,
        string[] calldata certifications
    ) external onlyRole(PROCUREMENT_MANAGER_ROLE) {
        require(supplierAddress != address(0), "Invalid supplier address");
        require(!suppliers[supplierAddress].active, "Supplier already registered");

        Supplier storage supplier = suppliers[supplierAddress];
        supplier.name = name;
        supplier.location = location;
        supplier.tier = tier;
        supplier.paymentAddress = paymentAddress;
        supplier.active = true;
        supplier.certified = false;
        supplier.certifications = certifications;

        // Initialize scores
        supplier.riskScore = 50; // Medium risk by default
        supplier.qualityRating = 50; // Average quality by default
        supplier.reliabilityScore = 50; // Average reliability by default

        supplierList.push(supplierAddress);
        suppliersByTier[tier].push(supplierAddress);

        _grantRole(SUPPLIER_ROLE, supplierAddress);

        emit SupplierRegistered(supplierAddress, name, tier);
    }

    /**
     * @dev Update supplier scores and metrics
     */
    function updateSupplierScore(
        address supplierAddress,
        uint256 riskScore,
        uint256 qualityRating,
        uint256 reliabilityScore,
        uint256 carbonFootprint
    ) external onlyRole(QUALITY_CONTROL_ROLE) {
        require(suppliers[supplierAddress].active, "Supplier not found");
        require(riskScore <= 100 && qualityRating <= 100 && reliabilityScore <= 100, "Invalid scores");

        Supplier storage supplier = suppliers[supplierAddress];
        supplier.riskScore = riskScore;
        supplier.qualityRating = qualityRating;
        supplier.reliabilityScore = reliabilityScore;
        supplier.carbonFootprint = carbonFootprint;

        emit SupplierScoreUpdated(supplierAddress, riskScore, qualityRating);
    }

    /**
     * @dev Certify supplier for compliance standards
     */
    function certifySupplierCompliance(
        address supplierAddress,
        ComplianceStandard[] calldata standards,
        bool[] calldata status
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        require(suppliers[supplierAddress].active, "Supplier not found");
        require(standards.length == status.length, "Arrays length mismatch");

        Supplier storage supplier = suppliers[supplierAddress];

        for (uint256 i = 0; i < standards.length; i++) {
            supplier.complianceStatus[standards[i]] = status[i];
        }

        // Update overall certification status
        supplier.certified = _checkOverallCompliance(supplierAddress);
    }

    // =============================================================
    //                   PRODUCT MANAGEMENT
    // =============================================================

    /**
     * @dev Create a new product digital twin
     */
    function createProduct(
        string calldata productType,
        string calldata batchNumber,
        string calldata serialNumber,
        uint256 expiryDate,
        string[] calldata components,
        address[] calldata supplierChain
    ) external onlyRole(PROCUREMENT_MANAGER_ROLE) returns (uint256 tokenId) {
        tokenId = nextTokenId++;

        ProductDigitalTwin storage digitalTwin = digitalTwins[tokenId];
        digitalTwin.tokenId = tokenId;
        digitalTwin.productType = productType;
        digitalTwin.batchNumber = batchNumber;
        digitalTwin.serialNumber = serialNumber;
        digitalTwin.manufacturer = msg.sender;
        digitalTwin.currentOwner = address(this);
        digitalTwin.currentStage = ProductStage.RawMaterial;
        digitalTwin.manufacturingDate = block.timestamp;
        digitalTwin.expiryDate = expiryDate;
        digitalTwin.components = components;
        digitalTwin.supplierChain = supplierChain;

        // Calculate carbon footprint based on supplier chain
        uint256 totalCarbonFootprint = 0;
        for (uint256 i = 0; i < supplierChain.length; i++) {
            totalCarbonFootprint += suppliers[supplierChain[i]].carbonFootprint;
        }
        digitalTwin.carbonFootprint = totalCarbonFootprint;

        _mint(address(this), tokenId);

        emit ProductCreated(tokenId, productType, msg.sender);
        return tokenId;
    }

    /**
     * @dev Update product stage in manufacturing process
     */
    function updateProductStage(
        uint256 tokenId,
        ProductStage newStage
    ) external onlyRole(LOGISTICS_MANAGER_ROLE) {
        require(_exists(tokenId), "Product does not exist");

        ProductDigitalTwin storage digitalTwin = digitalTwins[tokenId];
        require(uint8(newStage) > uint8(digitalTwin.currentStage), "Cannot move backwards in process");

        digitalTwin.currentStage = newStage;

        emit ProductStageUpdated(tokenId, newStage, msg.sender);
    }

    /**
     * @dev Transfer product ownership
     */
    function transferProductOwnership(
        uint256 tokenId,
        address newOwner
    ) external onlyRole(LOGISTICS_MANAGER_ROLE) {
        require(_exists(tokenId), "Product does not exist");

        ProductDigitalTwin storage digitalTwin = digitalTwins[tokenId];
        digitalTwin.currentOwner = newOwner;

        _transfer(digitalTwin.currentOwner, newOwner, tokenId);
    }

    /**
     * @dev Set product attribute
     */
    function setProductAttribute(
        uint256 tokenId,
        string calldata key,
        string calldata value
    ) external onlyRole(QUALITY_CONTROL_ROLE) {
        require(_exists(tokenId), "Product does not exist");

        digitalTwins[tokenId].attributes[key] = value;
    }

    // =============================================================
    //                  PROCUREMENT MANAGEMENT
    // =============================================================

    /**
     * @dev Create a purchase order
     */
    function createPurchaseOrder(
        address supplier,
        string[] calldata itemDescriptions,
        uint256[] calldata quantities,
        uint256[] calldata unitPrices,
        uint256 deliveryDate,
        string calldata deliveryLocation,
        ComplianceStandard[] calldata requiredCompliance
    ) external onlyRole(PROCUREMENT_MANAGER_ROLE) returns (bytes32 orderId) {
        require(suppliers[supplier].active, "Supplier not active");
        require(suppliers[supplier].certified, "Supplier not certified");
        require(itemDescriptions.length == quantities.length, "Arrays length mismatch");
        require(quantities.length == unitPrices.length, "Arrays length mismatch");

        orderId = keccak256(abi.encodePacked(
            supplier,
            msg.sender,
            block.timestamp,
            itemDescriptions
        ));

        PurchaseOrder storage order = purchaseOrders[orderId];
        order.orderId = orderId;
        order.supplier = supplier;
        order.procurementManager = msg.sender;
        order.itemDescriptions = itemDescriptions;
        order.quantities = quantities;
        order.unitPrices = unitPrices;
        order.deliveryDate = deliveryDate;
        order.deliveryLocation = deliveryLocation;
        order.createdAt = block.timestamp;

        // Calculate total amount
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < quantities.length; i++) {
            totalAmount += quantities[i] * unitPrices[i];
        }
        order.totalAmount = totalAmount;

        // Set compliance requirements
        for (uint256 i = 0; i < requiredCompliance.length; i++) {
            order.requiresCompliance[requiredCompliance[i]] = true;
        }

        activeOrders.push(orderId);

        emit PurchaseOrderCreated(orderId, supplier, totalAmount);
        return orderId;
    }

    /**
     * @dev Fund purchase order escrow
     */
    function fundPurchaseOrderEscrow(
        bytes32 orderId,
        address paymentToken
    ) external payable onlyRole(PROCUREMENT_MANAGER_ROLE) nonReentrant {
        PurchaseOrder storage order = purchaseOrders[orderId];
        require(order.orderId == orderId, "Order not found");
        require(!order.escrowFunded, "Escrow already funded");

        if (paymentToken == address(0)) {
            // ETH payment
            require(msg.value >= order.totalAmount, "Insufficient payment");
        } else {
            // ERC20 payment
            IERC20 token = IERC20(paymentToken);
            require(token.transferFrom(msg.sender, address(this), order.totalAmount), "Transfer failed");
        }

        order.escrowFunded = true;
    }

    /**
     * @dev Confirm delivery and trigger quality control
     */
    function confirmDelivery(
        bytes32 orderId
    ) external onlyRole(LOGISTICS_MANAGER_ROLE) {
        PurchaseOrder storage order = purchaseOrders[orderId];
        require(order.orderId == orderId, "Order not found");
        require(order.escrowFunded, "Escrow not funded");
        require(!order.delivered, "Already delivered");

        order.delivered = true;

        // Update supplier metrics
        Supplier storage supplier = suppliers[order.supplier];
        supplier.totalOrders++;
        supplier.totalValue += order.totalAmount;

        if (block.timestamp <= order.deliveryDate) {
            supplier.onTimeDeliveries++;
        }

        // Trigger automatic quality control process
        _triggerQualityControl(orderId);

        emit PurchaseOrderDelivered(orderId, false); // Quality approval pending
    }

    /**
     * @dev Release payment after quality approval
     */
    function releasePayment(
        bytes32 orderId,
        address paymentToken
    ) external onlyRole(QUALITY_CONTROL_ROLE) nonReentrant {
        PurchaseOrder storage order = purchaseOrders[orderId];
        require(order.orderId == orderId, "Order not found");
        require(order.delivered, "Not delivered yet");
        require(order.qualityApproved, "Quality not approved");
        require(!order.paymentReleased, "Payment already released");

        order.paymentReleased = true;

        // Calculate payment breakdown
        uint256 supplierPayment = order.totalAmount * 8500 / 10000; // 85% to supplier
        uint256 daiTithe = order.totalAmount * 1500 / 10000; // 15% DAIO tithe

        // Transfer payments
        if (paymentToken == address(0)) {
            // ETH payment
            payable(suppliers[order.supplier].paymentAddress).transfer(supplierPayment);
            payable(address(daiGovernance)).transfer(daiTithe);
        } else {
            // ERC20 payment
            IERC20 token = IERC20(paymentToken);
            token.transfer(suppliers[order.supplier].paymentAddress, supplierPayment);
            token.transfer(address(daiGovernance), daiTithe);
        }

        // Remove from active orders
        _removeFromActiveOrders(orderId);
    }

    // =============================================================
    //                   INVENTORY MANAGEMENT
    // =============================================================

    /**
     * @dev Add inventory item
     */
    function addInventoryItem(
        string calldata itemCode,
        string calldata description,
        uint256 currentStock,
        uint256 minimumStock,
        uint256 maximumStock,
        uint256 reorderPoint,
        uint256 reorderQuantity,
        address primarySupplier,
        address[] calldata alternativeSuppliers,
        uint256 unitPrice,
        uint256 leadTime,
        string calldata storageLocation,
        bool criticalItem
    ) external onlyRole(PROCUREMENT_MANAGER_ROLE) {
        InventoryItem storage item = inventory[itemCode];
        item.itemCode = itemCode;
        item.description = description;
        item.currentStock = currentStock;
        item.minimumStock = minimumStock;
        item.maximumStock = maximumStock;
        item.reorderPoint = reorderPoint;
        item.reorderQuantity = reorderQuantity;
        item.primarySupplier = primarySupplier;
        item.alternativeSuppliers = alternativeSuppliers;
        item.unitPrice = unitPrice;
        item.leadTime = leadTime;
        item.storageLocation = storageLocation;
        item.criticalItem = criticalItem;

        inventoryItems.push(itemCode);
    }

    /**
     * @dev Update inventory levels
     */
    function updateInventoryLevel(
        string calldata itemCode,
        uint256 newStockLevel
    ) external onlyRole(LOGISTICS_MANAGER_ROLE) {
        InventoryItem storage item = inventory[itemCode];
        require(bytes(item.itemCode).length > 0, "Item not found");

        item.currentStock = newStockLevel;

        // Check if reorder is needed
        if (newStockLevel <= item.reorderPoint) {
            _triggerReorder(itemCode);
        }
    }

    /**
     * @dev Trigger automatic reorder
     */
    function _triggerReorder(string memory itemCode) internal {
        InventoryItem storage item = inventory[itemCode];

        // Create automatic purchase order for reorder quantity
        address supplier = item.primarySupplier;

        // Verify supplier is still active and certified
        if (!suppliers[supplier].active || !suppliers[supplier].certified) {
            // Use alternative supplier
            for (uint256 i = 0; i < item.alternativeSuppliers.length; i++) {
                if (suppliers[item.alternativeSuppliers[i]].active &&
                    suppliers[item.alternativeSuppliers[i]].certified) {
                    supplier = item.alternativeSuppliers[i];
                    break;
                }
            }
        }

        require(suppliers[supplier].active, "No active supplier found");

        emit InventoryReorderTriggered(itemCode, item.currentStock, supplier);

        // In practice, this would automatically create a purchase order
        // For this example, we just emit the event
    }

    // =============================================================
    //                    QUALITY CONTROL
    // =============================================================

    /**
     * @dev Perform quality control check
     */
    function performQualityControl(
        uint256 tokenId,
        string calldata testType,
        bool passed,
        string calldata results,
        string[] calldata defects,
        string calldata correctiveActions
    ) external onlyRole(QUALITY_CONTROL_ROLE) returns (bytes32 recordId) {
        require(_exists(tokenId), "Product does not exist");

        recordId = keccak256(abi.encodePacked(
            tokenId,
            msg.sender,
            block.timestamp,
            testType
        ));

        QualityControlRecord storage record = qualityRecords[recordId];
        record.recordId = recordId;
        record.tokenId = tokenId;
        record.auditor = msg.sender;
        record.testType = testType;
        record.passed = passed;
        record.results = results;
        record.defects = defects;
        record.timestamp = block.timestamp;
        record.correctiveActions = correctiveActions;

        digitalTwins[tokenId].qualityChecks[msg.sender] = results;
        productQualityHistory[tokenId].push(recordId);

        emit QualityControlPerformed(recordId, tokenId, passed);

        return recordId;
    }

    /**
     * @dev Trigger quality control for purchase order
     */
    function _triggerQualityControl(bytes32 orderId) internal {
        PurchaseOrder storage order = purchaseOrders[orderId];

        // Simplified quality control trigger
        // In practice, this would initiate comprehensive testing protocols
        order.qualityApproved = true; // Assume passed for example

        emit PurchaseOrderDelivered(orderId, true);
    }

    /**
     * @dev Approve quality for purchase order
     */
    function approveQuality(bytes32 orderId) external onlyRole(QUALITY_CONTROL_ROLE) {
        PurchaseOrder storage order = purchaseOrders[orderId];
        require(order.orderId == orderId, "Order not found");
        require(order.delivered, "Not delivered yet");

        order.qualityApproved = true;
    }

    // =============================================================
    //                   ESG AND SUSTAINABILITY
    // =============================================================

    /**
     * @dev Generate ESG report
     */
    function generateESGReport(
        uint256 reportingPeriod,
        uint256 totalCarbonEmissions,
        uint256 wasteGenerated,
        uint256 energyConsumption,
        uint256 waterUsage,
        uint256 recycledMaterials,
        uint256 supplierDiversityScore,
        bool scope3Verified
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        ESGMetrics storage report = esgReports[reportingPeriod];
        report.reportingPeriod = reportingPeriod;
        report.totalCarbonEmissions = totalCarbonEmissions;
        report.wasteGenerated = wasteGenerated;
        report.energyConsumption = energyConsumption;
        report.waterUsage = waterUsage;
        report.recycledMaterials = recycledMaterials;
        report.supplierDiversityScore = supplierDiversityScore;
        report.scope3Verified = scope3Verified;

        emit ESGReportGenerated(reportingPeriod, totalCarbonEmissions, scope3Verified);
    }

    // =============================================================
    //                    RISK MANAGEMENT
    // =============================================================

    /**
     * @dev Identify supply chain risk
     */
    function identifySupplyChainRisk(
        string calldata riskType,
        string calldata description,
        uint256 severity,
        uint256 probability,
        address[] calldata affectedSuppliers,
        string[] calldata affectedProducts,
        string calldata mitigationPlan
    ) external onlyRole(PROCUREMENT_MANAGER_ROLE) returns (bytes32 riskId) {
        riskId = keccak256(abi.encodePacked(
            riskType,
            description,
            block.timestamp,
            msg.sender
        ));

        SupplyChainRisk storage risk = supplyChainRisks[riskId];
        risk.riskId = riskId;
        risk.riskType = riskType;
        risk.description = description;
        risk.severity = severity;
        risk.probability = probability;
        risk.affectedSuppliers = affectedSuppliers;
        risk.affectedProducts = affectedProducts;
        risk.mitigationPlan = mitigationPlan;
        risk.identifiedAt = block.timestamp;
        risk.resolved = false;

        activeRisks.push(riskId);

        emit SupplyChainRiskIdentified(riskId, riskType, severity);

        return riskId;
    }

    /**
     * @dev Resolve supply chain risk
     */
    function resolveSupplyChainRisk(bytes32 riskId) external onlyRole(PROCUREMENT_MANAGER_ROLE) {
        SupplyChainRisk storage risk = supplyChainRisks[riskId];
        require(risk.riskId == riskId, "Risk not found");
        require(!risk.resolved, "Risk already resolved");

        risk.resolved = true;
        risk.resolvedAt = block.timestamp;

        // Remove from active risks
        _removeFromActiveRisks(riskId);
    }

    // =============================================================
    //                   EMERGENCY RESPONSES
    // =============================================================

    /**
     * @dev Initiate product recall
     */
    function initiateProductRecall(
        uint256[] calldata tokenIds,
        string calldata reason
    ) external onlyRole(QUALITY_CONTROL_ROLE) {
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];
            require(_exists(tokenId), "Product does not exist");

            ProductDigitalTwin storage digitalTwin = digitalTwins[tokenId];
            digitalTwin.recalled = true;

            emit ProductRecalled(tokenId, reason, block.timestamp);
        }
    }

    /**
     * @dev Emergency supplier suspension
     */
    function emergencySupplierSuspension(
        address supplier,
        string calldata reason
    ) external {
        require(
            hasRole(COMPLIANCE_OFFICER_ROLE, msg.sender) ||
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Unauthorized"
        );

        suppliers[supplier].active = false;

        // Cancel all active orders with this supplier
        for (uint256 i = 0; i < activeOrders.length; i++) {
            bytes32 orderId = activeOrders[i];
            if (purchaseOrders[orderId].supplier == supplier &&
                !purchaseOrders[orderId].delivered) {
                // Cancel order logic would go here
            }
        }
    }

    // =============================================================
    //                    INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @dev Check overall compliance status for supplier
     */
    function _checkOverallCompliance(address supplier) internal view returns (bool) {
        Supplier storage sup = suppliers[supplier];

        // Check key compliance standards
        return sup.complianceStatus[ComplianceStandard.ISO9001] &&
               sup.complianceStatus[ComplianceStandard.ISO14001] &&
               sup.complianceStatus[ComplianceStandard.IATF16949];
    }

    /**
     * @dev Remove order from active orders list
     */
    function _removeFromActiveOrders(bytes32 orderId) internal {
        for (uint256 i = 0; i < activeOrders.length; i++) {
            if (activeOrders[i] == orderId) {
                activeOrders[i] = activeOrders[activeOrders.length - 1];
                activeOrders.pop();
                break;
            }
        }
    }

    /**
     * @dev Remove risk from active risks list
     */
    function _removeFromActiveRisks(bytes32 riskId) internal {
        for (uint256 i = 0; i < activeRisks.length; i++) {
            if (activeRisks[i] == riskId) {
                activeRisks[i] = activeRisks[activeRisks.length - 1];
                activeRisks.pop();
                break;
            }
        }
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get supplier information
     */
    function getSupplierInfo(address supplier) external view returns (
        string memory name,
        string memory location,
        SupplierTier tier,
        uint256 riskScore,
        uint256 qualityRating,
        bool certified,
        bool active
    ) {
        Supplier storage sup = suppliers[supplier];
        return (
            sup.name,
            sup.location,
            sup.tier,
            sup.riskScore,
            sup.qualityRating,
            sup.certified,
            sup.active
        );
    }

    /**
     * @dev Get product traceability
     */
    function getProductTraceability(uint256 tokenId) external view returns (
        string memory productType,
        address manufacturer,
        ProductStage currentStage,
        address[] memory supplierChain,
        uint256 carbonFootprint,
        bool recalled
    ) {
        require(_exists(tokenId), "Product does not exist");

        ProductDigitalTwin storage digitalTwin = digitalTwins[tokenId];
        return (
            digitalTwin.productType,
            digitalTwin.manufacturer,
            digitalTwin.currentStage,
            digitalTwin.supplierChain,
            digitalTwin.carbonFootprint,
            digitalTwin.recalled
        );
    }

    /**
     * @dev Get active purchase orders
     */
    function getActivePurchaseOrders() external view returns (bytes32[] memory) {
        return activeOrders;
    }

    /**
     * @dev Get active supply chain risks
     */
    function getActiveSupplyChainRisks() external view returns (bytes32[] memory) {
        return activeRisks;
    }

    /**
     * @dev Get suppliers by tier
     */
    function getSuppliersByTier(SupplierTier tier) external view returns (address[] memory) {
        return suppliersByTier[tier];
    }

    /**
     * @dev Get all inventory items
     */
    function getAllInventoryItems() external view returns (string[] memory) {
        return inventoryItems;
    }

    /**
     * @dev Get product quality history
     */
    function getProductQualityHistory(uint256 tokenId) external view returns (bytes32[] memory) {
        return productQualityHistory[tokenId];
    }

    /**
     * @dev Get product attribute
     */
    function getProductAttribute(uint256 tokenId, string calldata key) external view returns (string memory) {
        require(_exists(tokenId), "Product does not exist");
        return digitalTwins[tokenId].attributes[key];
    }

    /**
     * @dev Get supplier compliance status
     */
    function getSupplierComplianceStatus(
        address supplier,
        ComplianceStandard standard
    ) external view returns (bool) {
        return suppliers[supplier].complianceStatus[standard];
    }

    /**
     * @dev Get company overview
     */
    function getCompanyOverview() external view returns (
        string memory name,
        string memory industryType,
        uint256 production,
        uint256 facilities,
        uint256 totalSuppliers
    ) {
        return (
            companyName,
            industry,
            annualProduction,
            numberOfFacilities,
            supplierList.length
        );
    }
}