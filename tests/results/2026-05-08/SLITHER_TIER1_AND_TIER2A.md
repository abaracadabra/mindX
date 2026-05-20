# Slither — Tier-1 contracts + Tier-2A refactor pass

Generated: 2026-05-08
Slither: 0.11.5
Workspace: `/home/hacker/mindX/daio/contracts`

## Scope

- **Tier-1** (5 production-grade contracts): `iNFT_7857`, `BankonSubnameRegistrar`, `AgentRegistry`, `THOT_v1`, `X402Receipt`.
- **Tier-2A** (4 refactored DAIO governance contracts where 8 unsafe `.transfer()` calls were replaced with `.call{value:}()`): `BoardroomExtension`, `Treasury`, `TreasuryFeeCollector`, `ProposalStakingManager`.

Run with: `--exclude-informational --exclude-low` (production-relevant findings only).

## Tier-1 — production deploy targets

### `inft/iNFT_7857.sol`

```
	- iNFT_7857._update(address,uint256,address) (inft/iNFT_7857.sol#607-620)
	- _safeMint(to,childId) (inft/iNFT_7857.sol#418)
		- _owners[tokenId] = to (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#240)
	ERC721._owners (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#28) can be used in cross function reentrancies:
	- ERC721._ownerOf(uint256) (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#146-148)
	- ERC721._update(address,uint256,address) (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#216-245)
	- _safeMint(to,childId) (inft/iNFT_7857.sol#418)
		- _tokenApprovals[tokenId] = to (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#398)
	ERC721._tokenApprovals (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#32) can be used in cross function reentrancies:
	- ERC721._approve(address,uint256,address,bool) (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#383-399)
	- ERC721._getApproved(uint256) (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#153-155)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities-1
INFO:Detectors:
Detector: reentrancy-no-eth
Reentrancy in iNFT_7857.mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string) (inft/iNFT_7857.sol#254-307):
	External calls:
	- _safeMint(to,tokenId) (inft/iNFT_7857.sol#300)
		- ERC721Utils.checkOnERC721Received(_msgSender(),address(0),to,tokenId,data) (lib/openzeppelin-contracts/contracts/token/ERC721/ERC721.sol#289)
		- retval = IERC721Receiver(to).onERC721Received(operator,from,tokenId,data) (lib/openzeppelin-contracts/contracts/token/ERC721/utils/ERC721Utils.sol#33-47)
	State variables written after the call(s):
	- _gateOpen = false (inft/iNFT_7857.sol#301)
	iNFT_7857._gateOpen (inft/iNFT_7857.sol#158) can be used in cross function reentrancies:
	- iNFT_7857._update(address,uint256,address) (inft/iNFT_7857.sol#607-620)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities-2
INFO:Slither:inft/iNFT_7857.sol analyzed (34 contracts with 63 detectors), 3 result(s) found
```

### `ens/v1/BankonSubnameRegistrar.sol`

```
'forge clean' running (wd: /home/hacker/mindX/daio/contracts)
'forge config --json' running
'forge build --build-info ens/v1/BankonSubnameRegistrar.sol' running (wd: /home/hacker/mindX/daio/contracts)
INFO:Detectors:
Detector: unused-return
BankonSubnameRegistrar._capExpiry(uint64) (ens/v1/BankonSubnameRegistrar.sol#349-356) ignores return value by (None,None,parentExpiry) = nameWrapper.getData(uint256(parentNode)) (ens/v1/BankonSubnameRegistrar.sol#351)
BankonSubnameRegistrar._writeAndTransfer(string,address,uint64,AgentMetadata) (ens/v1/BankonSubnameRegistrar.sol#360-382) ignores return value by nameWrapper.setSubnodeOwner(parentNode,label,address(this),0,expiry) (ens/v1/BankonSubnameRegistrar.sol#367)
BankonSubnameRegistrar._writeAndTransfer(string,address,uint64,AgentMetadata) (ens/v1/BankonSubnameRegistrar.sol#360-382) ignores return value by nameWrapper.setSubnodeRecord(parentNode,label,owner,address(defaultResolver),0,DEFAULT_FUSES,expiry) (ens/v1/BankonSubnameRegistrar.sol#374-378)
BankonSubnameRegistrar._writeAgentRecords(bytes32,address,AgentMetadata) (ens/v1/BankonSubnameRegistrar.sol#384-435) ignores return value by defaultResolver.multicall(calls) (ens/v1/BankonSubnameRegistrar.sol#434)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#unused-return
INFO:Slither:ens/v1/BankonSubnameRegistrar.sol analyzed (28 contracts with 63 detectors), 4 result(s) found
```

### `agentregistry/AgentRegistry.sol`

