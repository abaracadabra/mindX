// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/IDNFT.sol";
import "../src/SoulBadger.sol";

contract IDNFTTest is Test {
    IDNFT public idnft;
    SoulBadger public soulBadger;
    address public governance;
    address public agent1;
    address public agent2;

    function setUp() public {
        governance = address(this);
        agent1 = makeAddr("agent1");
        agent2 = makeAddr("agent2");

        soulBadger = new SoulBadger("Test Soul", "TSOUL", "https://test.io/");
        idnft = new IDNFT();
        idnft.setSoulBadger(address(soulBadger));

        // Grant MINTER_ROLE to IDNFT on SoulBadger
        soulBadger.grantRole(soulBadger.MINTER_ROLE(), address(idnft));
    }

    function test_MintAgentIdentity() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "MastermindAgent",
            "You are a strategic planning agent",
            '{"traits": ["analytical", "strategic"]}',
            "ipfs://metadata",
            false
        );

        assertEq(idnft.ownerOf(tokenId), agent1);

        IDNFT.AgentIdentity memory identity = idnft.getAgentIdentity(tokenId);
        assertEq(identity.primaryWallet, agent1);
        assertEq(keccak256(bytes(identity.agentType)), keccak256(bytes("MastermindAgent")));
        assertTrue(identity.isActive);
        assertFalse(identity.isSoulbound);
    }

    function test_MintSoulboundIdentity() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "GuardianAgent",
            "You protect the system",
            '{"traits": ["vigilant"]}',
            "ipfs://guardian",
            true
        );

        IDNFT.AgentIdentity memory identity = idnft.getAgentIdentity(tokenId);
        assertTrue(identity.isSoulbound);
    }

    function test_SoulboundCannotTransfer() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "TestAgent",
            "Test",
            "{}",
            "ipfs://test",
            true
        );

        vm.prank(agent1);
        vm.expectRevert("Transfer blocked: soulbound identity");
        idnft.transferFrom(agent1, agent2, tokenId);
    }

    function test_AttachTHOT() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "THOTAgent",
            "THOT enabled",
            "{}",
            "ipfs://thot",
            false
        );

        bytes32 thotCID = keccak256("thot_tensor_data");

        bool success = idnft.attachTHOT(tokenId, thotCID, 8, 4); // THOT_8D
        assertTrue(success);

        IDNFT.THOTAttachment[] memory attachments = idnft.getTHOTAttachments(tokenId);
        assertEq(attachments.length, 1);
        assertEq(attachments[0].thotCID, thotCID);
        assertEq(attachments[0].dimensions, 8);
    }

    function test_AttachMultipleTHOTs() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "MultiTHOT",
            "Multi THOT",
            "{}",
            "ipfs://multi",
            false
        );

        idnft.attachTHOT(tokenId, keccak256("thot1"), 8, 2);   // THOT_8D
        idnft.attachTHOT(tokenId, keccak256("thot2"), 64, 4);  // THOT_512
        idnft.attachTHOT(tokenId, keccak256("thot3"), 128, 8); // THOT_768

        IDNFT.THOTAttachment[] memory attachments = idnft.getTHOTAttachments(tokenId);
        assertEq(attachments.length, 3);
    }

    function test_AttachModelDataset() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "ModelAgent",
            "Has model",
            "{}",
            "ipfs://model",
            false
        );

        bytes32 datasetCID = keccak256("model_weights");
        idnft.attachModelDataset(tokenId, datasetCID, "transformer-768");

        IDNFT.ModelDataset memory dataset = idnft.getModelDataset(tokenId);
        assertEq(dataset.datasetCID, datasetCID);
        assertTrue(dataset.verified);
    }

    function test_UpdatePersona() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "EvolvingAgent",
            "Initial prompt",
            '{"version": 1}',
            "ipfs://evolving",
            false
        );

        vm.prank(agent1);
        idnft.updatePersona(tokenId, "Updated prompt", '{"version": 2}');

        IDNFT.AgentIdentity memory identity = idnft.getAgentIdentity(tokenId);
        assertEq(keccak256(bytes(identity.prompt)), keccak256(bytes("Updated prompt")));
    }

    function test_IssueCredential() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "CredentialAgent",
            "Has credentials",
            "{}",
            "ipfs://cred",
            false
        );

        idnft.issueCredential(
            tokenId,
            "VERIFIED_AGENT",
            365 days,
            abi.encode("verification_data"),
            bytes("issuer_sig")
        );

        bytes32[] memory creds = idnft.getAgentCredentials(tokenId);
        assertEq(creds.length, 1);

        (bool valid, string memory credType) = idnft.verifyCredential(tokenId, creds[0]);
        assertTrue(valid);
        assertEq(keccak256(bytes(credType)), keccak256(bytes("VERIFIED_AGENT")));
    }

    function test_UpdateTrustScore() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "TrustAgent",
            "Tracking trust",
            "{}",
            "ipfs://trust",
            false
        );

        IDNFT.AgentIdentity memory before = idnft.getAgentIdentity(tokenId);
        assertEq(before.trustScore, 5000); // Initial score

        idnft.updateTrustScore(tokenId, 8500);

        IDNFT.AgentIdentity memory after_ = idnft.getAgentIdentity(tokenId);
        assertEq(after_.trustScore, 8500);
    }

    function test_GetTokenIdByWallet() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "FindableAgent",
            "Can be found",
            "{}",
            "ipfs://find",
            false
        );

        uint256 foundId = idnft.getTokenIdByWallet(agent1);
        assertEq(foundId, tokenId);
    }

    function test_EnableSoulbound() public {
        uint256 tokenId = idnft.mintAgentIdentity(
            agent1,
            "ConvertAgent",
            "Will become soulbound",
            "{}",
            "ipfs://convert",
            false
        );

        assertFalse(idnft.isSoulbound(tokenId));

        vm.prank(agent1);
        idnft.enableSoulbound(tokenId);

        assertTrue(idnft.isSoulbound(tokenId));
    }
}
