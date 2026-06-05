// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {OpenBDKL1Escrow} from "../src/bridge/OpenBDKL1Escrow.sol";
import {OpenBDKL2MinterBurner, IMintableBurnableERC20} from "../src/bridge/OpenBDKL2MinterBurner.sol";
import {OpenBDKNativeConverter} from "../src/bridge/OpenBDKNativeConverter.sol";
import {OpenBDKL2Token} from "../src/token/OpenBDKL2Token.sol";
import {IPolygonZkEVMBridgeV2} from "../src/interfaces/IPolygonZkEVMBridgeV2.sol";

/**
 * @title MockUnifiedBridge
 * @notice Minimal mock of PolygonZkEVMBridgeV2 for unit testing the openBDK contracts
 * @dev Records bridgeMessage calls and allows direct invocation of onMessageReceived
 *      to simulate cross-chain message delivery
 */
contract MockUnifiedBridge {
    event BridgeMessageCalled(
        uint32 destinationNetwork,
        address destinationAddress,
        bool forceUpdateGER,
        bytes metadata
    );

    event BridgeAssetCalled(
        uint32 destinationNetwork,
        address destinationAddress,
        uint256 amount,
        address token
    );

    function bridgeMessage(
        uint32 destinationNetwork,
        address destinationAddress,
        bool forceUpdateGER,
        bytes calldata metadata
    ) external payable {
        emit BridgeMessageCalled(destinationNetwork, destinationAddress, forceUpdateGER, metadata);
    }

    function bridgeAsset(
        uint32 destinationNetwork,
        address destinationAddress,
        uint256 amount,
        address token,
        bool,
        bytes calldata
    ) external payable {
        emit BridgeAssetCalled(destinationNetwork, destinationAddress, amount, token);
        // Pull tokens from caller to simulate bridge lock behavior
        if (token != address(0)) {
            IERC20(token).transferFrom(msg.sender, address(this), amount);
        }
    }

    /// @notice Simulate the bridge calling onMessageReceived on a destination contract
    function simulateClaim(
        address destinationContract,
        address originAddress,
        uint32 originNetwork,
        bytes calldata data
    ) external {
        (bool success,) = destinationContract.call(
            abi.encodeWithSignature(
                "onMessageReceived(address,uint32,bytes)",
                originAddress,
                originNetwork,
                data
            )
        );
        require(success, "Mock claim failed");
    }
}

/**
 * @title MockL1Token
 * @notice Simple ERC-20 for L1 USDC simulation
 */
contract MockL1Token {
    string public name = "USD Coin";
    string public symbol = "USDC";
    uint8 public constant decimals = 6;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Approval(address indexed owner, address indexed spender, uint256 amount);

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (allowance[from][msg.sender] != type(uint256).max) {
            allowance[from][msg.sender] -= amount;
        }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }
}

/**
 * @title BridgeIntegrationTest
 * @notice End-to-end tests for the openBDK L1Escrow + L2MinterBurner + NativeConverter pattern
 * @dev Tests the full deposit and withdrawal flows using mock bridge
 */
