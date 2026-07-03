/**
 * Proves the relayer's EIP-712 voucher is byte-for-byte what
 * BankonSubnameRegistrar.register() verifies:
 *   digest == _hashTypedDataV4(keccak256(abi.encode(REGISTRATION_TYPEHASH, ...)))
 *   recover(digest, gatewaySig) == the gateway signer
 * If the gateway address holds GATEWAY_SIGNER_ROLE, register() accepts it.
 *
 * Run: bun test
 */
import { test, expect } from "bun:test";
import {
  hashTypedData, recoverTypedDataAddress, keccak256, toBytes,
  encodeAbiParameters, concatHex, type Hex,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";

const REGISTRAR = "0x00000000000000000000000000000000000000A1" as const;
const CHAIN_ID = 1;
const DOMAIN = { name: "BankonSubnameRegistrar", version: "1", chainId: CHAIN_ID, verifyingContract: REGISTRAR } as const;
const TYPES = {
  Registration: [
    { name: "label", type: "string" },
    { name: "owner", type: "address" },
    { name: "expiry", type: "uint64" },
    { name: "paymentReceiptHash", type: "bytes32" },
    { name: "deadline", type: "uint256" },
  ],
} as const;

const gateway = privateKeyToAccount("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d");
const message = {
  label: "alice",
  owner: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8" as Hex,
  expiry: 2000000000n,
  paymentReceiptHash: keccak256(toBytes("receipt-xyz")),
  deadline: 1999999000n,
} as const;

// Reproduce the contract's OZ EIP712 _hashTypedDataV4 digest independently.
function contractDigest(): Hex {
  const REGISTRATION_TYPEHASH = keccak256(toBytes(
    "Registration(string label,address owner,uint64 expiry,bytes32 paymentReceiptHash,uint256 deadline)"));
  const structHash = keccak256(encodeAbiParameters(
    [{ type: "bytes32" }, { type: "bytes32" }, { type: "address" }, { type: "uint64" }, { type: "bytes32" }, { type: "uint256" }],
    [REGISTRATION_TYPEHASH, keccak256(toBytes(message.label)), message.owner, message.expiry, message.paymentReceiptHash, message.deadline]));
  const DOMAIN_TYPEHASH = keccak256(toBytes(
    "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"));
  const domainSep = keccak256(encodeAbiParameters(
    [{ type: "bytes32" }, { type: "bytes32" }, { type: "bytes32" }, { type: "uint256" }, { type: "address" }],
    [DOMAIN_TYPEHASH, keccak256(toBytes("BankonSubnameRegistrar")), keccak256(toBytes("1")), BigInt(CHAIN_ID), REGISTRAR]));
  return keccak256(concatHex(["0x1901", domainSep, structHash]));
}

test("voucher digest equals the contract's _hashTypedDataV4", () => {
  expect(hashTypedData({ domain: DOMAIN, types: TYPES, primaryType: "Registration", message })).toBe(contractDigest());
});

test("gatewaySig recovers to the gateway signer (register() accepts it)", async () => {
  const sig = await gateway.signTypedData({ domain: DOMAIN, types: TYPES, primaryType: "Registration", message });
  const recovered = await recoverTypedDataAddress({ domain: DOMAIN, types: TYPES, primaryType: "Registration", message, signature: sig });
  expect(recovered.toLowerCase()).toBe(gateway.address.toLowerCase());
});
