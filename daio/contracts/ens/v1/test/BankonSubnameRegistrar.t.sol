// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";

import {BankonSubnameRegistrar, AgentMetadata} from "../BankonSubnameRegistrar.sol";
import {BankonPriceOracle}    from "../BankonPriceOracle.sol";
import {BankonReputationGate} from "../BankonReputationGate.sol";
import {BankonPaymentRouter}  from "../BankonPaymentRouter.sol";

import {MockNameWrapper}       from "./mocks/MockNameWrapper.sol";
import {MockResolver}          from "./mocks/MockResolver.sol";
import {MockIdentityRegistry}  from "./mocks/MockIdentityRegistry.sol";

import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {Pausable}       from "@openzeppelin/contracts/utils/Pausable.sol";

/// @notice Foundry suite for the BANKON v1 ENS subname registrar.
///         Covers: paid registration via EIP-712 voucher, free reputation-gated
///         path, replay protection, label validation, expiry capping, ERC-8004
///         bundled mint, fuse profile, renewal, pause, role + admin, and event
///         emission. Plus fuzz over arbitrary labels + arbitrary owners.
contract BankonSubnameRegistrar_Test is Test {
    BankonSubnameRegistrar internal reg;
    BankonPriceOracle      internal oracle;
    BankonReputationGate   internal gate;
    BankonPaymentRouter    internal router;
    MockNameWrapper        internal wrapper;
    MockResolver           internal resolver;
    MockIdentityRegistry   internal idreg;

    address internal admin     = address(0xA11CE);
    address internal alice     = address(0xA1);
    address internal bob       = address(0xB1);
    address internal carol     = address(0xC1);
    uint256 internal gatewayPk = 0xD0;
    address internal gateway;

    bytes32 internal parentNode;

    /// EIP-712 domain helpers
    bytes32 internal DOMAIN_SEPARATOR;
    bytes32 internal constant REGISTRATION_TYPEHASH =
        keccak256("Registration(string label,address owner,uint64 expiry,bytes32 paymentReceiptHash,uint256 deadline)");
    bytes32 internal constant RENEWAL_TYPEHASH =
        keccak256("Renewal(string label,uint64 newExpiry,bytes32 paymentReceiptHash,uint256 deadline)");

    function setUp() public {
        gateway = vm.addr(gatewayPk);
        vm.warp(1_700_000_000);

        wrapper  = new MockNameWrapper();
        resolver = new MockResolver();
        idreg    = new MockIdentityRegistry();
        oracle   = new BankonPriceOracle(admin);
        gate     = new BankonReputationGate(admin);
        router   = new BankonPaymentRouter(admin);

        // namehash("bankon.eth") — synthetic for tests; real one is computed off-chain.
        parentNode = keccak256(abi.encodePacked(
            keccak256(abi.encodePacked(bytes32(0), keccak256("eth"))),
            keccak256("bankon")
        ));

        // Pre-set parent expiry far in the future so the test isn't capped.
        wrapper.adminSetParent(parentNode, admin, 0, uint64(block.timestamp + 365 days * 10));

        reg = new BankonSubnameRegistrar(
            address(wrapper),
            address(resolver),
            parentNode,
            address(router),
            address(oracle),
            address(gate),
            address(idreg),
            admin
        );

        // Cache the deployed contract's domain separator for voucher signing.
        DOMAIN_SEPARATOR = _domainSeparator(address(reg));

        bytes32 gwRole = reg.GATEWAY_SIGNER_ROLE();
        bytes32 govRole = gate.GOV_ROLE();
        bytes32 routerRegRole = router.REGISTRAR_ROLE();
        vm.startPrank(admin);
        reg.grantRole(gwRole, gateway);
        // Allow the gate's admin to set scores from this test contract directly
        gate.grantRole(govRole, address(this));
        // Allow the registrar to record receipts on the router
        router.grantRole(routerRegRole, address(reg));
        vm.stopPrank();
    }

    /* ────────── HELPERS ────────── */

    function _domainSeparator(address contractAddr) internal view returns (bytes32) {
        return keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("BankonSubnameRegistrar")),
            keccak256(bytes("1")),
            block.chainid,
            contractAddr
        ));
    }

    function _signRegistration(
        string memory label,
        address owner,
        uint64 expiry,
        bytes32 paymentReceiptHash,
        uint256 deadline,
        uint256 signerPk
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(
            REGISTRATION_TYPEHASH,
            keccak256(bytes(label)),
            owner,
            expiry,
            paymentReceiptHash,
            deadline
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _signRenewal(
        string memory label,
        uint64 newExpiry,
        bytes32 paymentReceiptHash,
        uint256 deadline,
        uint256 signerPk
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(
            RENEWAL_TYPEHASH,
            keccak256(bytes(label)),
            newExpiry,
            paymentReceiptHash,
            deadline
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(signerPk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _meta() internal pure returns (AgentMetadata memory) {
        return AgentMetadata({
            agentURI:      "ipfs://Qm/agent.json",
            mindxEndpoint: "https://mindx.pythai.net/agent/test",
            x402Endpoint:  "https://x402.bankon.eth/agent/test",
            algoIDNftDID:  "did:algo:Z123",
            contenthash:   hex"e3010170",
            baseAddress:   address(0xBA5E),
            algoAddr:      hex"01020304"
        });
    }

    function _node(string memory label) internal view returns (bytes32) {
        return keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Construction                                                     */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Constructor_setsRolesAndImmutables() public view {
        assertEq(address(reg.nameWrapper()),     address(wrapper));
        assertEq(address(reg.defaultResolver()), address(resolver));
        assertEq(address(reg.paymentRouter()),   address(router));
        assertEq(address(reg.priceOracle()),     address(oracle));
        assertEq(address(reg.reputationGate()),  address(gate));
        assertEq(reg.parentNode(),               parentNode);
        assertTrue(reg.hasRole(reg.DEFAULT_ADMIN_ROLE(), admin));
        assertTrue(reg.hasRole(reg.BANKON_OPS_ROLE(),    admin));
        assertTrue(reg.hasRole(reg.BONAFIDE_GOV_ROLE(),  admin));
        assertTrue(reg.hasRole(reg.GATEWAY_SIGNER_ROLE(), gateway));
        assertEq(reg.DEFAULT_FUSES(), uint32(0x10000 | 0x1 | 0x4 | 0x40000));
        assertTrue(reg.erc8004BundleEnabled());
    }

    function test_Constructor_revertsOnZeroAddresses() public {
        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        new BankonSubnameRegistrar(address(0), address(resolver), parentNode, address(router),
                                   address(oracle), address(gate), address(idreg), admin);

        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        new BankonSubnameRegistrar(address(wrapper), address(0), parentNode, address(router),
                                   address(oracle), address(gate), address(idreg), admin);

        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        new BankonSubnameRegistrar(address(wrapper), address(resolver), parentNode, address(0),
                                   address(oracle), address(gate), address(idreg), admin);

        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        new BankonSubnameRegistrar(address(wrapper), address(resolver), parentNode, address(router),
                                   address(0), address(gate), address(idreg), admin);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Paid registration (voucher path)                                 */
    /* ════════════════════════════════════════════════════════════════ */

    function test_PaidRegister_happyPath_emitsAndStores() public {
        string memory label = "alice";
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("receipt-1");
        uint256 deadline = block.timestamp + 5 minutes;
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, gatewayPk);

        (bytes32 node, uint256 agentId) = reg.register(label, alice, expiry, receipt, deadline, sig, _meta());

        assertEq(node, _node(label));
        assertGt(agentId, 0);
        assertEq(reg.labelOf(node), label);
        assertEq(reg.ownerOfLabel(node), alice);
        assertTrue(reg.usedReceipts(receipt));
        // Wrapper records final transfer with locked fuses to alice.
        (address ownerW, uint32 fuses, uint64 expW) = wrapper.getData(uint256(node));
        assertEq(ownerW, alice);
        assertEq(fuses, reg.DEFAULT_FUSES());
        assertEq(expW, expiry);
        // Resolver got the canonical setAddr for owner.
        assertEq(resolver.addrOf(node), alice);
        // ERC-8004 bundle: id minted and metadata stamped.
        assertEq(idreg.ownerOf(agentId), alice);
        assertEq(idreg.uriOf(agentId), _meta().agentURI);
    }

    function test_PaidRegister_revertsOnReplayedReceipt() public {
        string memory label = "alice";
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("receipt-replay");
        uint256 deadline = block.timestamp + 5 minutes;
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, gatewayPk);
        reg.register(label, alice, expiry, receipt, deadline, sig, _meta());

        // Different label, same receipt → replay.
        bytes memory sig2 = _signRegistration("bob", bob, expiry, receipt, deadline, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.ReceiptAlreadyUsed.selector);
        reg.register("bob", bob, expiry, receipt, deadline, sig2, _meta());
    }

    function test_PaidRegister_revertsOnWrongSigner() public {
        string memory label = "alice";
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("receipt-bad");
        uint256 deadline = block.timestamp + 5 minutes;
        // Sign with random non-gateway PK.
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, 0xDEAD);
        vm.expectRevert(BankonSubnameRegistrar.InvalidGatewaySignature.selector);
        reg.register(label, alice, expiry, receipt, deadline, sig, _meta());
    }

    function test_PaidRegister_revertsOnExpiredDeadline() public {
        string memory label = "alice";
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("receipt-expired");
        uint256 deadline = block.timestamp - 1;
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.VoucherExpired.selector);
        reg.register(label, alice, expiry, receipt, deadline, sig, _meta());
    }

    function test_PaidRegister_revertsOnEmptyLabel() public {
        bytes32 receipt = keccak256("r-empty");
        uint256 deadline = block.timestamp + 1 hours;
        bytes memory sig = _signRegistration("", alice, uint64(block.timestamp + 365 days), receipt, deadline, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.LabelEmpty.selector);
        reg.register("", alice, uint64(block.timestamp + 365 days), receipt, deadline, sig, _meta());
    }

    function test_PaidRegister_revertsOnLabelTooShort() public {
        bytes32 receipt = keccak256("r-2char");
        uint256 deadline = block.timestamp + 1 hours;
        bytes memory sig = _signRegistration("ab", alice, uint64(block.timestamp + 365 days), receipt, deadline, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.LabelTooShort.selector);
        reg.register("ab", alice, uint64(block.timestamp + 365 days), receipt, deadline, sig, _meta());
    }

    function test_PaidRegister_revertsOnZeroOwner() public {
        bytes32 receipt = keccak256("r-zero");
        uint256 deadline = block.timestamp + 1 hours;
        uint64  expiry  = uint64(block.timestamp + 365 days);
        bytes memory sig = _signRegistration("alice", address(0), expiry, receipt, deadline, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        reg.register("alice", address(0), expiry, receipt, deadline, sig, _meta());
    }

    function test_PaidRegister_capsExpiryToParent() public {
        // Set parent expiry to "now + 1 day" so the requested 1-year is capped.
        wrapper.adminSetParent(parentNode, admin, 0, uint64(block.timestamp + 1 days));

        string memory label = "alice";
        uint64 requested = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("r-cap");
        uint256 deadline = block.timestamp + 1 hours;
        bytes memory sig = _signRegistration(label, alice, requested, receipt, deadline, gatewayPk);

        reg.register(label, alice, requested, receipt, deadline, sig, _meta());

        ( , , uint64 actualExpiry ) = wrapper.getData(uint256(_node(label)));
        assertEq(actualExpiry, uint64(block.timestamp + 1 days));
    }

    function test_PaidRegister_revertsWhenAgentBanned() public {
        gate.setBanned(alice, true);
        bytes32 receipt = keccak256("r-banned");
        uint256 deadline = block.timestamp + 1 hours;
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes memory sig = _signRegistration("alice", alice, expiry, receipt, deadline, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.NotEligible.selector);
        reg.register("alice", alice, expiry, receipt, deadline, sig, _meta());
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Free registration (reputation gate)                              */
    /* ════════════════════════════════════════════════════════════════ */

    function test_FreeRegister_allowsReputableAgent() public {
        gate.setAdminScore(alice, 200);    // ≥ freeThreshold (100)
        string memory label = "longalice";  // 9 chars
        uint64 expiry = uint64(block.timestamp + 365 days);

        (bytes32 node, uint256 agentId) = reg.registerFree(label, alice, expiry, _meta());
        assertEq(node, _node(label));
        assertGt(agentId, 0);
        ( , uint32 fuses, ) = wrapper.getData(uint256(node));
        assertEq(fuses, reg.DEFAULT_FUSES());
    }

    function test_FreeRegister_revertsForUnreputableAgent() public {
        // alice has score 0 — not eligible for free.
        vm.expectRevert(BankonSubnameRegistrar.NotEligible.selector);
        reg.registerFree("longalice", alice, uint64(block.timestamp + 365 days), _meta());
    }

    function test_FreeRegister_revertsOnShortLabel() public {
        gate.setAdminScore(alice, 200);
        // 6-char label rejected — free tier is 7+.
        vm.expectRevert(BankonSubnameRegistrar.LabelTooShort.selector);
        reg.registerFree("abc123", alice, uint64(block.timestamp + 365 days), _meta());
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Renewal                                                          */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Renew_extendsExpiry() public {
        // First register
        string memory label = "alice";
        uint64 expiry  = uint64(block.timestamp + 365 days);
        bytes32 r1      = keccak256("r-init");
        uint256 dl      = block.timestamp + 5 minutes;
        bytes memory s1 = _signRegistration(label, alice, expiry, r1, dl, gatewayPk);
        reg.register(label, alice, expiry, r1, dl, s1, _meta());

        // Renew to +2 years from now
        uint64 newExp = uint64(block.timestamp + 2 * 365 days);
        bytes32 r2 = keccak256("r-renew");
        uint256 dl2 = block.timestamp + 5 minutes;
        bytes memory s2 = _signRenewal(label, newExp, r2, dl2, gatewayPk);

        reg.renew(label, newExp, r2, dl2, s2);

        ( , , uint64 finalExpiry) = wrapper.getData(uint256(_node(label)));
        assertEq(finalExpiry, newExp);
        assertTrue(reg.usedReceipts(r2));
    }

    function test_Renew_revertsOnReplayedReceipt() public {
        string memory label = "alice";
        uint64 expiry  = uint64(block.timestamp + 365 days);
        bytes32 r1      = keccak256("r-init-renew");
        uint256 dl      = block.timestamp + 5 minutes;
        bytes memory s1 = _signRegistration(label, alice, expiry, r1, dl, gatewayPk);
        reg.register(label, alice, expiry, r1, dl, s1, _meta());

        bytes32 receipt = keccak256("r-double-renew");
        uint64 newExp = uint64(block.timestamp + 2 * 365 days);
        bytes memory sig = _signRenewal(label, newExp, receipt, block.timestamp + 1 hours, gatewayPk);

        reg.renew(label, newExp, receipt, block.timestamp + 1 hours, sig);

        bytes memory sig2 = _signRenewal(label, newExp + 1 days, receipt, block.timestamp + 1 hours, gatewayPk);
        vm.expectRevert(BankonSubnameRegistrar.ReceiptAlreadyUsed.selector);
        reg.renew(label, newExp + 1 days, receipt, block.timestamp + 1 hours, sig2);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Resolver records                                                 */
    /* ════════════════════════════════════════════════════════════════ */

    function test_PaidRegister_writesAllResolverRecords() public {
        string memory label = "alice";
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("r-records");
        uint256 deadline = block.timestamp + 5 minutes;
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, gatewayPk);

        reg.register(label, alice, expiry, receipt, deadline, sig, _meta());

        bytes32 node = _node(label);
        AgentMetadata memory m = _meta();
        // setAddr(bytes32,address)
        assertEq(resolver.addrOf(node), alice);
        // text records
        assertEq(resolver.textOf(node, "url"),           m.mindxEndpoint);
        assertEq(resolver.textOf(node, "x402.endpoint"), m.x402Endpoint);
        assertEq(resolver.textOf(node, "algoid.did"),    m.algoIDNftDID);
        assertEq(resolver.textOf(node, "agent.card"),    m.agentURI);
        // contenthash
        assertEq(keccak256(resolver.contenthashOf(node)), keccak256(m.contenthash));
        // multi-chain Base address (coinType 0x80002105)
        assertEq(keccak256(resolver.addrOfChain(node, reg.COIN_TYPE_BASE())),
                 keccak256(abi.encodePacked(m.baseAddress)));
        // multi-chain Algorand address (coinType 0x8000011B)
        assertEq(keccak256(resolver.addrOfChain(node, reg.COIN_TYPE_ALGO())),
                 keccak256(m.algoAddr));
        assertEq(resolver.multicallCount(), 1);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  ERC-8004 bundle                                                  */
    /* ════════════════════════════════════════════════════════════════ */

    function test_PaidRegister_skipsErc8004WhenDisabled() public {
        vm.prank(admin);
        reg.setErc8004Bundle(false);
        string memory label = "alice";
        uint64 expiry = uint64(block.timestamp + 365 days);
        bytes32 receipt = keccak256("r-no8004");
        uint256 deadline = block.timestamp + 5 minutes;
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, gatewayPk);

        ( , uint256 agentId) = reg.register(label, alice, expiry, receipt, deadline, sig, _meta());
        assertEq(agentId, 0);
        // No mint should have happened.
        assertEq(idreg.nextId(), 1);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Pause                                                            */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Pause_blocksRegister() public {
        vm.prank(admin);
        reg.pause();
        bytes memory sig = _signRegistration("alice", alice, uint64(block.timestamp + 365 days),
                                             bytes32(uint256(1)), block.timestamp + 1 hours, gatewayPk);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        reg.register("alice", alice, uint64(block.timestamp + 365 days),
                     bytes32(uint256(1)), block.timestamp + 1 hours, sig, _meta());
    }

    function test_Pause_unpauseRestoresRegister() public {
        vm.startPrank(admin);
        reg.pause();
        reg.unpause();
        vm.stopPrank();

        bytes memory sig = _signRegistration("alice", alice, uint64(block.timestamp + 365 days),
                                             bytes32(uint256(2)), block.timestamp + 1 hours, gatewayPk);
        reg.register("alice", alice, uint64(block.timestamp + 365 days),
                     bytes32(uint256(2)), block.timestamp + 1 hours, sig, _meta());
        assertEq(reg.ownerOfLabel(_node("alice")), alice);
    }

    function test_Pause_revertsForNonOps() public {
        bytes32 opsRole = reg.BANKON_OPS_ROLE();
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            IAccessControl.AccessControlUnauthorizedAccount.selector, alice, opsRole
        ));
        reg.pause();
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Admin                                                            */
    /* ════════════════════════════════════════════════════════════════ */

    function test_SetPriceOracle_byGov() public {
        BankonPriceOracle newOracle = new BankonPriceOracle(admin);
        vm.prank(admin);
        reg.setPriceOracle(address(newOracle));
        assertEq(address(reg.priceOracle()), address(newOracle));
    }

    function test_SetPriceOracle_revertsOnZero() public {
        vm.prank(admin);
        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        reg.setPriceOracle(address(0));
    }

    function test_SetReputationGate_byGov() public {
        BankonReputationGate newGate = new BankonReputationGate(admin);
        vm.prank(admin);
        reg.setReputationGate(address(newGate));
        assertEq(address(reg.reputationGate()), address(newGate));
    }

    function test_SetIdentityRegistry8004_byGov() public {
        vm.prank(admin);
        reg.setIdentityRegistry8004(address(0xBEEF));
        assertEq(address(reg.identityRegistry8004()), address(0xBEEF));
    }

    function test_SetErc8004Bundle_emits() public {
        vm.prank(admin);
        reg.setErc8004Bundle(false);
        assertFalse(reg.erc8004BundleEnabled());
    }

    function test_GrantGatewaySignerRole_letsNewSignerVouch() public {
        uint256 newSignerPk = 0xCAFE;
        address newSigner   = vm.addr(newSignerPk);
        bytes32 gwRole = reg.GATEWAY_SIGNER_ROLE();
        vm.prank(admin);
        reg.grantRole(gwRole, newSigner);

        bytes memory sig = _signRegistration("alice", alice, uint64(block.timestamp + 365 days),
                                             bytes32(uint256(3)), block.timestamp + 1 hours, newSignerPk);
        reg.register("alice", alice, uint64(block.timestamp + 365 days),
                     bytes32(uint256(3)), block.timestamp + 1 hours, sig, _meta());
        assertEq(reg.ownerOfLabel(_node("alice")), alice);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Quote                                                            */
    /* ════════════════════════════════════════════════════════════════ */

    function test_QuoteUSD_usesOracle() public view {
        // 5-char default = $5/yr (5_000000 in USDC base units), exactly 1 year
        uint256 q = reg.quoteUSD("alice", uint64(block.timestamp + 365 days));
        assertEq(q, 5_000000);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  Fuzz                                                             */
    /* ════════════════════════════════════════════════════════════════ */

    function testFuzz_PaidRegister_arbitraryReceiptAndExpiry(bytes32 receipt, uint16 daysOut) public {
        vm.assume(receipt != bytes32(0));
        vm.assume(daysOut >= 1 && daysOut <= 365 * 5);
        string memory label = "fuzzz";
        uint64 expiry = uint64(block.timestamp + uint256(daysOut) * 1 days);
        uint256 deadline = block.timestamp + 1 hours;
        bytes memory sig = _signRegistration(label, alice, expiry, receipt, deadline, gatewayPk);
        reg.register(label, alice, expiry, receipt, deadline, sig, _meta());
        assertEq(reg.ownerOfLabel(_node(label)), alice);
        assertTrue(reg.usedReceipts(receipt));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  registerAgentSubname — mindX agent free address-as-label mint    */
    /* ════════════════════════════════════════════════════════════════ */

    address internal mindxMinter = address(0xCA51EFE);

    function _grantMindxMinter() internal {
        bytes32 role = reg.MINDX_AGENT_MINTER_ROLE();
        vm.prank(admin);
        reg.grantRole(role, mindxMinter);
    }

    function test_AgentSubname_revertsWithoutRole() public {
        // alice (no role) tries to mint for herself
        vm.prank(alice);
        vm.expectRevert();  // OZ AccessControl reverts with selector
        reg.registerAgentSubname(alice, uint64(block.timestamp + 365 days), _meta());
    }

    function test_AgentSubname_mintsWithRole_freeAddressAsLabel() public {
        _grantMindxMinter();
        uint64 expiry = uint64(block.timestamp + 365 days);

        vm.prank(mindxMinter);
        (bytes32 node, uint256 agentId, string memory label) =
            reg.registerAgentSubname(alice, expiry, _meta());

        // Label must be lowercase 40-char hex of alice (no 0x).
        // alice = 0xa1, so label is "00...0a1" (40 chars, lowercase).
        assertEq(bytes(label).length, 40);
        // Node matches namehash(label, parentNode)
        assertEq(node, _node(label));
        // ERC-8004 bundle still happens
        assertGt(agentId, 0);
        // alice is the owner of the subname
        assertEq(reg.ownerOfLabel(node), alice);
    }

    function test_AgentSubname_labelIsLowercaseHexNoPrefix() public {
        _grantMindxMinter();
        // Cast a non-trivial address to test the hex encoding
        address agent = 0xDEaDBeEFcAfe1234567890aBCDEF1234567890AB;

        vm.prank(mindxMinter);
        (, , string memory label) =
            reg.registerAgentSubname(agent, uint64(block.timestamp + 365 days), _meta());

        // Expected: deadbeefcafe1234567890abcdef1234567890ab (lowercased, no 0x)
        assertEq(label, "deadbeefcafe1234567890abcdef1234567890ab");
        assertEq(bytes(label).length, 40);
    }

    function test_AgentSubname_revertsOnZeroAddress() public {
        _grantMindxMinter();
        vm.prank(mindxMinter);
        vm.expectRevert(BankonSubnameRegistrar.ZeroAddress.selector);
        reg.registerAgentSubname(address(0), uint64(block.timestamp + 365 days), _meta());
    }

    function test_AgentSubname_paidAndFreePathsStillWork() public {
        // Verify the existing paid + reputation-gated free paths are unchanged
        // after adding the new role-gated agent path.
        _grantMindxMinter();

        // Paid path
        bytes32 receipt = keccak256("paid-receipt-1");
        uint64 expiry = uint64(block.timestamp + 365 days);
        uint256 deadline = block.timestamp + 1 hours;
        bytes memory sig = _signRegistration("paidalice", alice, expiry, receipt, deadline, gatewayPk);
        reg.register("paidalice", alice, expiry, receipt, deadline, sig, _meta());
        assertEq(reg.ownerOfLabel(_node("paidalice")), alice);

        // Reputation-gated free path
        gate.setAdminScore(bob, 200);
        reg.registerFree("longbob123", bob, expiry, _meta());
        assertEq(reg.ownerOfLabel(_node("longbob123")), bob);

        // New agent path
        vm.prank(mindxMinter);
        reg.registerAgentSubname(carol, expiry, _meta());
        // (label = lowercase hex of carol address)
    }
}
