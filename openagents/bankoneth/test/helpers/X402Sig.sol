// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Vm} from "forge-std/Vm.sol";
import {IBankonX402Attestor} from "../../contracts/interfaces/IBankonExtensions.sol";

/// @notice Shared EIP-712 receipt signer for x402 rail tests. Lifts the
///         signing dance out of individual test contracts so the IR
///         optimizer doesn't have to inline it into every test function
///         (Yul stack pressure killer).
library X402Sig {
    bytes32 internal constant TYPEHASH =
        keccak256("X402Receipt(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt)");
    bytes32 internal constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    function sign(
        Vm vm,
        uint256 facilitatorPk,
        address attestor,
        IBankonX402Attestor.X402Receipt memory r
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(TYPEHASH, r.receiptHash, r.claimant, r.usd6, r.nonce, r.expiresAt));
        bytes32 domain = keccak256(
            abi.encode(DOMAIN_TYPEHASH, keccak256("BankonX402Attestor"), keccak256("1"), block.chainid, attestor)
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 rr, bytes32 ss) = vm.sign(facilitatorPk, digest);
        return abi.encodePacked(rr, ss, v);
    }
}