```
'forge clean' running (wd: /home/hacker/mindX/daio/contracts)
'forge config --json' running
'forge build --build-info agentregistry/AgentRegistry.sol' running (wd: /home/hacker/mindX/daio/contracts)
INFO:Slither:agentregistry/AgentRegistry.sol analyzed (29 contracts with 63 detectors), 0 result(s) found
```

### `THOT/v1/THOT.sol`

```
'forge clean' running (wd: /home/hacker/mindX/daio/contracts)
'forge config --json' running
'forge build --build-info THOT/v1/THOT.sol' running (wd: /home/hacker/mindX/daio/contracts)
INFO:Slither:THOT/v1/THOT.sol analyzed (22 contracts with 63 detectors), 0 result(s) found
```

### `x402/X402Receipt.sol`

```
'forge clean' running (wd: /home/hacker/mindX/daio/contracts)
'forge config --json' running
'forge build --build-info x402/X402Receipt.sol' running (wd: /home/hacker/mindX/daio/contracts)
INFO:Slither:x402/X402Receipt.sol analyzed (23 contracts with 63 detectors), 0 result(s) found
```

## Tier-2A — refactored DAIO governance contracts

### `daio/BoardroomExtension.sol`

```
	- Treasury.createAllocation(uint256,string,address,uint256,address) (daio/treasury/Treasury.sol#172-210)
	- Treasury.getTreasuryBalance(string,address) (daio/treasury/Treasury.sol#279-288)
	- Treasury.getTreasuryStats(string) (daio/treasury/Treasury.sol#293-308)
	- Treasury.projectTreasuries (daio/treasury/Treasury.sol#33)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities-1
INFO:Detectors:
Detector: unused-return
BoardroomExtension.executeAllocation(uint256) (daio/BoardroomExtension.sol#103-126) ignores return value by (None,None,status,None,None) = daioGovernance.getProposal(proposalId) (daio/BoardroomExtension.sol#106)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#unused-return
INFO:Detectors:
Detector: constable-states
Treasury.requiredSignatures (daio/treasury/Treasury.sol#48) should be constant 
Treasury.totalSigners (daio/treasury/Treasury.sol#49) should be constant 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-constant
INFO:Detectors:
Detector: immutable-states
BoardroomExtension.daioGovernance (daio/BoardroomExtension.sol#14) should be immutable 
BoardroomExtension.owner (daio/BoardroomExtension.sol#33) should be immutable 
DAIOGovernance.constitution (daio/DAIOGovernance.sol#68) should be immutable 
DAIOGovernance.owner (daio/DAIOGovernance.sol#71) should be immutable 
DAIOGovernance.settings (daio/DAIOGovernance.sol#67) should be immutable 
DAIOGovernance.treasury (daio/DAIOGovernance.sol#69) should be immutable 
Treasury.constitution (daio/treasury/Treasury.sol#21) should be immutable 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-immutable
INFO:Slither:daio/BoardroomExtension.sol analyzed (14 contracts with 63 detectors), 11 result(s) found
```

### `daio/treasury/Treasury.sol`

```
'forge config --json' running
'forge build --build-info daio/treasury/Treasury.sol' running (wd: /home/hacker/mindX/daio/contracts)
INFO:Detectors:
Detector: reentrancy-eth
Reentrancy in Treasury.distributeReward(string,address,uint256,address,string) (daio/treasury/Treasury.sol#248-274):
	External calls:
	- (ok,None) = address(recipient).call{value: amount}() (daio/treasury/Treasury.sol#263)
	State variables written after the call(s):
	- treasury.totalDistributed += amount (daio/treasury/Treasury.sol#271)
	Treasury.projectTreasuries (daio/treasury/Treasury.sol#33) can be used in cross function reentrancies:
	- Treasury.createAllocation(uint256,string,address,uint256,address) (daio/treasury/Treasury.sol#172-210)
	- Treasury.getTreasuryBalance(string,address) (daio/treasury/Treasury.sol#279-288)
	- Treasury.getTreasuryStats(string) (daio/treasury/Treasury.sol#293-308)
	- Treasury.projectTreasuries (daio/treasury/Treasury.sol#33)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities-1
INFO:Detectors:
Detector: constable-states
Treasury.requiredSignatures (daio/treasury/Treasury.sol#48) should be constant 
Treasury.totalSigners (daio/treasury/Treasury.sol#49) should be constant 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-constant
INFO:Detectors:
Detector: immutable-states
Treasury.constitution (daio/treasury/Treasury.sol#21) should be immutable 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-immutable
INFO:Slither:daio/treasury/Treasury.sol analyzed (11 contracts with 63 detectors), 4 result(s) found
```

