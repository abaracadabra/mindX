// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../transparent/DAIO_TransparentProxy.sol";
import "../beacon/DAIO_BeaconProxy.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Create2.sol";

/**
 * @title DAIO_ProxyFactory
 * @notice Universal proxy factory for DAIO ecosystem with governance integration
 * @dev Deploys and manages transparent and beacon proxies with constitutional compliance
 */
contract DAIO_ProxyFactory is AccessControl, ReentrancyGuard {
    bytes32 public constant FACTORY_ADMIN_ROLE = keccak256("FACTORY_ADMIN_ROLE");
    bytes32 public constant PROXY_DEPLOYER_ROLE = keccak256("PROXY_DEPLOYER_ROLE");
    bytes32 public constant BEACON_MANAGER_ROLE = keccak256("BEACON_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Proxy deployment configuration
    struct ProxyConfig {
        ProxyType proxyType;           // Type of proxy to deploy
        address implementation;        // Implementation address (for transparent)
        address beacon;               // Beacon address (for beacon proxies)
        address admin;                // Proxy admin address
        bytes initData;               // Initialization data
        string salt;                  // Salt for Create2 deployment
        string purpose;               // Purpose description
        string version;               // Version identifier
        bool predictableDeploy;       // Whether to use Create2
    }

    enum ProxyType {
        TRANSPARENT,                  // Transparent upgradeable proxy
        BEACON,                       // Beacon proxy
        MINIMAL,                      // Minimal proxy (EIP-1167)
        CUSTOM                        // Custom proxy implementation
    }

    // Deployment tracking
    struct DeploymentRecord {
        address deployer;             // Who deployed the proxy
        uint256 deploymentTime;       // When deployed
        ProxyType proxyType;          // Type of proxy
        address implementation;       // Implementation address
        address admin;                // Admin address
        string purpose;               // Purpose description
        string version;               // Version identifier
        bool isActive;                // Whether proxy is active
        uint256 upgradeCount;         // Number of upgrades performed
    }

    // Factory statistics
    struct FactoryStats {
        uint256 totalProxiesDeployed; // Total proxies deployed
        uint256 transparentProxies;   // Number of transparent proxies
        uint256 beaconProxies;        // Number of beacon proxies
        uint256 minimalProxies;       // Number of minimal proxies
        uint256 activeProxies;        // Number of active proxies
        uint256 totalUpgrades;        // Total upgrades performed
    }

    // DAIO Constitutional Integration
    struct ConstitutionalLimits {
        uint256 maxProxiesPerDeployer; // Maximum proxies per deployer
        uint256 maxDailyDeployments;   // Maximum daily deployments
        uint256 deploymentFee;         // Fee for proxy deployment
        address treasuryContract;      // DAIO treasury contract
        address executiveGovernance;   // CEO + Seven Soldiers contract
        bool constitutionalCompliance; // Whether constitutional compliance is enforced
        uint256 gasLimitPerDeploy;     // Gas limit per deployment
    }

    // State variables
    mapping(address => DeploymentRecord) public deploymentRecords; // proxy -> deployment info
    mapping(address => address[]) public deployerProxies;         // deployer -> proxy addresses
    mapping(string => address) public purposeToProxy;             // purpose -> proxy address
    mapping(uint256 => uint256) public dailyDeployments;          // day -> deployment count

    address[] public allProxies;
    FactoryStats public factoryStats;
    ConstitutionalLimits public constitutionalLimits;

    // Template contracts for cloning
    address public transparentProxyTemplate;
    address public beaconProxyTemplate;
    address public proxyAdminTemplate;
    address public beaconTemplate;

    // Events
    event ProxyDeployed(
        address indexed proxy,
        ProxyType indexed proxyType,
        address indexed deployer,
        address implementation,
        string purpose,
        string version
    );
    event ProxyUpgraded(
        address indexed proxy,
        address indexed newImplementation,
        string newVersion,
        address upgrader
    );
    event ProxyDeactivated(
        address indexed proxy,
        string reason,
        address deactivator
    );
    event BeaconCreated(
        address indexed beacon,
        address indexed implementation,
        string version,
        address creator
    );
    event FactoryConfigUpdated(
        string parameter,
        uint256 oldValue,
        uint256 newValue,
        address updater
    );
    event ConstitutionalComplianceCheck(
        bool compliant,
        string reason,
        address deployer
    );
    event EmergencyProxyShutdown(
        address indexed proxy,
        string reason,
        address emergency_executor
    );

    /**
     * @notice Initialize DAIO Proxy Factory
     * @param _treasuryContract DAIO treasury contract
     * @param _executiveGovernance CEO + Seven Soldiers governance
     * @param admin Admin address for role management
     */
    constructor(
        address _treasuryContract,
        address _executiveGovernance,
        address admin
    ) {
        require(admin != address(0), "Invalid admin address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(FACTORY_ADMIN_ROLE, admin);
        _grantRole(PROXY_DEPLOYER_ROLE, admin);
        _grantRole(BEACON_MANAGER_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        // Initialize constitutional limits
        constitutionalLimits = ConstitutionalLimits({
            maxProxiesPerDeployer: 50,      // 50 proxies max per deployer
            maxDailyDeployments: 100,       // 100 deployments per day max
            deploymentFee: 0.01 ether,      // 0.01 ETH deployment fee
            treasuryContract: _treasuryContract,
            executiveGovernance: _executiveGovernance,
            constitutionalCompliance: true,
            gasLimitPerDeploy: 3000000      // 3M gas limit per deployment
        });

        // Initialize factory stats
        factoryStats = FactoryStats({
            totalProxiesDeployed: 0,
            transparentProxies: 0,
            beaconProxies: 0,
            minimalProxies: 0,
            activeProxies: 0,
            totalUpgrades: 0
        });
    }

    /**
     * @notice Deploy proxy using configuration
     * @param config Proxy deployment configuration
     * @return proxy Deployed proxy address
     */
    function deployProxy(ProxyConfig memory config) external payable nonReentrant returns (address proxy) {
        require(msg.value >= constitutionalLimits.deploymentFee, "Insufficient deployment fee");

        // Check constitutional compliance
        _checkConstitutionalCompliance(msg.sender);

        // Validate configuration
        _validateProxyConfig(config);

        // Deploy based on proxy type
        if (config.proxyType == ProxyType.TRANSPARENT) {
            proxy = _deployTransparentProxy(config);
        } else if (config.proxyType == ProxyType.BEACON) {
            proxy = _deployBeaconProxy(config);
        } else if (config.proxyType == ProxyType.MINIMAL) {
            proxy = _deployMinimalProxy(config);
        } else {
            revert("Unsupported proxy type");
        }

        // Record deployment
        _recordDeployment(proxy, config);

        // Send fee to treasury
        if (msg.value > 0 && constitutionalLimits.treasuryContract != address(0)) {
            payable(constitutionalLimits.treasuryContract).transfer(msg.value);
        }

        emit ProxyDeployed(
            proxy,
            config.proxyType,
            msg.sender,
            config.implementation != address(0) ? config.implementation : config.beacon,
            config.purpose,
            config.version
        );

        return proxy;
    }

    /**
     * @notice Deploy transparent proxy
     * @param config Proxy configuration
     * @return proxy Deployed proxy address
     */
    function _deployTransparentProxy(ProxyConfig memory config) internal returns (address proxy) {
        require(config.implementation != address(0), "Invalid implementation");
        require(config.admin != address(0), "Invalid admin");

        if (config.predictableDeploy) {
            bytes32 salt = keccak256(abi.encodePacked(config.salt, msg.sender));
            bytes memory bytecode = abi.encodePacked(
                type(DAIO_TransparentProxy).creationCode,
                abi.encode(config.implementation, config.admin, config.initData)
            );
            proxy = Create2.deploy(0, salt, bytecode);
        } else {
            proxy = address(new DAIO_TransparentProxy(
                config.implementation,
                config.admin,
                config.initData
            ));
        }

        factoryStats.transparentProxies++;
        return proxy;
    }

    /**
     * @notice Deploy beacon proxy
     * @param config Proxy configuration
     * @return proxy Deployed proxy address
     */
    function _deployBeaconProxy(ProxyConfig memory config) internal returns (address proxy) {
        require(config.beacon != address(0), "Invalid beacon");

        if (config.predictableDeploy) {
            bytes32 salt = keccak256(abi.encodePacked(config.salt, msg.sender));
            bytes memory bytecode = abi.encodePacked(
                type(DAIO_BeaconProxy).creationCode,
                abi.encode(config.beacon, config.initData)
            );
            proxy = Create2.deploy(0, salt, bytecode);
        } else {
            proxy = address(new DAIO_BeaconProxy(config.beacon, config.initData));
        }

        factoryStats.beaconProxies++;
        return proxy;
    }

    /**
     * @notice Deploy minimal proxy (EIP-1167)
     * @param config Proxy configuration
     * @return proxy Deployed proxy address
     */
    function _deployMinimalProxy(ProxyConfig memory config) internal returns (address proxy) {
        require(config.implementation != address(0), "Invalid implementation");

        bytes memory bytecode = abi.encodePacked(
            hex"3d602d80600a3d3981f3363d3d373d3d3d363d73",
            config.implementation,
            hex"5af43d82803e903d91602b57fd5bf3"
        );

        if (config.predictableDeploy) {
            bytes32 salt = keccak256(abi.encodePacked(config.salt, msg.sender));
            proxy = Create2.deploy(0, salt, bytecode);
        } else {
            assembly {
                proxy := create(0, add(bytecode, 0x20), mload(bytecode))
            }
        }

        require(proxy != address(0), "Minimal proxy deployment failed");

        // Initialize if init data provided
        if (config.initData.length > 0) {
            (bool success, ) = proxy.call(config.initData);
            require(success, "Minimal proxy initialization failed");
        }

        factoryStats.minimalProxies++;
        return proxy;
    }

    /**
     * @notice Create new beacon
     * @param implementation Initial implementation
     * @param version Initial version
     * @param admin Beacon admin
     * @return beacon Deployed beacon address
     */
    function createBeacon(
        address implementation,
        string memory version,
        address admin
    ) external onlyRole(BEACON_MANAGER_ROLE) returns (address beacon) {
        require(implementation != address(0), "Invalid implementation");
        require(admin != address(0), "Invalid admin");

        // Create CEO + Seven Soldiers addresses array (simplified for example)
        address[7] memory executives = [
            address(0x1), // CISO placeholder
            address(0x2), // CTO placeholder
            address(0x3), // CRO placeholder
            address(0x4), // CFO placeholder
            address(0x5), // CPO placeholder
            address(0x6), // COO placeholder
            address(0x7)  // CLO placeholder
        ];

        beacon = address(new DAIO_UpgradeableBeacon(
            implementation,
            version,
            admin, // CEO address
            executives,
            constitutionalLimits.treasuryContract,
            address(0), // Constitution contract
            admin
        ));

        emit BeaconCreated(beacon, implementation, version, msg.sender);
        return beacon;
    }

    /**
     * @notice Predict proxy address for Create2 deployment
     * @param config Proxy configuration
     * @param deployer Deployer address
     * @return predicted Predicted proxy address
     */
    function predictProxyAddress(
        ProxyConfig memory config,
        address deployer
    ) external view returns (address predicted) {
        require(config.predictableDeploy, "Not predictable deployment");

        bytes32 salt = keccak256(abi.encodePacked(config.salt, deployer));
        bytes memory bytecode;

        if (config.proxyType == ProxyType.TRANSPARENT) {
            bytecode = abi.encodePacked(
                type(DAIO_TransparentProxy).creationCode,
                abi.encode(config.implementation, config.admin, config.initData)
            );
        } else if (config.proxyType == ProxyType.BEACON) {
            bytecode = abi.encodePacked(
                type(DAIO_BeaconProxy).creationCode,
                abi.encode(config.beacon, config.initData)
            );
        } else if (config.proxyType == ProxyType.MINIMAL) {
            bytecode = abi.encodePacked(
                hex"3d602d80600a3d3981f3363d3d373d3d3d363d73",
                config.implementation,
                hex"5af43d82803e903d91602b57fd5bf3"
            );
        } else {
            revert("Unsupported proxy type for prediction");
        }

        return Create2.computeAddress(salt, keccak256(bytecode), address(this));
    }

    /**
     * @notice Batch deploy multiple proxies
     * @param configs Array of proxy configurations
     * @return proxies Array of deployed proxy addresses
     */
    function batchDeployProxies(
        ProxyConfig[] memory configs
    ) external payable nonReentrant returns (address[] memory proxies) {
        require(configs.length <= 10, "Too many proxies in batch");
        require(
            msg.value >= constitutionalLimits.deploymentFee * configs.length,
            "Insufficient deployment fee"
        );

        // Check constitutional compliance
        _checkConstitutionalCompliance(msg.sender);

        proxies = new address[](configs.length);

        for (uint256 i = 0; i < configs.length; i++) {
            // Validate configuration
            _validateProxyConfig(configs[i]);

            // Deploy proxy
            if (configs[i].proxyType == ProxyType.TRANSPARENT) {
                proxies[i] = _deployTransparentProxy(configs[i]);
            } else if (configs[i].proxyType == ProxyType.BEACON) {
                proxies[i] = _deployBeaconProxy(configs[i]);
            } else if (configs[i].proxyType == ProxyType.MINIMAL) {
                proxies[i] = _deployMinimalProxy(configs[i]);
            }

            // Record deployment
            _recordDeployment(proxies[i], configs[i]);

            emit ProxyDeployed(
                proxies[i],
                configs[i].proxyType,
                msg.sender,
                configs[i].implementation != address(0) ? configs[i].implementation : configs[i].beacon,
                configs[i].purpose,
                configs[i].version
            );
        }

        // Send fee to treasury
        if (msg.value > 0 && constitutionalLimits.treasuryContract != address(0)) {
            payable(constitutionalLimits.treasuryContract).transfer(msg.value);
        }

        return proxies;
    }

    /**
     * @notice Deactivate proxy
     * @param proxy Proxy address to deactivate
     * @param reason Deactivation reason
     */
    function deactivateProxy(address proxy, string memory reason) external {
        require(
            deploymentRecords[proxy].deployer == msg.sender || hasRole(EMERGENCY_ROLE, msg.sender),
            "Not authorized"
        );
        require(deploymentRecords[proxy].isActive, "Proxy already inactive");

        deploymentRecords[proxy].isActive = false;
        factoryStats.activeProxies--;

        emit ProxyDeactivated(proxy, reason, msg.sender);
    }

    /**
     * @notice Emergency shutdown proxy
     * @param proxy Proxy address
     * @param reason Emergency reason
     */
    function emergencyShutdownProxy(
        address proxy,
        string memory reason
    ) external onlyRole(EMERGENCY_ROLE) {
        require(deploymentRecords[proxy].isActive, "Proxy already inactive");

        deploymentRecords[proxy].isActive = false;
        factoryStats.activeProxies--;

        emit EmergencyProxyShutdown(proxy, reason, msg.sender);
    }

    /**
     * @notice Update constitutional limits
     * @param maxProxiesPerDeployer New max proxies per deployer
     * @param maxDailyDeployments New max daily deployments
     * @param deploymentFee New deployment fee
     */
    function updateConstitutionalLimits(
        uint256 maxProxiesPerDeployer,
        uint256 maxDailyDeployments,
        uint256 deploymentFee
    ) external onlyRole(FACTORY_ADMIN_ROLE) {
        uint256 oldMaxProxies = constitutionalLimits.maxProxiesPerDeployer;
        uint256 oldMaxDaily = constitutionalLimits.maxDailyDeployments;
        uint256 oldFee = constitutionalLimits.deploymentFee;

        constitutionalLimits.maxProxiesPerDeployer = maxProxiesPerDeployer;
        constitutionalLimits.maxDailyDeployments = maxDailyDeployments;
        constitutionalLimits.deploymentFee = deploymentFee;

        emit FactoryConfigUpdated("maxProxiesPerDeployer", oldMaxProxies, maxProxiesPerDeployer, msg.sender);
        emit FactoryConfigUpdated("maxDailyDeployments", oldMaxDaily, maxDailyDeployments, msg.sender);
        emit FactoryConfigUpdated("deploymentFee", oldFee, deploymentFee, msg.sender);
    }

    // Internal Functions

    function _validateProxyConfig(ProxyConfig memory config) internal pure {
        if (config.proxyType == ProxyType.TRANSPARENT) {
            require(config.implementation != address(0), "Invalid implementation for transparent proxy");
            require(config.admin != address(0), "Invalid admin for transparent proxy");
        } else if (config.proxyType == ProxyType.BEACON) {
            require(config.beacon != address(0), "Invalid beacon for beacon proxy");
        } else if (config.proxyType == ProxyType.MINIMAL) {
            require(config.implementation != address(0), "Invalid implementation for minimal proxy");
        }
    }

    function _checkConstitutionalCompliance(address deployer) internal {
        if (!constitutionalLimits.constitutionalCompliance) return;

        bool compliant = true;
        string memory reason = "Deployment within constitutional limits";

        // Check max proxies per deployer
        if (deployerProxies[deployer].length >= constitutionalLimits.maxProxiesPerDeployer) {
            compliant = false;
            reason = "Deployer proxy limit exceeded";
        }

        // Check daily deployment limit
        uint256 currentDay = block.timestamp / 86400;
        if (dailyDeployments[currentDay] >= constitutionalLimits.maxDailyDeployments) {
            compliant = false;
            reason = "Daily deployment limit exceeded";
        }

        emit ConstitutionalComplianceCheck(compliant, reason, deployer);
        require(compliant, reason);
    }

    function _recordDeployment(address proxy, ProxyConfig memory config) internal {
        // Record deployment info
        deploymentRecords[proxy] = DeploymentRecord({
            deployer: msg.sender,
            deploymentTime: block.timestamp,
            proxyType: config.proxyType,
            implementation: config.implementation != address(0) ? config.implementation : config.beacon,
            admin: config.admin,
            purpose: config.purpose,
            version: config.version,
            isActive: true,
            upgradeCount: 0
        });

        // Add to deployer's proxy list
        deployerProxies[msg.sender].push(proxy);

        // Add to global proxy list
        allProxies.push(proxy);

        // Update purpose mapping if provided
        if (bytes(config.purpose).length > 0) {
            purposeToProxy[config.purpose] = proxy;
        }

        // Update daily deployment count
        uint256 currentDay = block.timestamp / 86400;
        dailyDeployments[currentDay]++;

        // Update factory stats
        factoryStats.totalProxiesDeployed++;
        factoryStats.activeProxies++;
    }

    /**
     * @notice Get proxies deployed by address
     * @param deployer Deployer address
     * @return proxies Array of proxy addresses
     */
    function getProxiesByDeployer(address deployer) external view returns (address[] memory proxies) {
        return deployerProxies[deployer];
    }

    /**
     * @notice Get proxy by purpose
     * @param purpose Purpose string
     * @return proxy Proxy address
     */
    function getProxyByPurpose(string memory purpose) external view returns (address proxy) {
        return purposeToProxy[purpose];
    }

    /**
     * @notice Get all deployed proxies
     * @return proxies Array of all proxy addresses
     */
    function getAllProxies() external view returns (address[] memory proxies) {
        return allProxies;
    }

    /**
     * @notice Get active proxies
     * @return proxies Array of active proxy addresses
     */
    function getActiveProxies() external view returns (address[] memory proxies) {
        uint256 activeCount = 0;

        // Count active proxies
        for (uint256 i = 0; i < allProxies.length; i++) {
            if (deploymentRecords[allProxies[i]].isActive) {
                activeCount++;
            }
        }

        // Collect active proxies
        proxies = new address[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allProxies.length; i++) {
            if (deploymentRecords[allProxies[i]].isActive) {
                proxies[index] = allProxies[i];
                index++;
            }
        }

        return proxies;
    }

    /**
     * @notice Get factory statistics
     * @return stats Factory statistics
     */
    function getFactoryStats() external view returns (FactoryStats memory stats) {
        return factoryStats;
    }

    /**
     * @notice Get constitutional limits
     * @return limits Constitutional limits configuration
     */
    function getConstitutionalLimits() external view returns (ConstitutionalLimits memory limits) {
        return constitutionalLimits;
    }

    /**
     * @notice Get deployment record
     * @param proxy Proxy address
     * @return record Deployment record
     */
    function getDeploymentRecord(address proxy) external view returns (DeploymentRecord memory record) {
        return deploymentRecords[proxy];
    }
}