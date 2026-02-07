// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../DAIOBridge.sol";
import "../XMindAgentRegistry.sol";
import "../XMindProposer.sol";
import "../XMindTreasuryReceiver.sol";
import "./mocks/MockDAIOGovernance.sol";
import "./mocks/MockIDNFT.sol";

contract XmindTest is Test {
    DAIOBridge public bridge;
    XMindAgentRegistry public registry;
    XMindProposer public proposer;
    XMindTreasuryReceiver public receiver;

    MockDAIOGovernance public mockGov;
    MockIDNFT public mockIdNFT;
    address public mockFactory;
    address public mockKH = address(0xKh);

    function setUp() public {
        mockGov = new MockDAIOGovernance();
        bridge = new DAIOBridge(address(mockGov));

        mockIdNFT = new MockIDNFT();
        mockFactory = address(0xFa);
        registry = new XMindAgentRegistry(address(mockIdNFT), mockFactory);
        mockIdNFT.setMinter(address(registry), true);

        proposer = new XMindProposer(mockKH);
        receiver = new XMindTreasuryReceiver();
    }

    function test_DAIOBridge_getProposalCount() public view {
        assertEq(bridge.proposalCount(), 0);
    }

    function test_DAIOBridge_createProposal() public {
        uint256 id = bridge.createProposal(
            "Title",
            "Description",
            IDAIOGovernance.ProposalType.Generic,
            "mindx",
            address(0),
            ""
        );
        assertEq(id, 1);
        assertEq(bridge.proposalCount(), 1);
        (address proposerAddr,, IDAIOGovernance.ProposalStatus status,,) = bridge.getProposal(1);
        assertEq(proposerAddr, address(this));
        assertEq(uint256(status), uint256(IDAIOGovernance.ProposalStatus.Active));
    }

    function test_DAIOBridge_vote() public {
        bridge.createProposal("T", "D", IDAIOGovernance.ProposalType.Generic, "", address(0), "");
        bridge.vote(1, true);
        (, , , uint256 forVotes, uint256 againstVotes) = bridge.getProposal(1);
        assertEq(forVotes, 1);
        assertEq(againstVotes, 0);
    }

    function test_XMindAgentRegistry_registerAgent_withMint() public {
        vm.prank(registry.owner());
        uint256 tokenId = registry.registerAgent(
            address(0xA11),
            "type",
            "prompt",
            "persona",
            "",
            "uri",
            bytes32(uint256(1)),
            false
        );
        assertEq(tokenId, 1);
        (address agentAddr, uint256 idNFTId, uint256 registeredAt, bool active) = registry.agents(address(0xA11));
        assertEq(agentAddr, address(0xA11));
        assertEq(idNFTId, 1);
        assertTrue(active);
        assertEq(registry.getAgentCount(), 1);
    }

    function test_XMindAgentRegistry_registerAgent_onlyOwner() public {
        vm.prank(address(0xBad));
        vm.expectRevert();
        registry.registerAgent(address(0xA11), "t", "p", "p", "", "", bytes32(0), false);
    }

    function test_XMindProposer_requestProposal() public {
        vm.prank(proposer.owner());
        uint256 requestId = proposer.requestProposal("Do something");
        assertEq(requestId, 0);
        (string memory desc, uint256 requestedAt, bool fulfilled) = proposer.getRequest(0);
        assertEq(desc, "Do something");
        assertTrue(requestedAt > 0);
        assertFalse(fulfilled);
        assertEq(proposer.getRequestCount(), 1);
    }

    function test_XMindProposer_setFulfilled() public {
        vm.startPrank(proposer.owner());
        proposer.requestProposal("D");
        proposer.setFulfilled(0);
        vm.stopPrank();
        (, , bool fulfilled) = proposer.getRequest(0);
        assertTrue(fulfilled);
    }

    function test_XMindTreasuryReceiver_receiveAndWithdraw() public {
        address recipient = address(0xBee);
        uint256 amount = 1 ether;
        vm.deal(address(this), amount);
        (bool sent,) = address(receiver).call{value: amount}("");
        assertTrue(sent);
        assertEq(address(receiver).balance, amount);
        assertEq(receiver.balanceNative(), amount);

        vm.prank(receiver.owner());
        receiver.withdrawNative(payable(recipient), amount);
        assertEq(recipient.balance, amount);
        assertEq(address(receiver).balance, 0);
    }

    function test_XMindTreasuryReceiver_withdraw_onlyOwner() public {
        vm.deal(address(receiver), 1 ether);
        vm.prank(address(0xBad));
        vm.expectRevert();
        receiver.withdrawNative(payable(address(0xBee)), 1 ether);
    }
}
