// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {iNFT_7857} from "../../inft/iNFT_7857.sol";
import {THOTCommitmentRegistry} from "../../THOT/commitment/THOTCommitmentRegistry.sol";
import {ITHOTCommitmentRegistry} from "../../THOT/interfaces/ITHOTCommitmentRegistry.sol";

/**
 * @title  iNFT_7857_thot_attach_Test
 * @notice Covers the new attachThotRoot + revoke-gate flow.
 *
 *  Test matrix:
 *    1. setCommitmentRegistry: admin only, fires event.
 *    2. attachThotRoot: happy path with registered root.
 *    3. attachThotRoot: reverts when registry not set.
 *    4. attachThotRoot: reverts on unregistered root.
 *    5. attachThotRoot: reverts on revoked root.
 *    6. attachThotRoot: reverts on double-attach.
 *    7. attachThotRoot: MINTER_ROLE-gated.
 *    8. attachThotRoot: rejects zero root.
 *    9. transferWithSealedKey: reverts when attached root is revoked
 *       between mint and transfer.
 *   10. transferWithSealedKey: works normally for tokens without an
 *       attached root (regression test).
 */
contract iNFT_7857_thot_attach_Test is Test {
    iNFT_7857 public inft;
    THOTCommitmentRegistry public registry;

    address public admin;
    address public gate;
    address public issuer;
    address public alice;
    address public bob;
    address public oracleSigner;
    uint256 internal oraclePk;

    function setUp() public {
        admin   = makeAddr("admin-multisig");
        gate    = makeAddr("bankon-gate");
        issuer  = makeAddr("authorized-issuer");
        alice   = makeAddr("alice");
        bob     = makeAddr("bob");
        oraclePk = 0xA11CE;
        oracleSigner = vm.addr(oraclePk);

        // Commitment registry
        registry = new THOTCommitmentRegistry(gate, admin);
        vm.prank(gate);
        registry.authorizeIssuer(issuer);

        // iNFT_7857 — admin holds all roles by default.
        inft = new iNFT_7857(
            "Mock iNFT",
            "MNFT",
            admin,                      // admin
            admin,                      // royaltyReceiver
            500,                        // 5% royalty
            oracleSigner,               // oracle
            admin,                      // treasury
            0                           // cloneFeeWei
        );

        // Wire the registry into iNFT_7857.
        vm.prank(admin);
        inft.setCommitmentRegistry(ITHOTCommitmentRegistry(address(registry)));
    }

    // -----------------------------------------------------------------
    //                  Helpers
    // -----------------------------------------------------------------

    function _registerRoot(bytes32 root, bytes32 head) internal {
        vm.prank(issuer);
        registry.issueTHOT4096(root, head, 255, "ipfs://payload", "ipfs://meta");
    }

    function _mintTokenTo(address to, bytes32 contentRoot)
        internal
        returns (uint256 tokenId)
    {
        vm.prank(admin);   // MINTER_ROLE
        tokenId = inft.mintAgent(
            to,
            contentRoot,
            "0g://galileo/abc",
            keccak256("metadata"),
            uint32(4096),
            uint8(8),
            keccak256("sealed-for-alice"),
            ""
        );
    }

    // -----------------------------------------------------------------
    //                  setCommitmentRegistry
    // -----------------------------------------------------------------

    function test_SetCommitmentRegistry_AdminOnly() public {
        vm.prank(alice);
        vm.expectRevert();
        inft.setCommitmentRegistry(ITHOTCommitmentRegistry(address(registry)));

        vm.prank(admin);
        inft.setCommitmentRegistry(ITHOTCommitmentRegistry(address(registry)));
        assertEq(address(inft.commitmentRegistry()), address(registry));
    }

    function test_SetCommitmentRegistry_CanDetach() public {
        vm.prank(admin);
        inft.setCommitmentRegistry(ITHOTCommitmentRegistry(address(0)));
        assertEq(address(inft.commitmentRegistry()), address(0));
    }

    // -----------------------------------------------------------------
    //                  attachThotRoot
    // -----------------------------------------------------------------

    function test_AttachThotRoot_HappyPath() public {
        bytes32 thotRoot = keccak256("thot-root-A");
        _registerRoot(thotRoot, keccak256("head-A"));

        uint256 tokenId = _mintTokenTo(alice, keccak256("content-A"));

        vm.prank(admin);
        inft.attachThotRoot(tokenId, thotRoot);
        assertEq(inft.thotRootOf(tokenId), thotRoot);
    }

    function test_AttachThotRoot_RevertsWhenRegistryUnset() public {
        vm.prank(admin);
        inft.setCommitmentRegistry(ITHOTCommitmentRegistry(address(0)));

        bytes32 thotRoot = keccak256("thot-root-unset");
        uint256 tokenId = _mintTokenTo(alice, keccak256("content-unset"));

        vm.prank(admin);
        vm.expectRevert(iNFT_7857.CommitmentRegistryUnset.selector);
        inft.attachThotRoot(tokenId, thotRoot);
    }

    function test_AttachThotRoot_RevertsOnUnregisteredRoot() public {
        bytes32 thotRoot = keccak256("never-issued");
        uint256 tokenId = _mintTokenTo(alice, keccak256("content-B"));

        vm.prank(admin);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.ThotRootNotRegistered.selector, thotRoot
        ));
        inft.attachThotRoot(tokenId, thotRoot);
    }

    function test_AttachThotRoot_RevertsOnRevokedRoot() public {
        bytes32 thotRoot = keccak256("thot-root-rev");
        _registerRoot(thotRoot, keccak256("head-rev"));

        // Revoke the root before attaching.
        vm.prank(admin);
        registry.revoke(thotRoot, "censured");

        uint256 tokenId = _mintTokenTo(alice, keccak256("content-rev"));

        vm.prank(admin);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.ThotRootRevoked.selector, thotRoot
        ));
        inft.attachThotRoot(tokenId, thotRoot);
    }

    function test_AttachThotRoot_RevertsOnDoubleAttach() public {
        bytes32 thotRoot = keccak256("thot-root-D");
        _registerRoot(thotRoot, keccak256("head-D"));

        uint256 tokenId = _mintTokenTo(alice, keccak256("content-D"));

        vm.startPrank(admin);
        inft.attachThotRoot(tokenId, thotRoot);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.ThotRootAlreadyAttached.selector, tokenId
        ));
        inft.attachThotRoot(tokenId, thotRoot);
        vm.stopPrank();
    }

    function test_AttachThotRoot_OnlyMinter() public {
        bytes32 thotRoot = keccak256("thot-root-E");
        _registerRoot(thotRoot, keccak256("head-E"));

        uint256 tokenId = _mintTokenTo(alice, keccak256("content-E"));

        vm.prank(alice);   // not MINTER_ROLE
        vm.expectRevert();
        inft.attachThotRoot(tokenId, thotRoot);
    }

    function test_AttachThotRoot_RejectsZeroRoot() public {
        uint256 tokenId = _mintTokenTo(alice, keccak256("content-Z"));
        vm.prank(admin);
        vm.expectRevert(iNFT_7857.ZeroBytes32.selector);
        inft.attachThotRoot(tokenId, bytes32(0));
    }

    function test_AttachThotRoot_RejectsUnknownToken() public {
        bytes32 thotRoot = keccak256("thot-root-T");
        _registerRoot(thotRoot, keccak256("head-T"));
        vm.prank(admin);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.TokenDoesNotExist.selector, uint256(999)
        ));
        inft.attachThotRoot(999, thotRoot);
    }

    // -----------------------------------------------------------------
    //                  Transfer revoke gate
    // -----------------------------------------------------------------

    /// @dev EIP-712 domain separator for the iNFT_7857 instance. Computed
    ///      from the constructor args (name="Mock iNFT", version="1") and
    ///      the live chainId + verifying contract — matches OpenZeppelin's
    ///      `EIP712._domainSeparatorV4()` byte-for-byte.
    function _domainSeparator() internal view returns (bytes32) {
        return keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("Mock iNFT")),
            keccak256(bytes("1")),
            block.chainid,
            address(inft)
        ));
    }

    /// @dev Compose an EIP-712 sealed-key handoff signature so we can
    ///      exercise the real transfer path. Mirrors iNFT_7857's digest
    ///      construction in transferWithSealedKey.
    function _signSealedKey(
        uint256 tokenId,
        address from,
        address to,
        bytes32 contentRoot,
        bytes32 newSealedKeyHash,
        uint256 nonce
    ) internal view returns (bytes memory sig) {
        bytes32 structHash = keccak256(abi.encode(
            inft.SEALED_KEY_TYPEHASH(),
            tokenId, from, to, contentRoot, newSealedKeyHash, nonce
        ));
        bytes32 digest = keccak256(abi.encodePacked(
            "\x19\x01", _domainSeparator(), structHash
        ));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(oraclePk, digest);
        sig = abi.encodePacked(r, s, v);
    }

    function test_TransferRejectedAfterRootRevoked() public {
        bytes32 thotRoot   = keccak256("thot-root-X");
        bytes32 contentRoot = keccak256("content-X");
        _registerRoot(thotRoot, keccak256("head-X"));

        uint256 tokenId = _mintTokenTo(alice, contentRoot);

        vm.prank(admin);
        inft.attachThotRoot(tokenId, thotRoot);

        // Now revoke the THOT root.
        vm.prank(admin);
        registry.revoke(thotRoot, "post-mint censure");

        // Construct a valid sealed-key signature so transfer would
        // otherwise succeed. Revoke is what blocks it.
        bytes memory sealedKey = hex"feedface";
        bytes32 newSealedKeyHash = keccak256(sealedKey);
        bytes memory sig = _signSealedKey(
            tokenId, alice, bob, contentRoot, newSealedKeyHash, 0
        );

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.ThotRootRevoked.selector, thotRoot
        ));
        inft.transferWithSealedKey(alice, bob, tokenId, sealedKey, sig);
    }

    function test_TransferUnaffectedWhenNoRootAttached() public {
        // Token minted without any THOT root attached — transfer must
        // work exactly like before (regression).
        bytes32 contentRoot = keccak256("content-no-attach");
        uint256 tokenId = _mintTokenTo(alice, contentRoot);

        bytes memory sealedKey = hex"deadbeef";
        bytes32 newSealedKeyHash = keccak256(sealedKey);
        bytes memory sig = _signSealedKey(
            tokenId, alice, bob, contentRoot, newSealedKeyHash, 0
        );

        vm.prank(alice);
        inft.transferWithSealedKey(alice, bob, tokenId, sealedKey, sig);
        assertEq(inft.ownerOf(tokenId), bob);
    }
}
