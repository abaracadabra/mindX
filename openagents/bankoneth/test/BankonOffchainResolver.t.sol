// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonOffchainResolver} from "../contracts/BankonOffchainResolver.sol";

/// @notice EIP-712 helper for signing OffchainLookupResponse payloads.
///         Mirrors the BankonX402Sig helper but typehash + domain differ.
library OffchainProofSig {
    bytes32 internal constant TYPEHASH =
        keccak256("OffchainLookupResponse(bytes result,uint64 expires,address sender,bytes32 callHash)");
    bytes32 internal constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    struct Resp {
        bytes   result;
        uint64  expires;
        address sender;
        bytes32 callHash;
    }

    function sign(Vm vm, uint256 sk, Resp memory r) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(
            abi.encode(TYPEHASH, keccak256(r.result), r.expires, r.sender, r.callHash)
        );
        bytes32 domain = keccak256(
            abi.encode(
                DOMAIN_TYPEHASH,
                keccak256("BankonOffchainResolver"),
                keccak256("1"),
                block.chainid,
                r.sender
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 rr, bytes32 ss) = vm.sign(sk, digest);
        return abi.encodePacked(rr, ss, v);
    }
}

// Re-exported Vm type for the library — forge-std exposes it.
import {Vm} from "forge-std/Vm.sol";

abstract contract OffchainHarness is Test {
    BankonOffchainResolver r;

    address admin = makeAddr("admin");
    string[] urls;

    uint256 signerPk;
    address signer;

    function setUp() public virtual {
        urls = new string[](1);
        urls[0] = "https://offchain.bankon.eth/{sender}/{data}.json";

        signerPk = uint256(keccak256("offchain-signer-1"));
        signer   = vm.addr(signerPk);

        r = new BankonOffchainResolver(admin, urls, signer);
    }

    /// @dev DNS-encode "alice.bankon.eth".
    function _dns_alice_bankon_eth() internal pure returns (bytes memory) {
        return abi.encodePacked(
            bytes1(0x05), "alice", bytes1(0x06), "bankon", bytes1(0x03), "eth", bytes1(0x00)
        );
    }
}

// ── resolve() reverts with OffchainLookup ────────────────────────

contract OffchainResolveTest is OffchainHarness {
    function test_Resolve_revertsOffchainLookup() public {
        bytes memory dns = _dns_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(
            bytes4(0x3b3b57de),  // addr(node)
            keccak256(dns)
        );

        // Expect the revert. Since vm.expectRevert can't match exact tuple-
        // shaped custom errors easily, just expect any revert + assert the
        // selector below by catching low-level.
        (bool ok, bytes memory ret) = address(r).staticcall(
            abi.encodeWithSelector(BankonOffchainResolver.resolve.selector, dns, callData)
        );
        assertFalse(ok, "resolve must revert");

        // First 4 bytes of `ret` are the error selector.
        bytes4 selector;
        assembly { selector := mload(add(ret, 0x20)) }
        assertEq(
            selector,
            BankonOffchainResolver.OffchainLookup.selector,
            "expected OffchainLookup selector"
        );
    }
}

// ── resolveWithProof verifies EIP-712 signature ───────────────────

contract OffchainProofTest is OffchainHarness {
    function _extraData(bytes memory dns, bytes memory data) internal pure returns (bytes memory) {
        bytes memory callHash = abi.encode(keccak256(data));
        return abi.encode(dns, data, callHash);
    }

    function test_ResolveWithProof_happyPath() public {
        bytes memory dns = _dns_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(bytes4(0x3b3b57de), keccak256(dns));
        bytes memory extraData_ = _extraData(dns, callData);

        // Gateway-side response.
        bytes memory result = abi.encode(address(0xcafe));
        uint64 expires = uint64(block.timestamp + 1 hours);

        OffchainProofSig.Resp memory msgStruct = OffchainProofSig.Resp({
            result: result,
            expires: expires,
            sender: address(r),
            callHash: keccak256(callData)
        });
        bytes memory sig = OffchainProofSig.sign(vm, signerPk, msgStruct);
        bytes memory response = abi.encode(result, expires, sig);

        bytes memory got = r.resolveWithProof(response, extraData_);
        address decoded = abi.decode(got, (address));
        assertEq(decoded, address(0xcafe));
    }

    function test_ResolveWithProof_revertsOnExpired() public {
        bytes memory dns = _dns_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(bytes4(0x3b3b57de), keccak256(dns));
        bytes memory extraData_ = _extraData(dns, callData);

        bytes memory result = abi.encode(address(0xcafe));
        uint64 expires = uint64(block.timestamp + 1 hours);

        OffchainProofSig.Resp memory msgStruct = OffchainProofSig.Resp({
            result: result,
            expires: expires,
            sender: address(r),
            callHash: keccak256(callData)
        });
        bytes memory sig = OffchainProofSig.sign(vm, signerPk, msgStruct);

        // Warp past the expiry.
        vm.warp(uint256(expires) + 1);

        bytes memory response = abi.encode(result, expires, sig);
        vm.expectRevert(BankonOffchainResolver.ProofExpired.selector);
        r.resolveWithProof(response, extraData_);
    }

    function test_ResolveWithProof_revertsOnUnknownSigner() public {
        bytes memory dns = _dns_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(bytes4(0x3b3b57de), keccak256(dns));
        bytes memory extraData_ = _extraData(dns, callData);

        bytes memory result = abi.encode(address(0xcafe));
        uint64 expires = uint64(block.timestamp + 1 hours);

        uint256 rogueSk = uint256(keccak256("rogue-signer"));
        OffchainProofSig.Resp memory msgStruct = OffchainProofSig.Resp({
            result: result,
            expires: expires,
            sender: address(r),
            callHash: keccak256(callData)
        });
        bytes memory sig = OffchainProofSig.sign(vm, rogueSk, msgStruct);

        bytes memory response = abi.encode(result, expires, sig);
        vm.expectRevert();  // ProofSignerNotAllowed(rogue)
        r.resolveWithProof(response, extraData_);
    }

    function test_ResolveWithProof_revertsOnCallDataMismatch() public {
        bytes memory dns = _dns_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(bytes4(0x3b3b57de), keccak256(dns));
        bytes memory extraData_ = _extraData(dns, callData);

        bytes memory result = abi.encode(address(0xcafe));
        uint64 expires = uint64(block.timestamp + 1 hours);

        // Gateway signs over a DIFFERENT callHash — substitute attack.
        OffchainProofSig.Resp memory msgStruct = OffchainProofSig.Resp({
            result: result,
            expires: expires,
            sender: address(r),
            callHash: keccak256("different-call")
        });
        bytes memory sig = OffchainProofSig.sign(vm, signerPk, msgStruct);

        bytes memory response = abi.encode(result, expires, sig);
        vm.expectRevert();  // signer recovers to a different address → ProofSignerNotAllowed
        r.resolveWithProof(response, extraData_);
    }
}

