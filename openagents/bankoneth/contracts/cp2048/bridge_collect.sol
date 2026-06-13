// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// bridge_collect — the on-chain anchor of the "GLMR bridging machine" (LI.FI
// extrapolation). A payer can pay in ANY currency on ANY chain; LI.FI bridges
// the value to the settlement chain off-chain, and this contract (a) takes the
// golden-ratio fee → RAKE (→ bankon.eth) and (b) emits a BridgeCollected intent
// the LI.FI/GLMR relayer fulfils. Keeps collection sovereign and on-chain while
// the bridging itself rides LI.FI's open infrastructure.
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {scientific_math} from "./scientific_math.sol";

contract bridge_collect is Ownable {
    using SafeERC20 for IERC20;

    address public rake;       // golden fee → bankon.eth (via RAKE)
    uint256 public feeDiv;     // golden-fee divisor

    event BridgeCollected(
        address indexed payer, address indexed asset, uint256 amount, uint256 feeWad,
        uint256 indexed dstChainId, bytes32 resource, address recipient
    );
    event Config(address rake, uint256 feeDiv);

    constructor(address admin_, address rake_, uint256 feeDiv_) Ownable(admin_) { rake = rake_; feeDiv = feeDiv_; }
    function configure(address rk, uint256 fd) external onlyOwner { rake = rk; feeDiv = fd; emit Config(rk, fd); }

    /// @notice Collect a cross-chain payment: take `asset` from the payer, route the
    ///         golden fee to RAKE, hold the remainder for the LI.FI/GLMR relayer to
    ///         bridge to `dstChainId`, and emit the intent.
    function collect_for_bridge(
        address asset,
        uint256 amount,
        uint256 dstChainId,
        bytes32 resource,
        address recipient
    ) external returns (uint256 forwarded) {
        IERC20(asset).safeTransferFrom(msg.sender, address(this), amount);
        uint256 feeWad = feeDiv == 0 ? 0 : scientific_math.goldenFeeWad(amount, feeDiv);
        if (feeWad > 0 && rake != address(0)) IERC20(asset).safeTransfer(rake, feeWad);
        forwarded = amount - feeWad;
        emit BridgeCollected(msg.sender, asset, amount, feeWad, dstChainId, resource, recipient);
    }

    /// @notice Owner moves bridge-pending balances to the LI.FI router/relayer.
    function release(address asset, address to, uint256 amount) external onlyOwner {
        IERC20(asset).safeTransfer(to, amount);
    }
}
