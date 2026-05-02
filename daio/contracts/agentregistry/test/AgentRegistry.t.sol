// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {AgentRegistry, IAgentRegistry} from "../AgentRegistry.sol";
import {IAccessControl} from "@openzeppelin/contracts/access/IAccessControl.sol";
import {IERC721}        from "@openzeppelin/contracts/token/ERC721/IERC721.sol";

contract AgentRegistry_Test is Test {
    AgentRegistry internal reg;

    address internal admin    = address(0xA11CE);
    address internal minter   = address(0xB0B);   // BANKON registrar / iNFT factory analog
    address internal alice    = address(0xA1);
    address internal bob      = address(0xB1);
    uint256 internal attestorPk = 0xCAFE;
    address internal attestor;

    bytes32 internal DOMAIN_SEPARATOR;
    bytes32 internal constant ATTESTATION_TYPEHASH = keccak256(
        "Attestation(uint256 agentTokenId,string attestationURI,uint256 nonce)"
    );

    function setUp() public {
        attestor = vm.addr(attestorPk);
        reg = new AgentRegistry("mindX AgentRegistry", "AREG", admin);
        DOMAIN_SEPARATOR = _domainSeparator(address(reg));

        bytes32 minterRole   = reg.MINTER_ROLE();
        bytes32 attestorRole = reg.ATTESTOR_ROLE();
        vm.startPrank(admin);
        reg.grantRole(minterRole, minter);
        reg.grantRole(attestorRole, attestor);
        vm.stopPrank();
    }

    /* ────────── Helpers ────────── */

    function _domainSeparator(address contractAddr) internal view returns (bytes32) {
        return keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("mindX AgentRegistry")),
            keccak256(bytes("1")),
            block.chainid,
            contractAddr
        ));
    }

    function _signAttestation(uint256 agentTokenId, string memory uri, uint256 nonce, uint256 pk)
        internal view
        returns (bytes memory)
    {
        bytes32 structHash = keccak256(abi.encode(
            ATTESTATION_TYPEHASH, agentTokenId, keccak256(bytes(uri)), nonce
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    /* ────────── Construction ────────── */

    function test_Constructor_setsRolesAndName() public view {
        assertEq(reg.name(), "mindX AgentRegistry");
        assertTrue(reg.hasRole(reg.DEFAULT_ADMIN_ROLE(), admin));
        assertEq(reg.totalAgents(), 0);
    }

    function test_Constructor_revertsOnZeroAdmin() public {
        vm.expectRevert(AgentRegistry.ZeroAddress.selector);
        new AgentRegistry("X", "X", address(0));
    }

    /* ────────── Register ────────── */

    function test_Register_byOwnerSelf() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0xBEEF), bytes32(uint256(0xFF)), "ipfs://attest");
        assertEq(id, 1);
        assertEq(reg.ownerOf(id), alice);
        assertEq(reg.tokenOfAgentIdHash(keccak256(bytes("alice-agent"))), 1);
        ( , string memory aid, address linked, bytes32 cap, string memory uri, uint256 ac) = reg.getAgent(1);
        assertEq(aid, "alice-agent");
        assertEq(linked, address(0xBEEF));
        assertEq(cap, bytes32(uint256(0xFF)));
        assertEq(uri, "ipfs://attest");
        assertEq(ac, 0);
    }

    function test_Register_byMinterForOwner() public {
        vm.prank(minter);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        assertEq(reg.ownerOf(id), alice);
    }

    function test_Register_revertsForRandomCallerNotOwnerNotMinter() public {
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.NotOwnerNorMinter.selector, bob));
        reg.register(alice, "alice-agent", address(0), bytes32(0), "");
    }

    function test_Register_revertsOnEmptyAgentId() public {
        vm.prank(alice);
        vm.expectRevert(AgentRegistry.EmptyAgentId.selector);
        reg.register(alice, "", address(0), bytes32(0), "");
    }

    function test_Register_revertsOnTooLongAgentId() public {
        bytes memory huge = new bytes(65);
        for (uint256 i = 0; i < 65; i++) huge[i] = "x";
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.AgentIdTooLong.selector, uint256(65)));
        reg.register(alice, string(huge), address(0), bytes32(0), "");
    }

    function test_Register_revertsOnZeroOwner() public {
        vm.prank(minter);
        vm.expectRevert(AgentRegistry.ZeroAddress.selector);
        reg.register(address(0), "any", address(0), bytes32(0), "");
    }

    function test_Register_revertsOnDuplicateAgentId() public {
        vm.prank(alice);
        reg.register(alice, "ceo", address(0), bytes32(0), "");
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(
            AgentRegistry.AgentIdAlreadyTaken.selector, keccak256(bytes("ceo"))
        ));
        reg.register(bob, "ceo", address(0), bytes32(0), "");
    }

    /* ────────── Capability + Linked iNFT updates ────────── */

    function test_SetCapabilities_byOwner() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        vm.prank(alice);
        reg.setCapabilities(id, bytes32(uint256(0xFFFF)));
        ( , , , bytes32 cap, , ) = reg.getAgent(id);
        assertEq(cap, bytes32(uint256(0xFFFF)));
    }

    function test_SetCapabilities_revertsForNonOwner() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.NotOwnerNorMinter.selector, bob));
        reg.setCapabilities(id, bytes32(uint256(0x1)));
    }

    function test_SetLinkedINFT_byMinter() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        vm.prank(minter);
        reg.setLinkedINFT(id, address(0xCAFE));
        ( , , address linked, , , ) = reg.getAgent(id);
        assertEq(linked, address(0xCAFE));
    }

    /* ────────── Attestations ────────── */

    function test_Attest_validSignature_incrementsCount() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "ipfs://initial");
        bytes memory sig = _signAttestation(id, "ipfs://attestor1", 0, attestorPk);

        reg.attest(id, "ipfs://attestor1", sig);

        ( , , , , string memory uri, uint256 ac) = reg.getAgent(id);
        assertEq(uri, "ipfs://attestor1");
        assertEq(ac, 1);
        assertEq(reg.attestNonce(id), 1);
    }

    function test_Attest_sameAttestorTwice_doesNotDoubleCount() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");

        bytes memory sig1 = _signAttestation(id, "ipfs://a1", 0, attestorPk);
        reg.attest(id, "ipfs://a1", sig1);
        bytes memory sig2 = _signAttestation(id, "ipfs://a2", 1, attestorPk);
        reg.attest(id, "ipfs://a2", sig2);

        ( , , , , string memory uri, uint256 ac) = reg.getAgent(id);
        assertEq(uri, "ipfs://a2");          // most-recent URI wins
        assertEq(ac, 1);                      // attestorCount stays 1
    }

    function test_Attest_revertsOnNonAttestorSigner() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        uint256 randomPk = 0xDEAD;
        bytes memory sig = _signAttestation(id, "ipfs://x", 0, randomPk);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.NotAttestor.selector, vm.addr(randomPk)));
        reg.attest(id, "ipfs://x", sig);
    }

    function test_Attest_revertsOnTokenDoesNotExist() public {
        bytes memory sig = _signAttestation(99, "ipfs://x", 0, attestorPk);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.TokenDoesNotExist.selector, uint256(99)));
        reg.attest(99, "ipfs://x", sig);
    }

    /* ────────── Soulbound ────────── */

    function test_Soulbound_blocksTransfer() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        vm.prank(admin);
        reg.setSoulbound(id, true);
        vm.prank(alice);
        vm.expectRevert(AgentRegistry.SoulboundCannotTransfer.selector);
        reg.transferFrom(alice, bob, id);
    }

    function test_Soulbound_unsetAllowsTransferAgain() public {
        vm.prank(alice);
        uint256 id = reg.register(alice, "alice-agent", address(0), bytes32(0), "");
        vm.prank(admin);
        reg.setSoulbound(id, true);
        vm.prank(admin);
        reg.setSoulbound(id, false);
        vm.prank(alice);
        reg.transferFrom(alice, bob, id);
        assertEq(reg.ownerOf(id), bob);
    }

    /* ────────── Roles ────────── */

    function test_GrantMinterRole_byAdmin() public {
        bytes32 minterRole = reg.MINTER_ROLE();
        vm.prank(admin);
        reg.grantRole(minterRole, alice);
        assertTrue(reg.hasRole(minterRole, alice));
    }

    /* ────────── Interface support ────────── */

    function test_SupportsInterface_advertisesAll() public view {
        assertTrue(reg.supportsInterface(type(IERC721).interfaceId));
        assertTrue(reg.supportsInterface(type(IAccessControl).interfaceId));
        assertTrue(reg.supportsInterface(type(IAgentRegistry).interfaceId));
        assertTrue(reg.supportsInterface(0x01ffc9a7));   // ERC-165
    }
}