contract BridgeIntegrationTest is Test {
    OpenBDKL1Escrow l1Escrow;
    OpenBDKL2MinterBurner l2MinterBurner;
    OpenBDKL2Token l2Token;
    OpenBDKNativeConverter nativeConverter;
    MockUnifiedBridge bridge;
    MockL1Token l1Token;

    address admin = makeAddr("admin");
    address escrowManager = makeAddr("escrowManager");
    address user = makeAddr("user");
    address attacker = makeAddr("attacker");

    uint32 constant L1_NETWORK = 0;
    uint32 constant L2_NETWORK = 7;

    function setUp() public {
        bridge = new MockUnifiedBridge();
        l1Token = new MockL1Token();

        // Deploy L2 Token
        OpenBDKL2Token tokenImpl = new OpenBDKL2Token();
        ERC1967Proxy tokenProxy = new ERC1967Proxy(
            address(tokenImpl),
            abi.encodeCall(OpenBDKL2Token.initialize, ("USDC openBDK", "USDC.b", 6, admin))
        );
        l2Token = OpenBDKL2Token(address(tokenProxy));

        // Deploy L1 Escrow (uninitialized)
        OpenBDKL1Escrow escrowImpl = new OpenBDKL1Escrow();
        ERC1967Proxy escrowProxy = new ERC1967Proxy(address(escrowImpl), "");
        l1Escrow = OpenBDKL1Escrow(address(escrowProxy));

        // Deploy L2 MinterBurner
        OpenBDKL2MinterBurner mbImpl = new OpenBDKL2MinterBurner();
        ERC1967Proxy mbProxy = new ERC1967Proxy(
            address(mbImpl),
            abi.encodeCall(
                OpenBDKL2MinterBurner.initialize,
                (admin, address(bridge), address(l1Escrow), L1_NETWORK, address(l2Token))
            )
        );
        l2MinterBurner = OpenBDKL2MinterBurner(address(mbProxy));

        // Initialize L1 Escrow with L2 MinterBurner address
        l1Escrow.initialize(
            admin,
            escrowManager,
            address(bridge),
            address(l2MinterBurner),
            L2_NETWORK,
            address(l1Token),
            address(l2Token)
        );

        // Grant MINTER and BURNER roles on L2 Token to MinterBurner
        vm.startPrank(admin);
        l2Token.grantRole(l2Token.MINTER_ROLE(), address(l2MinterBurner));
        l2Token.grantRole(l2Token.BURNER_ROLE(), address(l2MinterBurner));
        vm.stopPrank();

        // Fund user with L1 USDC
        l1Token.mint(user, 10_000e6);
    }

    // ============ Deposit flow: L1 → L2 ============

    function test_DepositFlow_L1ToL2() public {
        uint256 amount = 1000e6;

        // 1. User approves L1Escrow to spend USDC
        vm.prank(user);
        l1Token.approve(address(l1Escrow), amount);

        // 2. User calls bridgeToken on L1Escrow
        vm.prank(user);
        l1Escrow.bridgeToken(user, amount, true);

        // 3. Verify L1 USDC is held in escrow
        assertEq(l1Token.balanceOf(address(l1Escrow)), amount, "L1 escrow balance");
        assertEq(l1Token.balanceOf(user), 9_000e6, "User L1 balance");

        // 4. Simulate bridge delivering message to L2MinterBurner
        bytes memory data = abi.encode(user, amount);
        bridge.simulateClaim(
            address(l2MinterBurner),
            address(l1Escrow),
            L1_NETWORK,
            data
        );

        // 5. Verify L2 token minted to user
        assertEq(l2Token.balanceOf(user), amount, "User L2 balance");
        assertEq(l2Token.totalSupply(), amount, "L2 total supply");
    }

    // ============ Withdraw flow: L2 → L1 ============

    function test_WithdrawFlow_L2ToL1() public {
        // Setup: user has L2 tokens (simulate prior deposit)
        test_DepositFlow_L1ToL2();
        uint256 amount = 500e6;

        // 1. User approves L2MinterBurner (no approval needed for burn — L2Token must check)
        // For L2Token burn, the burner role allows direct burn from any account
        // 2. User calls bridgeToken on L2MinterBurner
        vm.prank(user);
        l2MinterBurner.bridgeToken(user, amount, true);

        // 3. Verify L2 tokens burned
        assertEq(l2Token.balanceOf(user), 1000e6 - amount, "L2 balance after burn");

        // 4. Simulate bridge delivering message to L1Escrow
        bytes memory data = abi.encode(user, amount);
        bridge.simulateClaim(
            address(l1Escrow),
            address(l2MinterBurner),
            L2_NETWORK,
            data
        );

        // 5. Verify L1 USDC released to user
        assertEq(l1Token.balanceOf(user), 9_000e6 + amount, "User L1 balance restored");
        assertEq(l1Token.balanceOf(address(l1Escrow)), 1000e6 - amount, "Escrow balance reduced");
    }

    // ============ Critical security tests ============

    function test_RevertWhen_UnauthorizedBridgeCaller() public {
        // Attacker tries to call onMessageReceived directly (bypassing bridge)
        bytes memory data = abi.encode(attacker, 1_000_000e6);

        vm.expectRevert();
        vm.prank(attacker);
        l1Escrow.onMessageReceived(address(l2MinterBurner), L2_NETWORK, data);
    }

    function test_RevertWhen_WrongOriginAddress() public {
        // Bridge sends message but with wrong origin (not the L2MinterBurner)
        bytes memory data = abi.encode(attacker, 1_000_000e6);

        vm.expectRevert();
        bridge.simulateClaim(
            address(l1Escrow),
            attacker,            // WRONG: not the configured counterpart
            L2_NETWORK,
            data
        );
    }

    function test_RevertWhen_WrongOriginNetwork() public {
        // Bridge sends message from wrong origin network
        bytes memory data = abi.encode(attacker, 1_000_000e6);

        vm.expectRevert();
        bridge.simulateClaim(
            address(l1Escrow),
            address(l2MinterBurner),
            999,                 // WRONG: not the configured counterpart network
            data
        );
    }

    function test_RevertWhen_BridgeZeroAmount() public {
        vm.prank(user);
        l1Token.approve(address(l1Escrow), 1000e6);

        vm.expectRevert();
        vm.prank(user);
        l1Escrow.bridgeToken(user, 0, true);
    }

    function test_RevertWhen_BridgeWithMsgValue() public {
        vm.prank(user);
        l1Token.approve(address(l1Escrow), 1000e6);

        vm.deal(user, 1 ether);
        vm.expectRevert();
        vm.prank(user);
        l1Escrow.bridgeToken{value: 1 ether}(user, 1000e6, true);
    }

    // ============ Pause functionality ============

    function test_PauseAndUnpause() public {
        vm.prank(admin);
        l1Escrow.pause();

        vm.prank(user);
        l1Token.approve(address(l1Escrow), 1000e6);

        vm.expectRevert();
        vm.prank(user);
        l1Escrow.bridgeToken(user, 1000e6, true);

        vm.prank(admin);
        l1Escrow.unpause();

        vm.prank(user);
        l1Escrow.bridgeToken(user, 1000e6, true);
        assertEq(l1Token.balanceOf(address(l1Escrow)), 1000e6);
    }

    // ============ Escrow manager ============

    function test_EscrowManagerWithdraw() public {
        test_DepositFlow_L1ToL2();
        uint256 escrowBalance = l1Token.balanceOf(address(l1Escrow));

        address recipient = makeAddr("yieldStrategy");
        vm.prank(escrowManager);
        l1Escrow.withdraw(recipient, escrowBalance);

        assertEq(l1Token.balanceOf(recipient), escrowBalance);
        assertEq(l1Token.balanceOf(address(l1Escrow)), 0);
    }

    function test_RevertWhen_NonManagerWithdraw() public {
        test_DepositFlow_L1ToL2();
        vm.expectRevert();
        vm.prank(attacker);
        l1Escrow.withdraw(attacker, 1000e6);
    }

    // ============ Fuzz tests ============

    function testFuzz_DepositAmount(uint256 amount) public {
        amount = bound(amount, 1, 1_000_000e6);
        l1Token.mint(user, amount);

        vm.startPrank(user);
        l1Token.approve(address(l1Escrow), amount);
        l1Escrow.bridgeToken(user, amount, true);
        vm.stopPrank();

        assertGe(l1Token.balanceOf(address(l1Escrow)), amount);
    }

    function testFuzz_DepositToArbitraryRecipient(address recipient, uint256 amount) public {
        vm.assume(recipient != address(0));
        amount = bound(amount, 1, 100_000e6);

        l1Token.mint(user, amount);
        vm.startPrank(user);
        l1Token.approve(address(l1Escrow), amount);
        l1Escrow.bridgeToken(recipient, amount, true);
        vm.stopPrank();

        // Simulate bridge delivery
        bytes memory data = abi.encode(recipient, amount);
        bridge.simulateClaim(
            address(l2MinterBurner),
            address(l1Escrow),
            L1_NETWORK,
            data
        );

        assertEq(l2Token.balanceOf(recipient), amount);
    }
}

