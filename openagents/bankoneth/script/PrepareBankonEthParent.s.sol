// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

/// @notice The ENS NameWrapper surface this script touches. Both calls are made
///         BY the bankon.eth NameWrapper owner (or an approved operator).
interface INameWrapper {
    /// Burn owner-controlled fuses on a name you own. CANNOT_UNWRAP (=1) is
    /// owner-controlled; burning it puts bankon.eth into the "Locked" state,
    /// which ENS requires before the registrar can emancipate (burn PCC on)
    /// child subnames. Requires PARENT_CANNOT_CONTROL already burned — true for
    /// any .eth 2LD, confirmed for bankon.eth.
    function setFuses(bytes32 node, uint16 ownerControlledFuses) external returns (uint32);
    /// Approve an operator (the registrar) to manage all of your wrapped names,
    /// so BankonSubnameRegistrar can setSubnodeRecord under bankon.eth.
    function setApprovalForAll(address operator, bool approved) external;
    function getData(uint256 id) external view returns (address owner, uint32 fuses, uint64 expiry);
    function isApprovedForAll(address owner, address operator) external view returns (bool);
    function allFusesBurned(bytes32 node, uint32 fuseMask) external view returns (bool);
}

/// @title  PrepareBankonEthParent
/// @notice The two on-chain prerequisites that let BankonSubnameRegistrar issue
///         subnames under bankon.eth — done via contract calls, in one broadcast:
///           1. LOCK    — NameWrapper.setFuses(bankonNode, CANNOT_UNWRAP)
///           2. APPROVE — NameWrapper.setApprovalForAll(registrar, true)
///
///         MUST be broadcast by the bankon.eth NameWrapper OWNER (verified live:
///         0x54165AdA93FA752cfec95F3f3bAE2676D3752A99 — the retired root addr,
///         NOT the addr-record 0x10f7Ee…D169). If that key is unavailable,
///         transfer the wrapped bankon.eth to the current OVERLORD first, then
///         run this from the new owner. A contract can also perform both calls
///         if it holds bankon.eth or is an approved operator — this script is
///         the owner-EOA path; point OWNER_PK at a Safe/AA wallet to batch.
///
///         Idempotent: skips a step already done.
///
///         Run:
///           NAME_WRAPPER=0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401 \
///           BANKON_ETH_NODE=0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a \
///           REGISTRAR_ADDR=0x… \
///           OWNER_PK=0x…  (bankon.eth owner) \
///           forge script script/PrepareBankonEthParent.s.sol --rpc-url $RPC --broadcast
contract PrepareBankonEthParent is Script {
    uint16 constant CANNOT_UNWRAP        = 1;
    uint32 constant PARENT_CANNOT_CONTROL = 0x10000;

    function run() external {
        INameWrapper nw = INameWrapper(vm.envAddress("NAME_WRAPPER"));
        bytes32 node    = vm.envBytes32("BANKON_ETH_NODE");
        address registrar = vm.envAddress("REGISTRAR_ADDR");
        uint256 pk      = vm.envUint("OWNER_PK");
        address me      = vm.addr(pk);

        (address owner, uint32 fuses,) = nw.getData(uint256(node));
        console.log("bankon.eth wrapped owner:", owner);
        console.log("broadcasting as:         ", me);
        require(owner == me, "OWNER_PK is not the bankon.eth NameWrapper owner (transfer the name or use the owner key)");
        require(nw.allFusesBurned(node, PARENT_CANNOT_CONTROL), "PARENT_CANNOT_CONTROL not burned — cannot burn owner fuses");

        vm.startBroadcast(pk);

        // 1) LOCK — burn CANNOT_UNWRAP so the parent can emancipate children.
        if (nw.allFusesBurned(node, CANNOT_UNWRAP)) {
            console.log("[skip] already Locked (CANNOT_UNWRAP burned)");
        } else {
            nw.setFuses(node, CANNOT_UNWRAP);
            console.log("[done] Locked bankon.eth (CANNOT_UNWRAP burned)");
        }

        // 2) APPROVE — let the registrar setSubnodeRecord under bankon.eth.
        if (nw.isApprovedForAll(me, registrar)) {
            console.log("[skip] registrar already approved");
        } else {
            nw.setApprovalForAll(registrar, true);
            console.log("[done] approved registrar as operator:", registrar);
        }

        vm.stopBroadcast();

        // read-back
        (, fuses,) = nw.getData(uint256(node));
        console.log("final fuses:", fuses);
        require(nw.allFusesBurned(node, CANNOT_UNWRAP), "lock failed");
        require(nw.isApprovedForAll(me, registrar), "approval failed");
        console.log("bankon.eth is ready: Locked + registrar approved.");
    }
}
