// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/SoulBadger.sol";

contract SoulBadgerTest is Test {
    SoulBadger public soulBadger;
    address public admin;
    address public user1;
    address public user2;

    function setUp() public {
        admin = address(this);
        user1 = makeAddr("user1");
        user2 = makeAddr("user2");

        soulBadger = new SoulBadger(
            "Test Soul Badger",
            "TSOUL",
            "https://test.io/soul/"
        );
    }

    function test_MintSoulboundBadge() public {
        bytes32 badgeType = keccak256("AGENT_BADGE");

        uint256 badgeId = soulBadger.mintSoulboundBadge(
            user1,
            badgeType,
            0, // Never expires
            SoulBadger.BurnAuth.Neither,
            "ipfs://test"
        );

        assertEq(soulBadger.ownerOf(badgeId), user1);
        assertTrue(soulBadger.isBadgeValid(badgeId));
    }

    function test_SoulboundCannotTransfer() public {
        bytes32 badgeType = keccak256("AGENT_BADGE");

        uint256 badgeId = soulBadger.mintSoulboundBadge(
            user1,
            badgeType,
            0,
            SoulBadger.BurnAuth.Neither,
            "ipfs://test"
        );

        vm.prank(user1);
        vm.expectRevert(SoulBadger.TransferNotAllowed.selector);
        soulBadger.transferFrom(user1, user2, badgeId);
    }

    function test_MintAgentCredentialBadge() public {
        bytes32 badgeType = keccak256("AGENT_CREDENTIAL");
        bytes32 domainHash = keccak256("AI");

        uint256 badgeId = soulBadger.mintAgentCredentialBadge(
            user1,
            badgeType,
            "MastermindAgent",
            8000, // Trust level
            75,   // Knowledge level
            domainHash,
            "ipfs://credential"
        );

        SoulBadger.AgentCredentials memory creds = soulBadger.getCredentials(badgeId);
        assertEq(creds.trustLevel, 8000);
        assertEq(creds.knowledgeLevel, 75);
        assertTrue(creds.verified);
    }

    function test_UpdateCredentials() public {
        bytes32 badgeType = keccak256("AGENT_CREDENTIAL");

        uint256 badgeId = soulBadger.mintAgentCredentialBadge(
            user1,
            badgeType,
            "TestAgent",
            5000,
            50,
            bytes32(0),
            "ipfs://test"
        );

        soulBadger.updateCredentials(badgeId, 9000, 90);

        SoulBadger.AgentCredentials memory creds = soulBadger.getCredentials(badgeId);
        assertEq(creds.trustLevel, 9000);
        assertEq(creds.knowledgeLevel, 90);
    }

    function test_BadgeExpiration() public {
        bytes32 badgeType = keccak256("TEMP_BADGE");

        uint256 badgeId = soulBadger.mintSoulboundBadge(
            user1,
            badgeType,
            uint40(block.timestamp + 1 hours),
            SoulBadger.BurnAuth.IssuerOnly,
            "ipfs://temp"
        );

        assertFalse(soulBadger.isBadgeExpired(badgeId));

        // Fast forward
        vm.warp(block.timestamp + 2 hours);

        assertTrue(soulBadger.isBadgeExpired(badgeId));
        assertFalse(soulBadger.isBadgeValid(badgeId));
    }

    function test_RevokeBadge_IssuerOnly() public {
        bytes32 badgeType = keccak256("REVOKABLE");

        uint256 badgeId = soulBadger.mintSoulboundBadge(
            user1,
            badgeType,
            0,
            SoulBadger.BurnAuth.IssuerOnly,
            "ipfs://revokable"
        );

        // Owner cannot revoke
        vm.prank(user1);
        vm.expectRevert("Not authorized to revoke");
        soulBadger.revokeBadge(badgeId, "Trying to revoke");

        // Admin/Issuer can revoke
        soulBadger.revokeBadge(badgeId, "Admin revocation");
        assertFalse(soulBadger.isBadgeValid(badgeId));
    }

    function test_GetBadgesForAddress() public {
        bytes32 badgeType = keccak256("MULTI_BADGE");

        soulBadger.mintSoulboundBadge(user1, badgeType, 0, SoulBadger.BurnAuth.Neither, "1");
        soulBadger.mintSoulboundBadge(user1, badgeType, 0, SoulBadger.BurnAuth.Neither, "2");
        soulBadger.mintSoulboundBadge(user1, badgeType, 0, SoulBadger.BurnAuth.Neither, "3");

        uint256[] memory badges = soulBadger.getBadgesForAddress(user1);
        assertEq(badges.length, 3);
    }
}
