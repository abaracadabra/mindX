// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Unit suite for the modular canonical EIP-7857 + ERC-6551 stack. Uses mocks for
// NameWrapper + the 6551 registry so it runs without an RPC fork. A separate
// fork test (test/inft7857/fork/) exercises the real mainnet NameWrapper.
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {bankon_inft_subname} from "../../contracts/inft7857/bankon_inft_subname.sol";
import {bankon_inft_extension} from "../../contracts/inft7857/bankon_inft_extension.sol";
import {bankon_inft_registrar} from "../../contracts/inft7857/bankon_inft_registrar.sol";
import {bankon_tba_account} from "../../contracts/inft7857/bankon_tba_account.sol";
import {bankon_inft_oracle} from "../../contracts/inft7857/bankon_inft_oracle.sol";
import {
    INameWrapper, IERC6551Registry, IntelligentData, IERC7572
} from "../../contracts/inft7857/bankon_interfaces.sol";

contract MockNameWrapper is INameWrapper {
    mapping(uint256 => address) public owners;
    function setSubnodeOwner(bytes32 parentNode, string calldata label, address owner, uint32, uint64)
        external returns (bytes32 node)
    {
        node = keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));
        owners[uint256(node)] = owner;
    }
    function setSubnodeRecord(bytes32 parentNode, string calldata label, address owner, address, uint64, uint32, uint64)
        external returns (bytes32 node)
    {
        node = keccak256(abi.encodePacked(parentNode, keccak256(bytes(label))));
        owners[uint256(node)] = owner;
    }
    function ownerOf(uint256 id) external view returns (address) { return owners[id]; }
    function safeTransferFrom(address, address, uint256, uint256, bytes calldata) external {}
    function getData(uint256) external pure returns (address, uint32, uint64) { return (address(0), 0, 0); }
    function allFusesBurned(bytes32, uint32) external pure returns (bool) { return true; }
    function setApprovalForAll(address, bool) external {}
}

contract MockRegistry is IERC6551Registry {
    function createAccount(address impl, bytes32 salt, uint256 chainId, address tc, uint256 id)
        external returns (address) { return account(impl, salt, chainId, tc, id); }
    function account(address impl, bytes32 salt, uint256 chainId, address tc, uint256 id)
        public pure returns (address)
    { return address(uint160(uint256(keccak256(abi.encode(impl, salt, chainId, tc, id))))); }
}

