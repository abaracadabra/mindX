// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

import {MarketingAttributionReceipt} from "../MarketingAttributionReceipt.sol";
import {ITessera}                    from "../interfaces/ITessera.sol";
import {ICensura}                    from "../interfaces/ICensura.sol";

/// @dev Mocks. The ConclaveTest mocks in openagents/conclave/contracts/test/Conclave.t.sol
///      use the same shape; we duplicate locally to keep this profile compile-isolated.
contract MockTessera is ITessera {
    mapping(address => bool) public valid;
    function setValid(address h, bool v) external { valid[h] = v; }
    function hasValidCredential(address h) external view returns (bool) { return valid[h]; }
    function didOf(address) external pure returns (string memory) { return ""; }
    function transportKeyOf(address) external pure returns (bytes32) { return bytes32(0); }
}

contract MockCensura is ICensura {
    mapping(address => uint8) public scoreOf;
    function setScore(address s, uint8 v) external { scoreOf[s] = v; }
    function score(address s) external view returns (uint8) { return scoreOf[s]; }
    function report(address, bytes32) external pure {}
}

contract MarketingAttributionReceiptTest is Test {
    MarketingAttributionReceipt internal receipts;
    MockTessera internal tessera;
    MockCensura internal censura;

    address internal admin = address(0xA0);
    uint256 internal agentPk = 0xA11CE;
    address internal agent;
    uint8   internal constant FLOOR = 50;

    bytes32 internal constant CAMPAIGN_ID         = keccak256("camp-1");
    bytes32 internal constant BRIEF_CID           = keccak256("brief-1");
    bytes32 internal constant AUDIENCE_HASH       = keccak256("ABCD");
    uint32  internal constant CHANNEL_MASK        = 0x07;
    uint128 internal constant SPEND_USD_MICRO     = 250_000_000;
    bytes32 internal constant OUTCOME_CID         = keccak256("kpi-1");
    bytes32 internal constant BOARDROOM_SESSION_A = keccak256("br_session_A");
    bytes32 internal constant BOARDROOM_SESSION_B = keccak256("br_session_B");
    bytes32 internal constant TRACE_ID            = keccak256("trace-1");

    function setUp() public {
        agent = vm.addr(agentPk);
        tessera = new MockTessera();
        censura = new MockCensura();
        tessera.setValid(agent, true);
        censura.setScore(agent, FLOOR + 10);

        receipts = new MarketingAttributionReceipt(admin, tessera, censura, FLOOR);
    }

    // ── Helpers ──────────────────────────────────────────────────────

    function _sign(
        uint256 pk,
        bytes32 campaignId,
        bytes32 briefCid,
        bytes32 audienceHash,
        uint32  channelMask,
        uint128 spend,
        bytes32 outcomeCid,
        bytes32 boardroomSessionId,
        bytes32 traceId,
        uint64  nonce,
        uint64  signedAt
    ) internal view returns (bytes memory) {
        bytes32 digest = receipts.envelopeDigest(
            campaignId, briefCid, audienceHash, channelMask, spend, outcomeCid,
            boardroomSessionId, traceId, nonce, signedAt
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _record(uint64 nonce, uint64 signedAt, bytes32 sessionId) internal {
        bytes memory sig = _sign(
            agentPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, sessionId, TRACE_ID, nonce, signedAt
        );
        receipts.record(
            agent,
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, sessionId, TRACE_ID,
            nonce, signedAt, sig
        );
    }

    // ── Happy path ───────────────────────────────────────────────────

    function test_record_succeeds_with_valid_signature() public {
        _record(0, uint64(block.timestamp), BOARDROOM_SESSION_A);
        assertEq(receipts.nonces(agent, CAMPAIGN_ID), 1, "nonce must increment to 1");
    }

    function test_record_increments_nonce_per_campaign() public {
        _record(0, uint64(block.timestamp), BOARDROOM_SESSION_A);
        _record(1, uint64(block.timestamp), BOARDROOM_SESSION_A);
        assertEq(receipts.nonces(agent, CAMPAIGN_ID), 2);
    }

    function test_record_emits_boardroom_session_in_event() public {
        vm.recordLogs();
        _record(0, uint64(block.timestamp), BOARDROOM_SESSION_A);
        Vm.Log[] memory entries = vm.getRecordedLogs();
        assertGt(entries.length, 0, "no logs emitted");
        // topic[0] = event sig; topic[1] = campaignId; topic[2] = agent; topic[3] = boardroomSessionId
        bool found;
        for (uint256 i = 0; i < entries.length; i++) {
            if (entries[i].topics.length >= 4 && entries[i].topics[1] == CAMPAIGN_ID) {
                assertEq(entries[i].topics[3], BOARDROOM_SESSION_A, "boardroomSessionId must be indexed");
                found = true;
                break;
            }
        }
        assertTrue(found, "AttributionReceiptRecorded with campaignId not found");
    }

    // ── Replay protection — load-bearing ─────────────────────────────

    function test_record_reverts_on_nonce_replay() public {
        _record(0, uint64(block.timestamp), BOARDROOM_SESSION_A);
        bytes memory sig = _sign(
            agentPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp)
        );
        vm.expectRevert(abi.encodeWithSelector(
            MarketingAttributionReceipt.InvalidNonce.selector, agent, CAMPAIGN_ID, uint64(1), uint64(0)
        ));
        receipts.record(
            agent,
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
    }

    function test_record_reverts_on_skipped_nonce() public {
        bytes memory sig = _sign(
            agentPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 5, uint64(block.timestamp)
        );
        vm.expectRevert(abi.encodeWithSelector(
            MarketingAttributionReceipt.InvalidNonce.selector, agent, CAMPAIGN_ID, uint64(0), uint64(5)
        ));
        receipts.record(
            agent,
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 5, uint64(block.timestamp), sig
        );
    }

    // ── Identity + reputation gating ─────────────────────────────────

    function test_record_reverts_when_tessera_invalid() public {
        tessera.setValid(agent, false);
        bytes memory sig = _sign(
            agentPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp)
        );
        vm.expectRevert(abi.encodeWithSelector(
            MarketingAttributionReceipt.AgentMissingTessera.selector, agent
        ));
        receipts.record(
            agent,
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
    }

    function test_record_reverts_when_agent_faded() public {
        censura.setScore(agent, FLOOR - 1);
        bytes memory sig = _sign(
            agentPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp)
        );
        vm.expectRevert(abi.encodeWithSelector(
            MarketingAttributionReceipt.AgentFaded.selector, agent, uint8(FLOOR - 1), FLOOR
        ));
        receipts.record(
            agent,
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
    }

    function test_record_reverts_on_zero_agent() public {
        bytes memory sig = _sign(
            agentPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp)
        );
        vm.expectRevert(MarketingAttributionReceipt.ZeroAgent.selector);
        receipts.record(
            address(0),
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
    }

    function test_record_reverts_on_signature_from_wrong_key() public {
        uint256 wrongPk = 0xB0B;
        bytes memory sig = _sign(
            wrongPk, CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp)
        );
        address wrongAddr = vm.addr(wrongPk);
        vm.expectRevert(abi.encodeWithSelector(
            MarketingAttributionReceipt.InvalidSignature.selector, wrongAddr, agent
        ));
        receipts.record(
            agent,
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
    }

    // ── Fuzz: replay protection invariants ───────────────────────────

    /// @dev With --fuzz-runs 50000 we get confident that no two valid signatures
    ///      exist for the same (agent, campaignId, nonce) tuple — a different nonce
    ///      always changes the digest.
    function testFuzz_distinct_nonce_yields_distinct_digest(
        uint64 nonceA, uint64 nonceB, uint64 signedAt
    ) public view {
        vm.assume(nonceA != nonceB);
        bytes32 dA = receipts.envelopeDigest(
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, nonceA, signedAt
        );
        bytes32 dB = receipts.envelopeDigest(
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, nonceB, signedAt
        );
        assertTrue(dA != dB, "nonce must enter the digest");
    }

    /// @dev Different boardroomSessionId must change the digest. Without this
    ///      property a campaign approved in session X could be mis-attributed
    ///      to session Y by a relayer.
    function testFuzz_distinct_session_yields_distinct_digest(
        bytes32 sessionA, bytes32 sessionB, uint64 nonce, uint64 signedAt
    ) public view {
        vm.assume(sessionA != sessionB);
        bytes32 dA = receipts.envelopeDigest(
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, sessionA, TRACE_ID, nonce, signedAt
        );
        bytes32 dB = receipts.envelopeDigest(
            CAMPAIGN_ID, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            SPEND_USD_MICRO, OUTCOME_CID, sessionB, TRACE_ID, nonce, signedAt
        );
        assertTrue(dA != dB, "boardroomSessionId must enter the digest");
    }

    function testFuzz_record_then_replay_always_reverts(uint128 spend) public {
        bytes32 cid = keccak256(abi.encode("camp", spend));
        bytes memory sig = _sign(
            agentPk, cid, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            spend, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp)
        );
        receipts.record(
            agent, cid, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            spend, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
        vm.expectRevert(abi.encodeWithSelector(
            MarketingAttributionReceipt.InvalidNonce.selector, agent, cid, uint64(1), uint64(0)
        ));
        receipts.record(
            agent, cid, BRIEF_CID, AUDIENCE_HASH, CHANNEL_MASK,
            spend, OUTCOME_CID, BOARDROOM_SESSION_A, TRACE_ID, 0, uint64(block.timestamp), sig
        );
    }

    // ── Admin role ───────────────────────────────────────────────────

    function test_admin_can_update_floor_and_addresses() public {
        vm.startPrank(admin);
        receipts.setCensuraFloor(99);
        assertEq(receipts.censuraFloor(), 99);
        MockTessera t2 = new MockTessera();
        receipts.setTessera(t2);
        assertEq(address(receipts.tessera()), address(t2));
        vm.stopPrank();
    }

    function test_non_admin_cannot_update_floor() public {
        address nobody = address(0xDEAD);
        vm.prank(nobody);
        vm.expectRevert();
        receipts.setCensuraFloor(0);
    }
}

