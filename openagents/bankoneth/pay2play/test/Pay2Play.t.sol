// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {BankonServiceRegistry} from "../src/BankonServiceRegistry.sol";
import {BankonEntitlement}     from "../src/BankonEntitlement.sol";
import {BANKONPaymentRouter}   from "../src/BANKONPaymentRouter.sol";
import {IBankonServiceRegistry} from "../src/interfaces/IPay2Play.sol";

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USDC", "mUSDC") {}
    function mint(address to, uint256 amt) external { _mint(to, amt); }
    function decimals() public pure override returns (uint8) { return 6; }
}

contract Pay2PlayTest is Test {
    BankonServiceRegistry registry;
    BankonEntitlement     ent;
    BANKONPaymentRouter   router;
    MockUSDC              usdc;

    address admin       = address(0xA11CE);
    address beneficiary = address(0xB0B);
    address feeRecip    = address(0xFEE);
    address user        = address(0xCAFE);

    bytes32 constant SVC_NATIVE = keccak256("identity.register");
    bytes32 constant SVC_USDC   = keccak256("hosting.month");

    function setUp() public {
        vm.startPrank(admin);
        registry = new BankonServiceRegistry(admin);
        ent      = new BankonEntitlement(admin);
        router   = new BANKONPaymentRouter(admin, registry, ent, feeRecip);
        ent.grantRole(ent.GRANTER_ROLE(), address(router));
        usdc = new MockUSDC();

        // native, permanent, tier 1
        registry.setService(SVC_NATIVE, IBankonServiceRegistry.Service({
            beneficiary: beneficiary, asset: address(0), price: 1 ether,
            period: 0, tier: 1, active: true, name: "identity.register"
        }));
        // erc20, 30-day, tier 2
        registry.setService(SVC_USDC, IBankonServiceRegistry.Service({
            beneficiary: beneficiary, asset: address(usdc), price: 10e6,
            period: 30 days, tier: 2, active: true, name: "hosting.month"
        }));
        vm.stopPrank();
    }

    function test_PlayNative_splitsFeeAndGrantsPermanent() public {
        vm.deal(user, 1 ether);
        vm.prank(user);
        router.play{value: 1 ether}(SVC_NATIVE);

        // 2.5% fee default
        assertEq(feeRecip.balance, 0.025 ether, "fee");
        assertEq(beneficiary.balance, 0.975 ether, "net");
        assertTrue(ent.hasAccess(user, SVC_NATIVE), "access");
        assertEq(ent.expiryOf(user, SVC_NATIVE), type(uint64).max, "permanent");
        assertEq(ent.tierOf(user), 1, "tier");
    }

    function test_PlayERC20_timeBoxed() public {
        usdc.mint(user, 10e6);
        vm.startPrank(user);
        usdc.approve(address(router), 10e6);
        router.play(SVC_USDC);
        vm.stopPrank();

        assertEq(usdc.balanceOf(feeRecip), 0.25e6, "fee 2.5%");
        assertEq(usdc.balanceOf(beneficiary), 9.75e6, "net");
        assertTrue(ent.hasAccess(user, SVC_USDC), "access now");
        assertEq(ent.tierOf(user), 2, "tier");

        vm.warp(block.timestamp + 31 days);
        assertFalse(ent.hasAccess(user, SVC_USDC), "expired");
    }

    function test_PlayWithSig_bindsToSigner() public {
        (address signer, uint256 pk) = makeAddrAndKey("signer");
        address sponsor = address(0x5BADD);
        vm.deal(sponsor, 1 ether);

        bytes32 typehash = keccak256("Play(bytes32 serviceId,address user,uint256 nonce)");
        bytes32 structHash = keccak256(abi.encode(typehash, SVC_NATIVE, signer, uint256(0)));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", router.domainSeparator(), structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);

        vm.prank(sponsor);
        router.playWithSig{value: 1 ether}(SVC_NATIVE, signer, abi.encodePacked(r, s, v));

        // entitlement binds to the SIGNER (identity), not the sponsor (payer)
        assertTrue(ent.hasAccess(signer, SVC_NATIVE), "signer has access");
        assertFalse(ent.hasAccess(sponsor, SVC_NATIVE), "sponsor does not");
        assertEq(beneficiary.balance, 0.975 ether, "net paid by sponsor");
    }

    function test_FeeCappedAndConfigurable() public {
        vm.prank(admin);
        vm.expectRevert(BANKONPaymentRouter.FeeTooHigh.selector);
        router.setFee(1001, feeRecip);

        vm.prank(admin);
        router.setFee(500, feeRecip); // 5%
        assertEq(router.feeBps(), 500);
    }

    function test_InactiveServiceReverts() public {
        vm.prank(admin);
        registry.setActive(SVC_NATIVE, false);
        vm.deal(user, 1 ether);
        vm.prank(user);
        vm.expectRevert(abi.encodeWithSelector(BANKONPaymentRouter.ServiceInactive.selector, SVC_NATIVE));
        router.play{value: 1 ether}(SVC_NATIVE);
    }
}