### `daio/treasury/TreasuryFeeCollector.sol`

```
Reentrancy in Treasury.distributeReward(string,address,uint256,address,string) (daio/treasury/Treasury.sol#248-274):
	External calls:
	- (ok,None) = address(recipient).call{value: amount}() (daio/treasury/Treasury.sol#263)
	State variables written after the call(s):
	- treasury.totalDistributed += amount (daio/treasury/Treasury.sol#271)
	Treasury.projectTreasuries (daio/treasury/Treasury.sol#33) can be used in cross function reentrancies:
	- Treasury.createAllocation(uint256,string,address,uint256,address) (daio/treasury/Treasury.sol#172-210)
	- Treasury.getTreasuryBalance(string,address) (daio/treasury/Treasury.sol#279-288)
	- Treasury.getTreasuryStats(string) (daio/treasury/Treasury.sol#293-308)
	- Treasury.projectTreasuries (daio/treasury/Treasury.sol#33)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities-1
INFO:Detectors:
Detector: constable-states
Treasury.requiredSignatures (daio/treasury/Treasury.sol#48) should be constant 
Treasury.totalSigners (daio/treasury/Treasury.sol#49) should be constant 
TreasuryFeeCollector.gasBufferMultiplier (daio/treasury/TreasuryFeeCollector.sol#92) should be constant 
TreasuryFeeCollector.maxGasRefundPerTx (daio/treasury/TreasuryFeeCollector.sol#91) should be constant 
TreasuryFeeCollector.minOperationalReserve (daio/treasury/TreasuryFeeCollector.sol#93) should be constant 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-constant
INFO:Detectors:
Detector: immutable-states
Treasury.constitution (daio/treasury/Treasury.sol#21) should be immutable 
TreasuryFeeCollector.treasury (daio/treasury/TreasuryFeeCollector.sol#95) should be immutable 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-immutable
INFO:Slither:daio/treasury/TreasuryFeeCollector.sol analyzed (15 contracts with 63 detectors), 9 result(s) found
```

### `daio/economics/ProposalStakingManager.sol`

```
ProposalStakingManager.defaultTreasuryShare (daio/economics/ProposalStakingManager.sol#102) should be constant 
ProposalStakingManager.defaultWinnerShare (daio/economics/ProposalStakingManager.sol#101) should be constant 
ProposalStakingManager.maxCompetitors (daio/economics/ProposalStakingManager.sol#105) should be constant 
ProposalStakingManager.minCompetitors (daio/economics/ProposalStakingManager.sol#104) should be constant 
ProposalStakingManager.roundCount (daio/economics/ProposalStakingManager.sol#95) should be constant 
Treasury.requiredSignatures (daio/treasury/Treasury.sol#48) should be constant 
Treasury.totalSigners (daio/treasury/Treasury.sol#49) should be constant 
TreasuryFeeCollector.gasBufferMultiplier (daio/treasury/TreasuryFeeCollector.sol#92) should be constant 
TreasuryFeeCollector.maxGasRefundPerTx (daio/treasury/TreasuryFeeCollector.sol#91) should be constant 
TreasuryFeeCollector.minOperationalReserve (daio/treasury/TreasuryFeeCollector.sol#93) should be constant 
TriumvirateGovernance.requiredDomainsForApproval (daio/governance/TriumvirateGovernance.sol#111) should be constant 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-constant
INFO:Detectors:
Detector: immutable-states
DAIO_ConfigurationEngine.constitution (daio/settings/DAIO_ConfigurationEngine.sol#72) should be immutable 
KnowledgeHierarchyDAIO.constitution (daio/governance/KnowledgeHierarchyDAIO.sol#63) should be immutable 
KnowledgeHierarchyDAIO.timelock (daio/governance/KnowledgeHierarchyDAIO.sol#62) should be immutable 
ProposalStakingManager.feeCollector (daio/economics/ProposalStakingManager.sol#109) should be immutable 
ProposalStakingManager.triumvirateGovernance (daio/economics/ProposalStakingManager.sol#108) should be immutable 
Treasury.constitution (daio/treasury/Treasury.sol#21) should be immutable 
TreasuryFeeCollector.treasury (daio/treasury/TreasuryFeeCollector.sol#95) should be immutable 
TriumvirateGovernance.configEngine (daio/governance/TriumvirateGovernance.sol#115) should be immutable 
TriumvirateGovernance.knowledgeHierarchy (daio/governance/TriumvirateGovernance.sol#114) should be immutable 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-immutable
INFO:Slither:daio/economics/ProposalStakingManager.sol analyzed (27 contracts with 63 detectors), 31 result(s) found
```