// ── Admin / signer rotation ──────────────────────────────────────

contract OffchainAdminTest is OffchainHarness {
    function test_GrantSigner_byAdmin_allowsProof() public {
        uint256 newSignerPk = uint256(keccak256("new-signer"));
        address newSigner   = vm.addr(newSignerPk);

        vm.prank(admin);
        r.grantSigner(newSigner);

        // Now a proof from newSigner should verify.
        bytes memory dns = abi.encodePacked(bytes1(0x03), "bob", bytes1(0x03), "eth", bytes1(0x00));
        bytes memory callData = abi.encodeWithSelector(bytes4(0x3b3b57de), keccak256(dns));
        bytes memory result = abi.encode(address(0xbb));
        uint64 expires = uint64(block.timestamp + 1 hours);
        bytes memory callHash = abi.encode(keccak256(callData));
        bytes memory extraData_ = abi.encode(dns, callData, callHash);

        OffchainProofSig.Resp memory msgStruct = OffchainProofSig.Resp({
            result: result,
            expires: expires,
            sender: address(r),
            callHash: keccak256(callData)
        });
        bytes memory sig = OffchainProofSig.sign(vm, newSignerPk, msgStruct);
        bytes memory response = abi.encode(result, expires, sig);

        bytes memory got = r.resolveWithProof(response, extraData_);
        assertEq(abi.decode(got, (address)), address(0xbb));
    }

    function test_RevokeSigner_byAdmin_blocksProof() public {
        vm.prank(admin);
        r.revokeSigner(signer);
        // Now the original signer's signatures should fail.
        bytes memory dns = _dns_alice_bankon_eth();
        bytes memory callData = abi.encodeWithSelector(bytes4(0x3b3b57de), keccak256(dns));
        bytes memory result = abi.encode(address(0xcafe));
        uint64 expires = uint64(block.timestamp + 1 hours);
        bytes memory callHash = abi.encode(keccak256(callData));
        bytes memory extraData_ = abi.encode(dns, callData, callHash);

        OffchainProofSig.Resp memory msgStruct = OffchainProofSig.Resp({
            result: result, expires: expires, sender: address(r), callHash: keccak256(callData)
        });
        bytes memory sig = OffchainProofSig.sign(vm, signerPk, msgStruct);
        bytes memory response = abi.encode(result, expires, sig);
        vm.expectRevert();
        r.resolveWithProof(response, extraData_);
    }

    function test_SetUrls_byAdmin() public {
        string[] memory next = new string[](2);
        next[0] = "https://primary.bankon.eth/{sender}/{data}.json";
        next[1] = "https://backup.bankon.eth/{sender}/{data}.json";
        vm.prank(admin);
        r.setUrls(next);
        string[] memory got = r.urls();
        assertEq(got.length, 2);
        assertEq(got[0], next[0]);
    }
}

// ── ERC-165 ──────────────────────────────────────────────────────

contract OffchainSupportsInterfaceTest is OffchainHarness {
    function test_AdvertisesIExtendedResolver() public view {
        assertTrue(r.supportsInterface(0x9061b923));
    }

    function test_AdvertisesIERC165() public view {
        assertTrue(r.supportsInterface(0x01ffc9a7));
    }
}
