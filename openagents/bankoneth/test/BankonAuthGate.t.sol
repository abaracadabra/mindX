// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";

import {BankonAuthGate, IAuthGateResolver} from "../contracts/identity/BankonAuthGate.sol";
import {INameWrapper}                       from "../contracts/interfaces/IBankon.sol";
import {MockNameWrapper}                    from "./mocks/MockNameWrapper.sol";

/// @dev Minimal text-record-returning resolver stub for mode-2 tests.
contract StubResolver is IAuthGateResolver {
    mapping(bytes32 => mapping(string => string)) public records;

    function setText(bytes32 node, string calldata key, string calldata value) external {
        records[node][key] = value;
    }

    function text(bytes32 node, string calldata key) external view override returns (string memory) {
        return records[node][key];
    }
}

abstract contract AuthHarness is Test {
    BankonAuthGate    gate;
    MockNameWrapper   nw;
    StubResolver      resolver;

    bytes32 constant ETH_NODE      = keccak256(abi.encodePacked(bytes32(0), keccak256("eth")));
    bytes32 constant BANKON_ETH    = keccak256(abi.encodePacked(ETH_NODE, keccak256("bankon")));
    bytes32 constant ALICE_NODE    = keccak256(abi.encodePacked(BANKON_ETH, keccak256("alice")));

    uint256 aliceSk;
    address alice;

    function setUp() public virtual {
        nw       = new MockNameWrapper();
        resolver = new StubResolver();
        gate     = new BankonAuthGate(INameWrapper(address(nw)), BANKON_ETH);

        aliceSk = uint256(keccak256("alice-key"));
        alice   = vm.addr(aliceSk);

        // Mint alice.bankon.eth to alice via the mock wrapper.
        nw.adminSetParent(ALICE_NODE, alice, 0, type(uint64).max);
    }

    /// @dev EIP-191 personal_sign over a string. Mirrors what wallets do.
    function _signSiwe(uint256 sk, string memory msg_) internal pure returns (bytes memory) {
        bytes32 digest = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n", _utoa(bytes(msg_).length), msg_)
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(sk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _utoa(uint256 v) internal pure returns (string memory) {
        if (v == 0) return "0";
        uint256 j = v;
        uint256 len;
        while (j != 0) { len++; j /= 10; }
        bytes memory b = new bytes(len);
        uint256 k = len;
        while (v != 0) { b[--k] = bytes1(uint8(48 + v % 10)); v /= 10; }
        return string(b);
    }
}

// ── Mode 1: NameWrapper ownership ─────────────────────────────────

contract AuthGateOwnsLabelTest is AuthHarness {
    string constant MSG = "bankon.eth wants you to sign in with your Ethereum account";

    function test_VerifyOwnsLabel_happyPath() public {
        bytes memory sig = _signSiwe(aliceSk, MSG);
        assertTrue(gate.verifyOwnsLabel(MSG, sig, "alice"));
    }

    function test_VerifyOwnsLabel_wrongSigner_false() public {
        uint256 mallorySk = uint256(keccak256("mallory-key"));
        bytes memory sig  = _signSiwe(mallorySk, MSG);
        assertFalse(gate.verifyOwnsLabel(MSG, sig, "alice"));
    }

    function test_VerifyOwnsLabel_wrongLabel_false() public {
        bytes memory sig = _signSiwe(aliceSk, MSG);
        // bob.bankon.eth doesn't exist in the mock — ownerOf returns address(0)
        assertFalse(gate.verifyOwnsLabel(MSG, sig, "bob"));
    }

    function test_VerifyOwnsLabel_emptyLabel_reverts() public {
        bytes memory sig = _signSiwe(aliceSk, MSG);
        vm.expectRevert(BankonAuthGate.LabelEmpty.selector);
        gate.verifyOwnsLabel(MSG, sig, "");
    }

    function test_VerifyOwnsLabelDigest_acceptsDirectDigest() public {
        bytes32 digest = keccak256("custom typed-data digest");
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(aliceSk, digest);
        bytes memory sig = abi.encodePacked(r, s, v);
        assertTrue(gate.verifyOwnsLabelDigest(digest, sig, "alice"));
    }
}

// ── Mode 2: Resolver text-record claim ─────────────────────────────

contract AuthGateTextClaimTest is AuthHarness {
    string constant MSG = "Sign in to access AgenticPlace as the holder";
    string constant KEY = "authz.signer";

    function _setAliceClaim() internal {
        // Resolver text record set to alice's lowercased hex address.
        // Format: "0xabcd…" (40 hex chars after 0x).
        bytes memory addrBytes = abi.encodePacked(alice);
        bytes memory hex_ = new bytes(42);
        hex_[0] = "0"; hex_[1] = "x";
        bytes memory alphabet = "0123456789abcdef";
        for (uint256 i = 0; i < 20; ++i) {
            uint8 b = uint8(addrBytes[i]);
            hex_[2 + 2 * i]     = alphabet[b >> 4];
            hex_[2 + 2 * i + 1] = alphabet[b & 0x0f];
        }
        resolver.setText(ALICE_NODE, KEY, string(hex_));
    }

    function test_VerifyTextClaim_happyPath() public {
        _setAliceClaim();
        bytes memory sig = _signSiwe(aliceSk, MSG);
        assertTrue(gate.verifyTextClaim(MSG, sig, resolver, ALICE_NODE, KEY));
    }

    function test_VerifyTextClaim_wrongSigner_false() public {
        _setAliceClaim();
        uint256 mallorySk = uint256(keccak256("mallory-key-2"));
        bytes memory sig  = _signSiwe(mallorySk, MSG);
        assertFalse(gate.verifyTextClaim(MSG, sig, resolver, ALICE_NODE, KEY));
    }

    function test_VerifyTextClaim_emptyRecord_false() public {
        // No claim set.
        bytes memory sig = _signSiwe(aliceSk, MSG);
        assertFalse(gate.verifyTextClaim(MSG, sig, resolver, ALICE_NODE, KEY));
    }

    function test_VerifyTextClaim_caseInsensitive() public {
        // Manually uppercase the resolver text to confirm case-insensitive match.
        _setAliceClaim();
        string memory original = resolver.text(ALICE_NODE, KEY);
        bytes memory orig = bytes(original);
        for (uint256 i = 2; i < orig.length; ++i) {
            if (orig[i] >= 0x61 && orig[i] <= 0x66) {       // a..f
                orig[i] = bytes1(uint8(orig[i]) - 32);      // → A..F
            }
        }
        resolver.setText(ALICE_NODE, KEY, string(orig));
        bytes memory sig = _signSiwe(aliceSk, MSG);
        assertTrue(gate.verifyTextClaim(MSG, sig, resolver, ALICE_NODE, KEY));
    }
}
