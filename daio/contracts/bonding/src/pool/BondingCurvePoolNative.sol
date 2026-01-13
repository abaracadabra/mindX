// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";

import { UD60x18, ud, unwrap } from "prb-math/UD60x18.sol";
import { CurveToken } from "../token/CurveToken.sol";
import { CurveMath } from "../math/CurveMath.sol";
import { MultiCurveMath } from "../math/MultiCurveMath.sol";
import { CurveType } from "../math/CurveType.sol";

/// @notice Native-reserve (ETH) bonding curve pool.
///         Protocol fee is optional (bps, default 0), taken from:
///           - buy: fee from ETH-in
///           - sell: fee from ETH-out
///         Curve: power curve price(S)=k*S^p via integral/inverse integral.
contract BondingCurvePoolNative is ReentrancyGuard, Ownable {
    using MultiCurveMath for MultiCurveMath.CurveParams;

    event Buy(address indexed buyer, address indexed to, uint256 ethIn, uint256 feeEth, uint256 tokensOut);
    event Sell(address indexed seller, address indexed to, uint256 tokensIn, uint256 ethOut, uint256 feeEth);

    CurveToken public immutable curveToken;
    MultiCurveMath.CurveParams public curveParams;
    CurveType public curveType;

    uint16 public protocolFeeBps; // 0..10_000
    address public feeRecipient;

    error Slippage();
    error ZeroAddress();
    error InvalidFeeBps();
    error TransferFailed();
    error InsufficientReserve();

    constructor(
        CurveToken curveToken_,
        MultiCurveMath.CurveParams memory curveParams_,
        address owner_
    ) Ownable(owner_) {
        curveToken = curveToken_;
        curveParams = curveParams_;
        curveType = curveParams_.curveType;
        protocolFeeBps = 0;
        feeRecipient = owner_;
    }

    receive() external payable {}

    function setProtocolFee(uint16 bps, address recipient) external onlyOwner {
        if (bps > 10_000) revert InvalidFeeBps();
        if (recipient == address(0)) revert ZeroAddress();
        protocolFeeBps = bps;
        feeRecipient = recipient;
    }

    function totalSupply() public view returns (uint256) {
        return curveToken.totalSupply();
    }

    function quoteBuy(uint256 ethIn) external view returns (uint256 tokensOut) {
        if (ethIn == 0) return 0;
        uint256 fee = (ethIn * protocolFeeBps) / 10_000;
        uint256 net = ethIn - fee;

        UD60x18 S = ud(totalSupply());
        UD60x18 cost = ud(net);
        UD60x18 d = MultiCurveMath.mintAmountForCost(curveParams, S, cost);
        return unwrap(d);
    }

    function quoteSell(uint256 tokensIn) external view returns (uint256 ethOut) {
        if (tokensIn == 0) return 0;

        UD60x18 S = ud(totalSupply());
        UD60x18 d = ud(tokensIn);
        UD60x18 refund = MultiCurveMath.refundToBurn(curveParams, S, d);
        uint256 gross = unwrap(refund);

        uint256 fee = (gross * protocolFeeBps) / 10_000;
        return gross - fee;
    }

    function buy(uint256 minTokensOut, address to) external payable nonReentrant returns (uint256 tokensOut) {
        require(to != address(0), "to=0");
        require(msg.value > 0, "ethIn=0");

        uint256 fee = (msg.value * protocolFeeBps) / 10_000;
        uint256 net = msg.value - fee;

        UD60x18 S = ud(totalSupply());
        UD60x18 cost = ud(net);
        UD60x18 d = MultiCurveMath.mintAmountForCost(curveParams, S, cost);
        tokensOut = unwrap(d);

        if (tokensOut < minTokensOut) revert Slippage();

        if (fee > 0) {
            (bool okFee,) = payable(feeRecipient).call{value: fee}("");
            if (!okFee) revert TransferFailed();
        }

        curveToken.mint(to, tokensOut);
        emit Buy(msg.sender, to, msg.value, fee, tokensOut);
    }

    function sell(uint256 tokensIn, uint256 minEthOut, address to) external nonReentrant returns (uint256 ethOut) {
        require(to != address(0), "to=0");
        require(tokensIn > 0, "tokensIn=0");

        UD60x18 S = ud(totalSupply());
        UD60x18 d = ud(tokensIn);
        UD60x18 refund = MultiCurveMath.refundToBurn(curveParams, S, d);
        uint256 gross = unwrap(refund);

        if (address(this).balance < gross) revert InsufficientReserve();

        uint256 fee = (gross * protocolFeeBps) / 10_000;
        ethOut = gross - fee;

        if (ethOut < minEthOut) revert Slippage();

        // pull tokens then burn
        curveToken.transferFrom(msg.sender, address(this), tokensIn);
        curveToken.burn(address(this), tokensIn);

        if (fee > 0) {
            (bool okFee,) = payable(feeRecipient).call{value: fee}("");
            if (!okFee) revert TransferFailed();
        }

        (bool ok,) = payable(to).call{value: ethOut}("");
        if (!ok) revert TransferFailed();

        emit Sell(msg.sender, to, tokensIn, ethOut, fee);
    }
}