/**
 * @title BridgeForkTest
 * @notice Fork tests against real Ethereum mainnet Unified Bridge
 * @dev Run with: forge test --fork-url $ETHEREUM_RPC_URL --match-contract BridgeForkTest -vvv
 */
contract BridgeForkTest is Test {
    address constant UNIFIED_BRIDGE = 0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe;
    address constant L1_USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;

    function setUp() public {
        try vm.envString("ETHEREUM_RPC_URL") returns (string memory rpc) {
            vm.createSelectFork(rpc);
        } catch {
            vm.skip(true);
        }
    }

    function test_UnifiedBridgeExists() public view {
        assertGt(UNIFIED_BRIDGE.code.length, 0, "Unified Bridge missing on mainnet");
    }

    function test_BridgeNetworkID() public view {
        uint32 networkId = IPolygonZkEVMBridgeV2(UNIFIED_BRIDGE).networkID();
        assertEq(networkId, 0, "Mainnet network ID should be 0");
    }

    function test_BridgeDepositCount() public view {
        uint256 count = IPolygonZkEVMBridgeV2(UNIFIED_BRIDGE).depositCount();
        assertGt(count, 0, "Bridge should have processed deposits");
        console2.log("Total deposits processed by mainnet Unified Bridge:", count);
    }
}
