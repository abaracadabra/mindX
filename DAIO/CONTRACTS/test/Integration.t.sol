// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";
import "../src/DAIO_Constitution.sol";
import "../src/SoulBadger.sol";
import "../src/IDNFT.sol";
import "../src/KnowledgeHierarchyDAIO.sol";
import "../src/AgentFactory.sol";
import "../src/Treasury.sol";

/**
 * @title IntegrationTest
 * @dev Full integration tests for the DAIO ecosystem
 */
contract IntegrationTest is Test {
    // Contracts
    TimelockController public timelock;
    DAIO_Constitution public constitution;
    SoulBadger public soulBadger;
    IDNFT public idnft;
    KnowledgeHierarchyDAIO public knowledgeHierarchy;
    AgentFactory public agentFactory;
    Treasury public treasury;

    // Actors
    address public deployer;
    address public chairman;
    address public agent1;
    address public agent2;
    address public voter1;
    address public voter2;

    function setUp() public {
        deployer = address(this);
        chairman = makeAddr("chairman");
        agent1 = makeAddr("agent1");
        agent2 = makeAddr("agent2");
        voter1 = makeAddr("voter1");
        voter2 = makeAddr("voter2");

        // Deploy TimelockController
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);
        proposers[0] = deployer;
        executors[0] = deployer;

        timelock = new TimelockController(1 hours, proposers, executors, deployer);

        // Deploy Constitution
        constitution = new DAIO_Constitution(chairman, address(timelock));

        // Deploy SoulBadger
        soulBadger = new SoulBadger("DAIO Soul", "DSOUL", "https://daio.io/soul/");

        // Deploy IDNFT
        idnft = new IDNFT();
        idnft.setSoulBadger(address(soulBadger));

        // Deploy KnowledgeHierarchy
        knowledgeHierarchy = new KnowledgeHierarchyDAIO(timelock);

        // Deploy AgentFactory
        agentFactory = new AgentFactory(address(knowledgeHierarchy));

        // Deploy Treasury
        treasury = new Treasury(address(constitution));

        // Setup roles
        _setupRoles();
    }

    function _setupRoles() internal {
        soulBadger.grantRole(soulBadger.MINTER_ROLE(), address(idnft));
        knowledgeHierarchy.grantRole(knowledgeHierarchy.AGENT_MANAGER_ROLE(), address(agentFactory));
        knowledgeHierarchy.grantRole(knowledgeHierarchy.AGENT_MANAGER_ROLE(), deployer);
        idnft.grantRole(idnft.GOVERNANCE_ROLE(), address(knowledgeHierarchy));
        treasury.grantRole(treasury.SIGNER_ROLE(), deployer);
        constitution.grantRole(constitution.GOVERNANCE_ROLE(), address(treasury));
    }

    function test_FullAgentLifecycle() public {
        // 1. Create agent identity
        uint256 idnftTokenId = idnft.mintAgentIdentity(
            agent1,
            "MastermindAgent",
            "Strategic planning agent",
            '{"complexity": 0.9}',
            "ipfs://mastermind",
            false
        );

        // Verify identity created
        IDNFT.AgentIdentity memory identity = idnft.getAgentIdentity(idnftTokenId);
        assertEq(identity.primaryWallet, agent1);
        assertTrue(identity.isActive);

        // 2. Register agent in KnowledgeHierarchy
        bytes32 agentId = knowledgeHierarchy.registerAgent(
            agent1,
            80, // Knowledge level
            KnowledgeHierarchyDAIO.Domain.AI
        );

        // Verify registration
        KnowledgeHierarchyDAIO.Agent memory agent = knowledgeHierarchy.getAgent(agent1);
        assertEq(agent.knowledgeLevel, 80);
        assertTrue(agent.active);

        // 3. Create agent via factory
        AgentFactory.AgentCreationParams memory params = AgentFactory.AgentCreationParams({
            agentAddress: agent2,
            agentType: "BDIAgent",
            tokenName: "BDI Token",
            tokenSymbol: "BDI",
            initialTokenSupply: 1_000_000 ether,
            nftMetadata: "ipfs://bdi",
            metadataHash: keccak256("bdi_metadata")
        });

        agentFactory.grantRole(agentFactory.AGENT_CREATOR_ROLE(), deployer);
        (bytes32 factoryAgentId, address tokenAddr, uint256 nftId) = agentFactory.createAgent(params);

        // Verify factory creation
        assertTrue(factoryAgentId != bytes32(0));
        assertTrue(tokenAddr != address(0));
        assertEq(agentFactory.ownerOf(nftId), agent2);
    }

    function test_GovernanceProposalFlow() public {
        // Register agent for voting
        knowledgeHierarchy.registerAgent(
            agent1,
            75,
            KnowledgeHierarchyDAIO.Domain.Blockchain
        );

        // Grant proposer role
        knowledgeHierarchy.grantRole(knowledgeHierarchy.PROPOSER_ROLE(), deployer);

        // Create proposal
        address[] memory targets = new address[](1);
        uint256[] memory values = new uint256[](1);
        bytes[] memory calldatas = new bytes[](1);

        targets[0] = address(constitution);
        values[0] = 0;
        calldatas[0] = abi.encodeWithSignature("pauseSystem(string)", "Test");

        uint256 proposalId = knowledgeHierarchy.createProposal(
            "Test proposal for governance",
            targets,
            values,
            calldatas
        );

        // Agent votes
        vm.prank(agent1);
        knowledgeHierarchy.agentVote(proposalId, true);

        // Check vote count
        (,,,uint256 aiVotes) = knowledgeHierarchy.getVoteCounts(proposalId);
        assertEq(aiVotes, 75); // Agent's knowledge level
    }

    function test_TreasuryOperations() public {
        // Deposit ETH
        vm.deal(voter1, 100 ether);
        vm.prank(voter1);
        treasury.deposit{value: 10 ether}();

        // Check tithe collected (15%)
        (uint256 deposited,, uint256 tithe,) = treasury.getStats();
        assertEq(deposited, 10 ether);
        assertEq(tithe, 1.5 ether);

        // Mark ETH as diversified to meet 15% requirement (need at least 1.5 ETH)
        treasury.grantRole(treasury.TREASURER_ROLE(), deployer);
        treasury.markAsDiversified(address(0), 2 ether); // 20% diversified

        // Distribute reward
        treasury.distributeReward(agent1, 1 ether, address(0), "Performance bonus");

        // Verify distribution
        (,uint256 distributed,,) = treasury.getStats();
        assertEq(distributed, 1 ether);
    }

    function test_ConstitutionalChecks() public {
        // Update treasury state
        constitution.grantRole(constitution.GOVERNANCE_ROLE(), deployer);
        constitution.updateTreasuryState(100 ether, 20 ether);

        // Check diversification compliance
        assertTrue(constitution.checkDiversificationLimit());

        // Validate tithe
        assertTrue(constitution.validateTithe(100 ether, 15 ether));
        assertFalse(constitution.validateTithe(100 ether, 10 ether));
    }

    function test_ChairmanVeto() public {
        // Chairman can pause the system
        vm.prank(chairman);
        constitution.pauseSystem("Emergency situation");

        assertTrue(constitution.paused());

        // Chairman can unpause
        vm.prank(chairman);
        constitution.unpauseSystem();

        assertFalse(constitution.paused());
    }

    function test_THOTIntegration() public {
        // Create agent with THOT
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "THOTAgent",
            "THOT-enabled agent",
            '{"thot_enabled": true}',
            "ipfs://thot-agent",
            false
        );

        // Attach THOT tensors
        idnft.attachTHOT(tokenId, keccak256("thot8d_data"), 8, 4);
        idnft.attachTHOT(tokenId, keccak256("thot512_data"), 64, 8);
        idnft.attachTHOT(tokenId, keccak256("thot768_data"), 128, 16);

        // Attach model dataset
        idnft.attachModelDataset(tokenId, keccak256("model_weights"), "transformer-768");

        // Verify attachments
        IDNFT.THOTAttachment[] memory thots = idnft.getTHOTAttachments(tokenId);
        assertEq(thots.length, 3);

        IDNFT.ModelDataset memory model = idnft.getModelDataset(tokenId);
        assertTrue(model.verified);
    }

    function test_SoulboundCredentials() public {
        // Create soulbound identity
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "PermanentAgent",
            "Permanent credentials",
            '{"permanent": true}',
            "ipfs://permanent",
            true
        );

        // Verify soulbound
        assertTrue(idnft.isSoulbound(tokenId));

        // Attempt transfer (should fail)
        vm.prank(agent1);
        vm.expectRevert("Transfer blocked: soulbound identity");
        idnft.transferFrom(agent1, agent2, tokenId);
    }

    function test_MultiSigTreasury() public {
        // Add additional signer and treasurer
        treasury.grantRole(treasury.SIGNER_ROLE(), voter1);
        treasury.grantRole(treasury.SIGNER_ROLE(), voter2);
        treasury.grantRole(treasury.TREASURER_ROLE(), deployer);

        // Fund treasury
        vm.deal(deployer, 100 ether);
        treasury.deposit{value: 50 ether}();

        // Mark ETH as diversified to meet 15% requirement (need at least 7.5 ETH)
        treasury.markAsDiversified(address(0), 10 ether); // 20% diversified

        // Submit transaction (auto-confirms for submitter)
        uint256 txId = treasury.submitTransaction(
            agent1,
            5 ether,
            address(0),
            "",
            "Agent reward"
        );

        // Need 2 more confirmations (total 3)
        vm.prank(voter1);
        treasury.confirmTransaction(txId);

        vm.prank(voter2);
        treasury.confirmTransaction(txId);

        // Transaction should be executed
        Treasury.Transaction memory txn = treasury.getTransaction(txId);
        assertEq(uint256(txn.status), uint256(Treasury.TransactionStatus.Executed));
    }
}
