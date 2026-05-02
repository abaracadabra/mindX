// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {iNFT_7857, IERC7857} from "../../inft/iNFT_7857.sol";
import {IERC721}         from "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import {IERC721Receiver} from "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import {IERC2981}        from "@openzeppelin/contracts/interfaces/IERC2981.sol";
import {IAccessControl}  from "@openzeppelin/contracts/access/IAccessControl.sol";
import {Pausable}        from "@openzeppelin/contracts/utils/Pausable.sol";
import {ECDSA}           from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @notice Comprehensive Foundry suite for iNFT_7857 (ERC-7857 hardened build).
contract iNFT_7857_Test is Test {

    iNFT_7857 internal nft;

    // Test fixtures
    address internal admin     = address(0xA11CE);
    address internal minter    = address(0xB0B);
    uint256 internal oraclePk  = 0xBEEF;
    address internal oracle;
    address internal alice     = address(0xA1);
    address internal bob       = address(0xB1);
    address internal carol     = address(0xC1);
    address internal treasury  = address(0xDEAD);
    address internal royaltyTo = address(0xCAFE);
    address internal mp        = address(0x4A4); // mock marketplace
    address internal vault     = address(0xBA17); // mock BANKON vault

    bytes32 internal constant ROOT_A = bytes32(uint256(0x11AA));
    bytes32 internal constant ROOT_B = bytes32(uint256(0x22BB));
    bytes32 internal constant META_A = bytes32(uint256(0xCCCC));
    bytes32 internal constant SKEY_A = keccak256("alice-key-v1");
    bytes32 internal constant SKEY_B = keccak256("bob-key-v1");

    function setUp() public {
        oracle = vm.addr(oraclePk);

        nft = new iNFT_7857(
            "mindX iNFT-7857",
            "MINFT",
            admin,            // DEFAULT_ADMIN_ROLE + all role grants
            royaltyTo,        // royalty receiver
            500,              // 5% royalty
            oracle,           // oracle pubkey for ECDSA verification
            treasury,         // clone fee recipient
            0.01 ether        // clone fee
        );

        // Operator delegates MINTER_ROLE to a separate "minter" identity
        // (mirrors AgenticPlace marketplace / BANKON vault / IDManagerAgent).
        bytes32 minterRole = nft.MINTER_ROLE();
        vm.prank(admin);
        nft.grantRole(minterRole, minter);

        // Fund cloners
        vm.deal(alice, 10 ether);
        vm.deal(bob,   10 ether);
        vm.deal(carol, 10 ether);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  HELPERS                                                          */
    /* ════════════════════════════════════════════════════════════════ */

    function _mint(address to, bytes32 root) internal returns (uint256 tokenId) {
        vm.prank(minter);
        tokenId = nft.mintAgent(
            to, root, "0g://galileo/test", META_A, 2048, 8, SKEY_A,
            "https://mindx.pythai.net/inft/test"
        );
    }

    function _signSealedKey(uint256 tokenId, address from, address to, bytes32 newSealedKeyHash)
        internal view returns (bytes memory sig)
    {
        bytes32 root = nft.getPayload(tokenId).contentRoot;
        uint256 nonce = nft.oracleNonce(tokenId);
        bytes32 digest = nft.sealedKeyDigest(tokenId, from, to, root, newSealedKeyHash, nonce);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(oraclePk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _signClone(uint256 parentTokenId, address to, bytes32 newSealedKeyHash)
        internal view returns (bytes memory sig)
    {
        bytes32 root = nft.getPayload(parentTokenId).contentRoot;
        uint256 nonce = nft.oracleNonce(parentTokenId);
        bytes32 digest = nft.cloneDigest(parentTokenId, to, root, newSealedKeyHash, nonce);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(oraclePk, digest);
        return abi.encodePacked(r, s, v);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  CONSTRUCTION                                                     */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Constructor_setsRolesAndRoyalty() public view {
        assertTrue(nft.hasRole(nft.DEFAULT_ADMIN_ROLE(), admin));
        assertTrue(nft.hasRole(nft.MINTER_ROLE(),        admin));
        assertTrue(nft.hasRole(nft.PAUSER_ROLE(),        admin));
        assertTrue(nft.hasRole(nft.TREASURER_ROLE(),     admin));
        assertTrue(nft.hasRole(nft.ORACLE_ROLE(),        oracle));
        assertEq(nft.oracle(),   oracle);
        assertEq(nft.treasury(), treasury);
        assertEq(nft.cloneFeeWei(), 0.01 ether);
        assertEq(nft.name(),   "mindX iNFT-7857");
        assertEq(nft.symbol(), "MINFT");
        (address rcv, uint256 amt) = nft.royaltyInfo(1, 10_000);
        assertEq(rcv, royaltyTo);
        assertEq(amt, 500);          // 5% of 10000
    }

    function test_Constructor_revertsOnZeroAdmin() public {
        vm.expectRevert(iNFT_7857.ZeroAddress.selector);
        new iNFT_7857("X", "X", address(0), royaltyTo, 0, oracle, treasury, 0);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  MINT                                                             */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Mint_happyPath_emitsAndStores() public {
        vm.expectEmit(true, true, true, true);
        emit IERC7857.AgentMinted(1, ROOT_A, 2048, alice);

        uint256 id = _mint(alice, ROOT_A);
        assertEq(id, 1);
        assertEq(nft.ownerOf(id), alice);
        assertEq(nft.totalMinted(), 1);
        assertTrue(nft.exists(id));
        assertTrue(nft.isRootUsed(ROOT_A));

        iNFT_7857.IntelligencePayload memory p = nft.getPayload(id);
        assertEq(p.contentRoot,   ROOT_A);
        assertEq(p.dimensions,    2048);
        assertEq(p.parallelUnits, 8);
        assertEq(p.sealedKeyHash, SKEY_A);
        assertTrue(p.verified);
    }

    function test_Mint_revertsOnDuplicateRoot() public {
        _mint(alice, ROOT_A);
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.ContentRootAlreadyMinted.selector, ROOT_A));
        nft.mintAgent(bob, ROOT_A, "0g://x", META_A, 2048, 8, SKEY_B, "");
    }

    function test_Mint_revertsOnZeroAddress() public {
        vm.prank(minter);
        vm.expectRevert(iNFT_7857.ZeroAddress.selector);
        nft.mintAgent(address(0), ROOT_A, "0g://x", META_A, 2048, 8, SKEY_A, "");
    }

    function test_Mint_revertsOnZeroRoot() public {
        vm.prank(minter);
        vm.expectRevert(iNFT_7857.ZeroBytes32.selector);
        nft.mintAgent(alice, bytes32(0), "0g://x", META_A, 2048, 8, SKEY_A, "");
    }

    function test_Mint_revertsOnZeroSealedKey() public {
        vm.prank(minter);
        vm.expectRevert(iNFT_7857.ZeroBytes32.selector);
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, 2048, 8, bytes32(0), "");
    }

    function test_Mint_revertsOnInvalidDimension() public {
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.InvalidDimension.selector, uint32(123)));
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, 123, 8, SKEY_A, "");
    }

    function test_Mint_revertsOnZeroParallelUnits() public {
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.InvalidDimension.selector, uint32(0)));
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, 2048, 0, SKEY_A, "");
    }

    function test_Mint_revertsOnEmptyURI() public {
        vm.prank(minter);
        vm.expectRevert(iNFT_7857.EmptyString.selector);
        nft.mintAgent(alice, ROOT_A, "", META_A, 2048, 8, SKEY_A, "");
    }

    function test_Mint_revertsOnURITooLong() public {
        bytes memory huge = new bytes(2049);
        for (uint256 i = 0; i < huge.length; i++) huge[i] = "a";
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.StringTooLong.selector, uint256(2049)));
        nft.mintAgent(alice, ROOT_A, string(huge), META_A, 2048, 8, SKEY_A, "");
    }

    function test_Mint_revertsWithoutMinterRole() public {
        bytes32 minterRole = nft.MINTER_ROLE();
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            IAccessControl.AccessControlUnauthorizedAccount.selector,
            alice, minterRole
        ));
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, 2048, 8, SKEY_A, "");
    }

    function test_Mint_acceptsAllValidDimensions() public {
        uint32[11] memory dims = nft.validDimensions();
        for (uint256 i = 0; i < dims.length; i++) {
            bytes32 r = bytes32(uint256(0xDEAD000) + i);
            vm.prank(minter);
            uint256 id = nft.mintAgent(alice, r, "0g://x", META_A, dims[i], 1, SKEY_A, "");
            assertEq(nft.getPayload(id).dimensions, dims[i]);
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  TRANSFER GATING — the heart of ERC-7857                          */
    /* ════════════════════════════════════════════════════════════════ */

    function test_StandardTransferFrom_reverts() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        vm.expectRevert(iNFT_7857.TransferRequiresSealedKey.selector);
        nft.transferFrom(alice, bob, id);
    }

    function test_SafeTransferFrom_reverts() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        vm.expectRevert(iNFT_7857.TransferRequiresSealedKey.selector);
        nft.safeTransferFrom(alice, bob, id);
    }

    function test_SafeTransferFromWithData_reverts() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        vm.expectRevert(iNFT_7857.TransferRequiresSealedKey.selector);
        nft.safeTransferFrom(alice, bob, id, "");
    }

    function test_TransferWithSealedKey_succeeds_andRotatesKey() public {
        uint256 id = _mint(alice, ROOT_A);
        bytes memory newSealedKey = unicode"alice→bob ciphertext";
        bytes32 newHash = keccak256(newSealedKey);
        bytes memory sig = _signSealedKey(id, alice, bob, newHash);

        vm.expectEmit(true, true, false, true);
        emit IERC7857.SealedKeyRotated(id, bob, newHash);

        vm.prank(alice);
        nft.transferWithSealedKey(alice, bob, id, newSealedKey, sig);

        assertEq(nft.ownerOf(id), bob);
        assertEq(nft.getPayload(id).sealedKeyHash, newHash);
        assertEq(nft.oracleNonce(id), 1);
    }

    function test_TransferWithSealedKey_revertsOnBadOracleSignature() public {
        uint256 id = _mint(alice, ROOT_A);
        // Sign with wrong key
        uint256 fakeKey = 0xDEAD;
        bytes32 newHash = keccak256("fake");
        uint256 nonce = nft.oracleNonce(id);
        bytes32 digest = nft.sealedKeyDigest(id, alice, bob, ROOT_A, newHash, nonce);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(fakeKey, digest);
        bytes memory badSig = abi.encodePacked(r, s, v);

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.WrongOracleSigner.selector,
            vm.addr(fakeKey),
            oracle
        ));
        nft.transferWithSealedKey(alice, bob, id, "fake", badSig);
    }

    function test_TransferWithSealedKey_revertsWhenCallerNotApproved() public {
        uint256 id = _mint(alice, ROOT_A);
        bytes memory sealed_ = "x";
        bytes memory sig = _signSealedKey(id, alice, bob, keccak256(sealed_));
        vm.prank(carol);   // carol has no approval
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.NotAuthorized.selector, carol));
        nft.transferWithSealedKey(alice, bob, id, sealed_, sig);
    }

    function test_TransferWithSealedKey_revertsOnReplay() public {
        uint256 id = _mint(alice, ROOT_A);
        bytes memory sealed_ = "x";
        bytes32 h = keccak256(sealed_);
        bytes memory sig = _signSealedKey(id, alice, bob, h);
        vm.prank(alice);
        nft.transferWithSealedKey(alice, bob, id, sealed_, sig);

        // bob tries to replay the SAME signature back to alice — nonce changed
        vm.prank(bob);
        vm.expectRevert();   // wrong-signer because new nonce makes new digest
        nft.transferWithSealedKey(bob, alice, id, sealed_, sig);
    }

    function test_TransferWithSealedKey_revertsOnZeroTo() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        vm.expectRevert(iNFT_7857.ZeroAddress.selector);
        nft.transferWithSealedKey(alice, address(0), id, "x", new bytes(65));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  CLONE                                                            */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Clone_happyPath_paysFee_emitsEvent() public {
        uint256 parent = _mint(alice, ROOT_A);
        bytes memory sealed_ = "carol-clone-key";
        bytes32 h = keccak256(sealed_);
        bytes memory sig = _signClone(parent, carol, h);

        uint256 treasuryBefore = treasury.balance;

        vm.expectEmit(true, true, true, true);
        emit IERC7857.AgentCloned(parent, 2, alice);

        vm.prank(alice);
        uint256 child = nft.cloneAgent{value: 0.01 ether}(parent, carol, sealed_, sig);

        assertEq(child, 2);
        assertEq(nft.ownerOf(child), carol);
        assertEq(nft.cloneCount(parent), 1);
        assertEq(nft.clonedFrom(child), parent);
        assertEq(nft.getPayload(child).contentRoot, nft.getPayload(parent).contentRoot);
        assertEq(nft.getPayload(child).sealedKeyHash, h);
        assertEq(treasury.balance - treasuryBefore, 0.01 ether);
    }

    function test_Clone_revertsOnUnderpayment() public {
        uint256 parent = _mint(alice, ROOT_A);
        bytes memory sealed_ = "x";
        bytes memory sig = _signClone(parent, carol, keccak256(sealed_));
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            iNFT_7857.CloneFeeUnderpaid.selector, uint256(0.005 ether), uint256(0.01 ether)
        ));
        nft.cloneAgent{value: 0.005 ether}(parent, carol, sealed_, sig);
    }

    function test_Clone_revertsWhenNotApproved() public {
        uint256 parent = _mint(alice, ROOT_A);
        bytes memory sealed_ = "x";
        bytes memory sig = _signClone(parent, carol, keccak256(sealed_));
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.NotAuthorized.selector, bob));
        nft.cloneAgent{value: 0.01 ether}(parent, carol, sealed_, sig);
    }

    function test_Clone_revertsOnBadOracleProof() public {
        uint256 parent = _mint(alice, ROOT_A);
        uint256 fakeKey = 0xBAD;
        bytes memory sealed_ = "x";
        bytes32 h = keccak256(sealed_);
        uint256 nonce = nft.oracleNonce(parent);
        bytes32 digest = nft.cloneDigest(parent, carol, ROOT_A, h, nonce);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(fakeKey, digest);
        bytes memory badSig = abi.encodePacked(r, s, v);

        vm.prank(alice);
        vm.expectRevert();
        nft.cloneAgent{value: 0.01 ether}(parent, carol, sealed_, badSig);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  AUTHORIZE / REVOKE USAGE                                         */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Authorize_emitsAndStores() public {
        uint256 id = _mint(alice, ROOT_A);
        uint64 expiry = uint64(block.timestamp + 1 days);
        vm.expectEmit(true, true, false, true);
        emit IERC7857.UsageAuthorized(id, bob, 0xFF, expiry, alice);
        vm.prank(alice);
        nft.authorizeUsage(id, bob, 0xFF, expiry);

        assertTrue(nft.isUsageAuthorized(id, bob));
        iNFT_7857.UsageGrant memory g = nft.getUsageGrant(id, bob);
        assertEq(g.permissions, 0xFF);
        assertEq(g.expiresAt,   expiry);
        assertEq(g.grantor,     alice);
    }

    function test_Authorize_perExecutorIsolation() public {
        uint256 id = _mint(alice, ROOT_A);
        uint64 e1 = uint64(block.timestamp + 1 days);
        uint64 e2 = uint64(block.timestamp + 2 days);
        vm.startPrank(alice);
        nft.authorizeUsage(id, bob,   0x01, e1);
        nft.authorizeUsage(id, carol, 0x02, e2);
        vm.stopPrank();
        assertEq(nft.getUsageGrant(id, bob).permissions,   0x01);
        assertEq(nft.getUsageGrant(id, carol).permissions, 0x02);
        assertTrue(nft.isUsageAuthorized(id, bob));
        assertTrue(nft.isUsageAuthorized(id, carol));
    }

    function test_Authorize_revertsOnPastExpiry() public {
        uint256 id = _mint(alice, ROOT_A);
        // jump forward so block.timestamp > 0
        vm.warp(1000);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.ExpiryInPast.selector, uint64(500)));
        nft.authorizeUsage(id, bob, 0, 500);
    }

    function test_Authorize_expiresAutomatically() public {
        uint256 id = _mint(alice, ROOT_A);
        uint64 expiry = uint64(block.timestamp + 1 hours);
        vm.prank(alice);
        nft.authorizeUsage(id, bob, 0xFF, expiry);
        assertTrue(nft.isUsageAuthorized(id, bob));
        vm.warp(block.timestamp + 2 hours);
        assertFalse(nft.isUsageAuthorized(id, bob));
    }

    function test_Revoke_emitsAndClears() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        nft.authorizeUsage(id, bob, 0xFF, uint64(block.timestamp + 1 days));

        vm.expectEmit(true, true, true, false);
        emit IERC7857.UsageRevoked(id, bob, alice);
        vm.prank(alice);
        nft.revokeUsage(id, bob);

        assertFalse(nft.isUsageAuthorized(id, bob));
        assertEq(nft.getUsageGrant(id, bob).expiresAt, 0);
    }

    function test_Authorize_revertsForRandomCaller() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.NotAuthorized.selector, bob));
        nft.authorizeUsage(id, carol, 0, uint64(block.timestamp + 1));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  BURN                                                             */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Burn_clearsState_andRootStaysReserved() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        nft.authorizeUsage(id, bob, 0xFF, uint64(block.timestamp + 1 days));

        vm.expectEmit(true, true, false, false);
        emit IERC7857.AgentBurned(id, alice);
        vm.prank(alice);
        nft.burn(id);

        assertFalse(nft.exists(id));
        assertTrue(nft.isRootUsed(ROOT_A));   // root is permanently reserved

        // Re-mint under same root must fail
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.ContentRootAlreadyMinted.selector, ROOT_A));
        nft.mintAgent(carol, ROOT_A, "0g://x", META_A, 2048, 8, SKEY_A, "");
    }

    function test_Burn_revertsForNonOwner() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(bob);
        vm.expectRevert();
        nft.burn(id);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  PAUSE                                                            */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Pause_blocksMint() public {
        vm.prank(admin);
        nft.pause();
        vm.prank(minter);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, 2048, 8, SKEY_A, "");
    }

    function test_Pause_blocksTransfer() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(admin);
        nft.pause();
        bytes memory sealed_ = "x";
        bytes memory sig = new bytes(65);
        vm.prank(alice);
        vm.expectRevert(Pausable.EnforcedPause.selector);
        nft.transferWithSealedKey(alice, bob, id, sealed_, sig);
    }

    function test_Pause_unpauseRestores() public {
        vm.startPrank(admin);
        nft.pause();
        nft.unpause();
        vm.stopPrank();
        // Mint should now succeed
        _mint(alice, ROOT_A);
        assertEq(nft.ownerOf(1), alice);
    }

    function test_Pause_revertsForNonPauser() public {
        bytes32 pauserRole = nft.PAUSER_ROLE();
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(
            IAccessControl.AccessControlUnauthorizedAccount.selector,
            alice, pauserRole
        ));
        nft.pause();
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  ROYALTY                                                          */
    /* ════════════════════════════════════════════════════════════════ */

    function test_Royalty_calculation() public {
        uint256 id = _mint(alice, ROOT_A);
        (address rcv, uint256 amt) = nft.royaltyInfo(id, 1 ether);
        assertEq(rcv, royaltyTo);
        assertEq(amt, 0.05 ether);   // 5%
    }

    function test_Royalty_perTokenOverride() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(admin);
        nft.setTokenRoyalty(id, bob, 1000);   // 10%
        (address rcv, uint256 amt) = nft.royaltyInfo(id, 1 ether);
        assertEq(rcv, bob);
        assertEq(amt, 0.1 ether);
    }

    function test_SetDefaultRoyalty_revertsOverCap() public {
        vm.prank(admin);
        vm.expectRevert();        // exceeds MAX_ROYALTY_BPS
        nft.setDefaultRoyalty(bob, 3000);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  AGENT_ID BINDING                                                 */
    /* ════════════════════════════════════════════════════════════════ */

    function test_BindAgentId_oneShot() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.expectEmit(true, true, false, true);
        emit IERC7857.AgentIdBound(id, keccak256(bytes("ceo-mastermind")), "ceo-mastermind");
        vm.prank(alice);
        nft.bindAgentId(id, "ceo-mastermind");
        assertEq(nft.getAgentId(id), "ceo-mastermind");
        assertEq(nft.getAgentIdHash(id), keccak256(bytes("ceo-mastermind")));

        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.AgentIdAlreadyBound.selector, id));
        nft.bindAgentId(id, "different");
    }

    function test_BindAgentId_revertsOnEmpty() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(alice);
        vm.expectRevert(iNFT_7857.EmptyString.selector);
        nft.bindAgentId(id, "");
    }

    function test_BindAgentId_revertsOnTooLong() public {
        uint256 id = _mint(alice, ROOT_A);
        bytes memory huge = new bytes(65);
        for (uint256 i = 0; i < 65; i++) huge[i] = "x";
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.StringTooLong.selector, uint256(65)));
        nft.bindAgentId(id, string(huge));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  AGENTICPLACE + BANKON HOOKS                                      */
    /* ════════════════════════════════════════════════════════════════ */

    function test_OfferOnAgenticPlace_emits() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.expectEmit(true, true, false, true);
        emit IERC7857.AgenticPlaceListed(id, mp, 0.5 ether, true, address(0));
        vm.prank(alice);
        nft.offerOnAgenticPlace(id, mp, 0.5 ether, true, address(0));
        assertEq(nft.agenticPlaceFor(id), mp);
    }

    function test_BindBankonVault_emits() public {
        uint256 id = _mint(alice, ROOT_A);
        bytes32 ref = keccak256("vault-ref");
        vm.expectEmit(true, true, false, true);
        emit IERC7857.BankonVaultBound(id, vault, ref);
        vm.prank(alice);
        nft.bindBankonVault(id, vault, ref);
        assertEq(nft.bankonVaultFor(id), vault);
        assertEq(nft.bankonVaultRef(id), ref);
    }

    function test_OfferOnAgenticPlace_revertsForNonOwner() public {
        uint256 id = _mint(alice, ROOT_A);
        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.NotAuthorized.selector, bob));
        nft.offerOnAgenticPlace(id, mp, 0, false, address(0));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  ACCESSCONTROL                                                    */
    /* ════════════════════════════════════════════════════════════════ */

    function test_GrantMinterRole_byAdmin() public {
        bytes32 minterRole = nft.MINTER_ROLE();
        vm.prank(admin);
        nft.grantRole(minterRole, alice);
        assertTrue(nft.hasRole(minterRole, alice));
        vm.prank(alice);
        nft.mintAgent(bob, ROOT_A, "0g://x", META_A, 2048, 8, SKEY_A, "");
        assertEq(nft.ownerOf(1), bob);
    }

    function test_RevokeMinterRole_blocksMint() public {
        bytes32 minterRole = nft.MINTER_ROLE();
        vm.prank(admin);
        nft.revokeRole(minterRole, minter);
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(
            IAccessControl.AccessControlUnauthorizedAccount.selector,
            minter, minterRole
        ));
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, 2048, 8, SKEY_A, "");
    }

    function test_SetOracle_swapsRole() public {
        address newOracle = address(0xFEED);
        vm.prank(admin);
        nft.setOracle(newOracle);
        assertEq(nft.oracle(), newOracle);
        assertFalse(nft.hasRole(nft.ORACLE_ROLE(), oracle));
        assertTrue(nft.hasRole(nft.ORACLE_ROLE(), newOracle));
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  INTERFACE SUPPORT                                                */
    /* ════════════════════════════════════════════════════════════════ */

    function test_SupportsInterface_advertisesAll() public view {
        assertTrue(nft.supportsInterface(type(IERC721).interfaceId));
        assertTrue(nft.supportsInterface(type(IERC2981).interfaceId));
        assertTrue(nft.supportsInterface(type(IAccessControl).interfaceId));
        assertTrue(nft.supportsInterface(type(IERC7857).interfaceId));
        assertTrue(nft.supportsInterface(0x01ffc9a7));   // ERC-165
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  TREASURY                                                         */
    /* ════════════════════════════════════════════════════════════════ */

    function test_SetTreasury_byTreasurer() public {
        vm.prank(admin);
        nft.setTreasury(bob);
        assertEq(nft.treasury(), bob);
    }

    function test_SetCloneFee_byTreasurer() public {
        vm.prank(admin);
        nft.setCloneFee(0.5 ether);
        assertEq(nft.cloneFeeWei(), 0.5 ether);
    }

    function test_SetTreasury_revertsForNonTreasurer() public {
        vm.prank(alice);
        vm.expectRevert();
        nft.setTreasury(bob);
    }

    /* ════════════════════════════════════════════════════════════════ */
    /*  FUZZ                                                             */
    /* ════════════════════════════════════════════════════════════════ */

    function testFuzz_Mint_arbitraryRoot(bytes32 root, address to) public {
        vm.assume(root != bytes32(0));
        vm.assume(to != address(0));
        vm.assume(to.code.length == 0);   // skip contracts that may revert in onERC721Received

        vm.prank(minter);
        uint256 id = nft.mintAgent(to, root, "0g://x", META_A, 2048, 1, SKEY_A, "");
        assertEq(nft.ownerOf(id), to);
        assertEq(nft.getPayload(id).contentRoot, root);
        assertTrue(nft.isRootUsed(root));
    }

    function testFuzz_Mint_invalidDimensionAlwaysReverts(uint32 d) public {
        vm.assume(
            d != 8 && d != 64 && d != 256 && d != 512 && d != 768 &&
            d != 1024 && d != 2048 && d != 4096 && d != 8192 &&
            d != 65536 && d != 1048576
        );
        vm.prank(minter);
        vm.expectRevert(abi.encodeWithSelector(iNFT_7857.InvalidDimension.selector, d));
        nft.mintAgent(alice, ROOT_A, "0g://x", META_A, d, 1, SKEY_A, "");
    }

    function testFuzz_AuthorizeRevoke_multipleExecutors(address e1, address e2) public {
        vm.assume(e1 != address(0) && e2 != address(0) && e1 != e2);
        uint256 id = _mint(alice, ROOT_A);
        uint64 expiry = uint64(block.timestamp + 1 hours);
        vm.startPrank(alice);
        nft.authorizeUsage(id, e1, 0x1, expiry);
        nft.authorizeUsage(id, e2, 0x2, expiry);
        vm.stopPrank();
        assertTrue(nft.isUsageAuthorized(id, e1));
        assertTrue(nft.isUsageAuthorized(id, e2));
        vm.prank(alice);
        nft.revokeUsage(id, e1);
        assertFalse(nft.isUsageAuthorized(id, e1));
        assertTrue(nft.isUsageAuthorized(id, e2));
    }

    /// @notice Slither-flagged regression: a malicious receiver tries to
    ///         re-enter mintAgent during onERC721Received while _gateOpen
    ///         is true. The nonReentrant modifier on mintAgent must block it.
    function test_mintAgent_blocksReentrancyViaOnERC721Received() public {
        ReentrantReceiver attacker = new ReentrantReceiver(nft);
        vm.prank(minter);
        // The attacker's onERC721Received calls mintAgent again. nonReentrant
        // on the outer call should cause the re-entry to revert; _safeMint
        // surfaces that revert through ERC721's standard receiver-rejection path.
        vm.expectRevert();
        nft.mintAgent(
            address(attacker),
            ROOT_A,
            "ipfs://x",
            bytes32(uint256(0xab)),
            128,
            1,
            keccak256("sealed-key-A"),
            "ipfs://uri"
        );
    }
}

/// @notice Malicious ERC-721 receiver that re-enters mintAgent during
///         onERC721Received. Used by test_mintAgent_blocksReentrancyViaOnERC721Received.
contract ReentrantReceiver is IERC721Receiver {
    iNFT_7857 internal target;
    constructor(iNFT_7857 _target) {
        target = _target;
    }
    function onERC721Received(
        address /* operator */,
        address /* from */,
        uint256 /* tokenId */,
        bytes calldata /* data */
    ) external returns (bytes4) {
        // Attempt cross-function reentrancy. Will revert because of nonReentrant
        // mutex held by the outer mintAgent call. The revert propagates up.
        target.mintAgent(
            address(this),
            keccak256("re-entry-root"),
            "ipfs://reentry",
            bytes32(uint256(0xcd)),
            128,
            1,
            keccak256("sealed-reentry"),
            "ipfs://uri-reentry"
        );
        return IERC721Receiver.onERC721Received.selector;
    }
}
