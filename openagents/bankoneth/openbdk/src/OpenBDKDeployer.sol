// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

import {OpenBDKTimelock} from "./governance/OpenBDKTimelock.sol";
import {OpenBDKValidatorRegistry} from "./governance/OpenBDKValidatorRegistry.sol";
import {OpenBDKAllocations} from "./allocations/OpenBDKAllocations.sol";

/**
 * @title  OpenBDKDeployer — one-transaction, OWNER-custodial openBDK governance stack
 * @author Professor Codephreak / openBDK
 * @notice The client-side deployer (deployer/index.xml DEPLOY → LAUNCH) fires this
 *         with STATIC constructor args only (no proxy `bytes` init — that lives
 *         here, in Solidity). In one tx it stands up the OWNER-custodial control
 *         plane and hands EVERYTHING to the OWNER's timelock:
 *
 *           1. OpenBDKTimelock (the OVERLORD)  — proposer/executor = OWNER wallet
 *           2. OpenBDKValidatorRegistry (proxy) — DEFAULT_ADMIN = the timelock
 *           3. OpenBDKAllocations              — owner = the timelock (if token given)
 *
 * @dev    THE NON-CUSTODIAL INVARIANT: this factory grants itself NO role and keeps
 *         NO key. Admin of every deployed contract is the OVERLORD timelock, whose
 *         sole proposer/executor is `owner` — the wallet that holds its own private
 *         key (recognized at the UI by proof-of-signature). The software/deploy key
 *         that broadcasts this tx retains nothing once the constructor returns.
 *
 *         OWNER holds the private key. The software does not.
 */
contract OpenBDKDeployer {
    address public immutable owner;
    address public immutable timelock;
    address public immutable validatorRegistry;
    address public immutable allocations;

    event OpenBDKDeployed(
        address indexed owner,
        address timelock,
        address validatorRegistry,
        address allocations,
        uint256 timelockMinDelay
    );

    /**
     * @param owner_           the wallet that will own the stack (holds its own key)
     * @param timelockMinDelay OVERLORD transparency delay, seconds (e.g. 2 days)
     * @param stakingToken     ERC-20 validators stake (THRUST/governance token)
     * @param minimumStake     minimum stake to qualify as validator
     * @param unbondingPeriod  blocks staked tokens lock after exit
     * @param allocationToken  ERC-20 for vesting allocations; address(0) to skip
     */
    constructor(
        address owner_,
        uint256 timelockMinDelay,
        address stakingToken,
        uint256 minimumStake,
        uint256 unbondingPeriod,
        address allocationToken
    ) {
        owner = owner_;

        // 1. OVERLORD timelock — owner is sole proposer/executor; no admin backdoor.
        OpenBDKTimelock tl = new OpenBDKTimelock(timelockMinDelay, owner_);
        timelock = address(tl);

        // 2. ValidatorRegistry behind a proxy, admin = the timelock (NOT this factory).
        OpenBDKValidatorRegistry vrImpl = new OpenBDKValidatorRegistry();
        ERC1967Proxy vrProxy = new ERC1967Proxy(
            address(vrImpl),
            abi.encodeCall(
                OpenBDKValidatorRegistry.initialize,
                (address(tl), stakingToken, owner_, minimumStake, unbondingPeriod)
            )
        );
        validatorRegistry = address(vrProxy);

        // 3. Allocations vault owned by the timelock (optional).
        address alloc;
        if (allocationToken != address(0)) {
            alloc = address(new OpenBDKAllocations(allocationToken, address(tl)));
        }
        allocations = alloc;

        emit OpenBDKDeployed(owner_, address(tl), address(vrProxy), alloc, timelockMinDelay);
    }
}
