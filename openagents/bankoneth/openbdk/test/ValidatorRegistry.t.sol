// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {OpenBDKValidatorRegistry} from "../src/governance/OpenBDKValidatorRegistry.sol";
import {IOpenBDKValidatorRegistry} from "../src/interfaces/IOpenBDKValidatorRegistry.sol";

/**
 * @title MockStakingToken
 * @notice Simple ERC-20 for testing the ValidatorRegistry
 */
contract MockStakingToken {
    string public name = "THRUST";
    string public symbol = "THRUST";
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (allowance[from][msg.sender] != type(uint256).max) {
            allowance[from][msg.sender] -= amount;
        }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

/**
 * @title ValidatorRegistryTest
 * @notice Tests the openBDK Relayer-Validator topology: 1 Relayer + 3 Validators
 */
contract ValidatorRegistryTest is Test {
    OpenBDKValidatorRegistry registry;
    MockStakingToken token;

    address admin     = makeAddr("admin");
    address relayer   = makeAddr("relayer");
    address consensus = makeAddr("consensus");

    address validator1 = makeAddr("validator1");
    address validator2 = makeAddr("validator2");
    address validator3 = makeAddr("validator3");
    address validator4 = makeAddr("validator4"); // The "4th" who can't fit in v1

    address attacker = makeAddr("attacker");

    uint256 constant MIN_STAKE = 1_000e18;
    uint256 constant UNBONDING_BLOCKS = 100;

    function setUp() public {
        token = new MockStakingToken();

        OpenBDKValidatorRegistry impl = new OpenBDKValidatorRegistry();
        ERC1967Proxy proxy = new ERC1967Proxy(
            address(impl),
            abi.encodeCall(
                OpenBDKValidatorRegistry.initialize,
                (admin, address(token), relayer, MIN_STAKE, UNBONDING_BLOCKS)
            )
        );
        registry = OpenBDKValidatorRegistry(address(proxy));

        // Grant CONSENSUS_ROLE to the consensus address.
        // Cache the role first: an inline registry.CONSENSUS_ROLE() view call would
        // consume the vm.prank, leaving grantRole to run as the test contract.
        bytes32 consensusRole = registry.CONSENSUS_ROLE();
        vm.prank(admin);
        registry.grantRole(consensusRole, consensus);

        // Fund all validators with stake tokens
        token.mint(validator1, 10_000e18);
        token.mint(validator2, 10_000e18);
        token.mint(validator3, 10_000e18);
        token.mint(validator4, 10_000e18);
        token.mint(consensus, 100_000e18); // For reward distribution
    }

    // ============ Registration ============

    function test_RegisterValidator() public {
        vm.startPrank(validator1);
        token.approve(address(registry), MIN_STAKE);
        registry.registerValidator();
        vm.stopPrank();

        IOpenBDKValidatorRegistry.Validator memory v = registry.getValidator(validator1);
        assertEq(uint8(v.status), uint8(IOpenBDKValidatorRegistry.ValidatorStatus.Candidate));
        assertEq(v.stakedAmount, MIN_STAKE);
        assertEq(v.fidesScore, 100);
    }

    function test_RevertWhen_RegisterTwice() public {
        _registerValidator(validator1);

        vm.startPrank(validator1);
        token.approve(address(registry), MIN_STAKE);
        vm.expectRevert();
        registry.registerValidator();
        vm.stopPrank();
    }

    function test_RevertWhen_InsufficientStake() public {
        address poorValidator = makeAddr("poor");
        token.mint(poorValidator, MIN_STAKE - 1);

        vm.startPrank(poorValidator);
        token.approve(address(registry), MIN_STAKE);
        vm.expectRevert();
        registry.registerValidator();
        vm.stopPrank();
    }

    // ============ Activation ============

    function test_ActivateValidator() public {
        _registerValidator(validator1);

        vm.prank(relayer);
        registry.activateValidator(validator1);

        assertTrue(registry.isActiveValidator(validator1));
        assertEq(registry.activeValidatorCount(), 1);
    }

    function test_FullV1Topology_OneRelayerThreeValidators() public {
        // The complete openBDK v1 setup: 1 Relayer + 3 Validators
        _registerValidator(validator1);
        _registerValidator(validator2);
        _registerValidator(validator3);

        vm.startPrank(relayer);
        registry.activateValidator(validator1);
        registry.activateValidator(validator2);
        registry.activateValidator(validator3);
        vm.stopPrank();

        // Verify the v1 topology
        assertEq(registry.activeValidatorCount(), 3, "Should have exactly 3 validators");
        assertEq(registry.currentRelayer(), relayer, "Relayer should be set");

        address[] memory active = registry.getActiveValidatorSet();
        assertEq(active.length, 3);

        // Verify 2/3 consensus math: ceil(2 * 3 / 3) = 2 votes required
        // f = n/3 = 1 Byzantine fault tolerated
        console2.log("openBDK v1 topology verified:");
        console2.log("  Relayer:", registry.currentRelayer());
        console2.log("  Active validators:", registry.activeValidatorCount());
        console2.log("  Required votes for consensus: 2/3 = 2");
        console2.log("  Byzantine fault tolerance: 1");
    }

    function test_RevertWhen_FourthValidator_ExceedsV1Cap() public {
        // v1 caps at 3 validators
        _registerAndActivate(validator1);
        _registerAndActivate(validator2);
        _registerAndActivate(validator3);

        _registerValidator(validator4);
        vm.prank(relayer);
        vm.expectRevert();
        registry.activateValidator(validator4);
    }

    function test_RevertWhen_NonRelayerActivates() public {
        _registerValidator(validator1);

        vm.prank(attacker);
        vm.expectRevert();
        registry.activateValidator(validator1);
    }

    // ============ Rewards ============

    function test_DistributeRewards() public {
        _registerAndActivate(validator1);
        _registerAndActivate(validator2);
        _registerAndActivate(validator3);

        // Fund the registry to pay rewards
        vm.prank(consensus);
        token.transfer(address(registry), 1000e18);

        address[] memory approvers = new address[](2);
        approvers[0] = validator1;
        approvers[1] = validator2;

        vm.prank(consensus);
        registry.distributeRewards(approvers, 1000e18);

        // Each validator should get 500e18
        assertEq(registry.getValidator(validator1).rewardsAccumulated, 500e18);
        assertEq(registry.getValidator(validator2).rewardsAccumulated, 500e18);
        assertEq(registry.getValidator(validator3).rewardsAccumulated, 0); // Did not approve

        // Fides score increased for participating validators
        assertEq(registry.getValidator(validator1).fidesScore, 101);
        assertEq(registry.getValidator(validator2).fidesScore, 101);
        assertEq(registry.getValidator(validator3).fidesScore, 100);
    }

    function test_ClaimRewards() public {
        test_DistributeRewards();

        uint256 balBefore = token.balanceOf(validator1);
        vm.prank(validator1);
        registry.claimRewards();

        assertEq(token.balanceOf(validator1) - balBefore, 500e18);
        assertEq(registry.getValidator(validator1).rewardsAccumulated, 0);
    }

    // ============ Slashing ============

    function test_SlashValidator() public {
        _registerAndActivate(validator1);

        uint256 stakeBefore = registry.getValidator(validator1).stakedAmount;

        vm.prank(consensus);
        registry.slash(validator1, 100e18, "Equivocation detected");

        // Partial-slash accounting: stake debited, fides docked 10.
        assertEq(registry.getValidator(validator1).stakedAmount, stakeBefore - 100e18);
        assertEq(registry.getValidator(validator1).fidesScore, 90); // -10
        // registerValidator() stakes EXACTLY minimumStake, so any slash drops below
        // the minimum and the contract deactivates (status -> Slashed). Over-minimum
        // staking — to let a minor slash leave a validator active — is a v2 "sane
        // deployment" enhancement (variable-amount staking).
        assertFalse(registry.isActiveValidator(validator1));
        assertEq(
            uint8(registry.getValidator(validator1).status),
            uint8(IOpenBDKValidatorRegistry.ValidatorStatus.Slashed)
        );
    }

    function test_SlashBelowMinimum_Deactivates() public {
        _registerAndActivate(validator1);

        // Slash everything below minimum
        vm.prank(consensus);
        registry.slash(validator1, MIN_STAKE / 2, "Major violation");

        assertFalse(registry.isActiveValidator(validator1));
        assertEq(
            uint8(registry.getValidator(validator1).status),
            uint8(IOpenBDKValidatorRegistry.ValidatorStatus.Slashed)
        );
    }

    // ============ Relayer rotation ============

    function test_RotateRelayer() public {
        _registerAndActivate(validator1);
        _registerAndActivate(validator2);

        bytes32 govRole = registry.GOVERNANCE_ROLE();
        vm.prank(admin);
        registry.grantRole(govRole, admin);

        vm.prank(admin);
        registry.rotateRelayer(validator1);

        assertEq(registry.currentRelayer(), validator1);
    }

    function test_RevertWhen_RotateToNonValidator() public {
        bytes32 govRole = registry.GOVERNANCE_ROLE();
        vm.prank(admin);
        registry.grantRole(govRole, admin);

        vm.prank(admin);
        vm.expectRevert();
        registry.rotateRelayer(attacker);
    }

    // ============ Exit and unbonding ============

    function test_ExitValidator() public {
        _registerAndActivate(validator1);

        vm.prank(validator1);
        registry.exitValidator();

        assertEq(
            uint8(registry.getValidator(validator1).status),
            uint8(IOpenBDKValidatorRegistry.ValidatorStatus.Exited)
        );
        assertFalse(registry.isActiveValidator(validator1));
    }

    function test_WithdrawStakeAfterUnbonding() public {
        _registerAndActivate(validator1);

        vm.prank(validator1);
        registry.exitValidator();

        // Cannot withdraw immediately
        vm.expectRevert();
        vm.prank(validator1);
        registry.withdrawStake();

        // Advance past unbonding period
        vm.roll(block.number + UNBONDING_BLOCKS + 1);

        uint256 balBefore = token.balanceOf(validator1);
        vm.prank(validator1);
        registry.withdrawStake();

        assertEq(token.balanceOf(validator1) - balBefore, MIN_STAKE);
    }

    // ============ Helpers ============

    function _registerValidator(address v) internal {
        vm.startPrank(v);
        token.approve(address(registry), MIN_STAKE);
        registry.registerValidator();
        vm.stopPrank();
    }

    function _registerAndActivate(address v) internal {
        _registerValidator(v);
        vm.prank(relayer);
        registry.activateValidator(v);
    }
}