contract bankon_inft_subname_test is Test {
    bankon_inft_subname inft;
    bankon_inft_extension ext;
    bankon_inft_registrar reg;
    bankon_tba_account tbaImpl;
    bankon_inft_oracle oracle;
    MockNameWrapper wrapper;
    MockRegistry registry;

    address admin = address(0xBA1);
    address user = address(0xBA2);
    address user2 = address(0xBA3);
    address treasury = address(0xBA4);
    address signer1;
    uint256 signer1Pk;
    bytes32 constant BANKON_NODE = keccak256(abi.encodePacked(
        keccak256(abi.encodePacked(bytes32(0), keccak256("eth"))), keccak256("bankon")
    ));

    function setUp() public {
        (signer1, signer1Pk) = makeAddrAndKey("signer1");
        address[] memory s = new address[](1); s[0] = signer1;
        wrapper = new MockNameWrapper();
        registry = new MockRegistry();
        oracle = new bankon_inft_oracle(admin, s, 1);
        tbaImpl = new bankon_tba_account();
        inft = new bankon_inft_subname(
            "BANKON Agent", "BANK", "ipfs://bankon", "https://bankon.eth/contract.json",
            admin, address(0), wrapper, oracle, treasury, 250
        );
        ext = new bankon_inft_extension(
            "BANKON Ext", "BANKX", "ipfs://bankon-ext", admin, wrapper, oracle, treasury, 250
        );
        reg = new bankon_inft_registrar(
            admin, wrapper, inft, ext, registry, address(tbaImpl), signer1
        );
        vm.prank(admin); inft.setMinter(address(reg));
    }

    function _data() internal pure returns (IntelligentData[] memory d) {
        d = new IntelligentData[](1);
        d[0] = IntelligentData("agent", keccak256("seed"));
    }

    /* interface introspection */
    function test_supportsInterface_erc5192() public view { assertTrue(inft.supportsInterface(0xb45a3c0e)); }
    function test_supportsInterface_erc4906() public view { assertTrue(inft.supportsInterface(0x49064906)); }
    function test_supportsInterface_erc2981() public view { assertTrue(inft.supportsInterface(0x2a55205a)); }
    function test_supportsInterface_erc7572() public view { assertTrue(inft.supportsInterface(type(IERC7572).interfaceId)); }
    function test_supportsInterface_erc721()  public view { assertTrue(inft.supportsInterface(0x80ac58cd)); }

    /* royalty */
    function test_royaltyInfo_default_250_bps() public view {
        (address rcv, uint256 amt) = inft.royaltyInfo(1, 1 ether);
        assertEq(rcv, treasury); assertEq(amt, 1 ether * 250 / 10000);
    }
    function test_setRoyalty_above_10000_reverts() public {
        vm.prank(admin); vm.expectRevert(); inft.setDefaultRoyalty(treasury, 10001);
    }

    /* soulbound */
    function test_minter_only() public {
        vm.expectRevert(bankon_inft_subname.NotMinter.selector);
        inft.mintUnified("x", user, BANKON_NODE, _data(), true, uint64(block.timestamp + 365 days));
    }
    function test_locked_when_soulbound() public {
        vm.prank(address(reg));
        (uint256 id,) = inft.mintUnified("alice", user, BANKON_NODE, _data(), true, uint64(block.timestamp + 365 days));
        assertTrue(inft.locked(id));
        assertEq(inft.ownerOf(id), user);
    }
    function test_transfer_reverts_when_soulbound() public {
        vm.prank(address(reg));
        (uint256 id,) = inft.mintUnified("alice2", user, BANKON_NODE, _data(), true, uint64(block.timestamp + 365 days));
        vm.prank(user);
        vm.expectRevert(abi.encodeWithSelector(bankon_inft_subname.TokenSoulbound.selector, id));
        inft.transferFrom(user, user2, id);
    }
    function test_transfer_succeeds_when_not_soulbound() public {
        vm.prank(address(reg));
        (uint256 id,) = inft.mintUnified("bob", user, BANKON_NODE, _data(), false, uint64(block.timestamp + 365 days));
        vm.prank(user); inft.transferFrom(user, user2, id);
        assertEq(inft.ownerOf(id), user2);
    }
    function test_intelligentDataOf() public {
        vm.prank(address(reg));
        (uint256 id,) = inft.mintUnified("carol", user, BANKON_NODE, _data(), true, uint64(block.timestamp + 365 days));
        IntelligentData[] memory d = inft.intelligentDataOf(id);
        assertEq(d.length, 1); assertEq(d[0].dataHash, keccak256("seed"));
    }

    /* authorize / revoke */
    function test_authorize_and_revoke() public {
        vm.prank(address(reg));
        (uint256 id,) = inft.mintUnified("dave", user, BANKON_NODE, _data(), true, uint64(block.timestamp + 365 days));
        vm.prank(user); inft.authorizeUsage(id, user2);
        assertEq(inft.authorizedUsersOf(id)[0], user2);
        vm.prank(user); inft.revokeAuthorization(id, user2);
        assertEq(inft.authorizedUsersOf(id).length, 0);
    }

    /* registrar: x402-gated unified mint + deterministic TBA */
    function test_registrar_unified_mint_and_tba() public {
        bytes32 receipt = keccak256("r1");
        uint64 expiry = uint64(block.timestamp + 365 days);
        bankon_inft_registrar.MintMode mode = bankon_inft_registrar.MintMode.UNIFIED_INFT_SOULBOUND;
        bytes32 digest = _x402Digest(user, BANKON_NODE, "erc7857agent", mode, expiry, receipt);
        (uint8 v, bytes32 r, bytes32 s2) = vm.sign(signer1Pk, digest);
        (uint256 tokenId, address tba) = reg.mintWithX402(
            user, BANKON_NODE, "erc7857agent", mode, expiry, _data(), receipt, abi.encodePacked(r, s2, v)
        );
        assertEq(inft.ownerOf(tokenId), user);
        assertTrue(inft.locked(tokenId));
        // TBA matches the deterministic registry computation
        assertEq(tba, registry.account(address(tbaImpl), bytes32(0), block.chainid, address(inft), tokenId));
    }
    function test_registrar_receipt_replay_blocked() public {
        bytes32 receipt = keccak256("r2");
        uint64 expiry = uint64(block.timestamp + 365 days);
        bankon_inft_registrar.MintMode mode = bankon_inft_registrar.MintMode.UNIFIED_INFT;
        bytes32 digest = _x402Digest(user, BANKON_NODE, "agentx", mode, expiry, receipt);
        (uint8 v, bytes32 r, bytes32 s2) = vm.sign(signer1Pk, digest);
        bytes memory sig = abi.encodePacked(r, s2, v);
        reg.mintWithX402(user, BANKON_NODE, "agentx", mode, expiry, _data(), receipt, sig);
        vm.expectRevert(abi.encodeWithSelector(bankon_inft_registrar.ReceiptUsed.selector, receipt));
        reg.mintWithX402(user, BANKON_NODE, "agentx", mode, expiry, _data(), receipt, sig);
    }

    function _x402Digest(
        address to, bytes32 parentNode, string memory label,
        bankon_inft_registrar.MintMode mode, uint64 expiry, bytes32 receipt
    ) internal view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(
            reg.X402_TYPEHASH(), to, parentNode, keccak256(bytes(label)), uint8(mode), expiry, receipt
        ));
        bytes32 domainSep = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256("BankonRegistrar"), keccak256("1"), block.chainid, address(reg)
        ));
        return keccak256(abi.encodePacked("\x19\x01", domainSep, structHash));
    }
}
