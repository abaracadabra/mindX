// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ISpinTradePair} from "./interfaces/ISpinTradePair.sol";

/// @title SpinTradePair — minimal Uniswap V2-style constant product market maker
/// @notice (x * y = k) AMM with 0.30% trading fee. LP shares are themselves
///         ERC20 tokens minted to liquidity providers.
/// @dev    Designed for local testing of the BANKON/PYTHAI BDI trader.
///         Spec deliberately mirrors Uniswap V2 swap math so existing tooling
///         (slippage calc, price impact, off-chain quoter) translates directly.
contract SpinTradePair is ISpinTradePair, ERC20, ReentrancyGuard {
    using SafeERC20 for IERC20;

    /// 0.30% trading fee (Uniswap V2 standard) — 997/1000 of input retained for swap.
    uint256 public constant FEE_NUMERATOR = 997;
    uint256 public constant FEE_DENOMINATOR = 1000;

    /// Locked dust to prevent first-LP donation attack (Uniswap V2 MINIMUM_LIQUIDITY).
    uint256 public constant MINIMUM_LIQUIDITY = 1000;

    address public immutable token0;
    address public immutable token1;

    /// @dev Reserve cache; updated on every state-changing call.
    uint112 private _reserve0;
    uint112 private _reserve1;
    uint32  private _blockTimestampLast;

    constructor(address _token0, address _token1)
        ERC20(_pairName(_token0, _token1), _pairSymbol(_token0, _token1))
    {
        require(_token0 != address(0) && _token1 != address(0), "ZERO_ADDR");
        require(_token0 != _token1, "IDENTICAL_TOKENS");
        // Canonical ordering — pair is symmetrical but token0 < token1 by address.
        if (_token0 < _token1) {
            token0 = _token0;
            token1 = _token1;
        } else {
            token0 = _token1;
            token1 = _token0;
        }
    }

    /* ─────────── Reads ─────────── */

    function reserves() external view override returns (uint256 r0, uint256 r1, uint32 lastUpdate) {
        return (_reserve0, _reserve1, _blockTimestampLast);
    }

    function quote(uint256 amountIn, address tokenIn) external view override returns (uint256 amountOut) {
        if (amountIn == 0) revert ZeroAmount();
        if (tokenIn != token0 && tokenIn != token1) revert InvalidToken();
        (uint256 reserveIn, uint256 reserveOut) = tokenIn == token0
            ? (uint256(_reserve0), uint256(_reserve1))
            : (uint256(_reserve1), uint256(_reserve0));
        if (reserveIn == 0 || reserveOut == 0) revert InsufficientLiquidity();
        return _getAmountOut(amountIn, reserveIn, reserveOut);
    }

    /* ─────────── Liquidity ─────────── */

    /// @notice Deposit token0+token1 in proportion; mint LP shares.
    /// @dev    First call sets the price. Subsequent calls require ratio match.
    function addLiquidity(uint256 amount0, uint256 amount1, address to)
        external
        override
        nonReentrant
        returns (uint256 lpMinted)
    {
        if (amount0 == 0 || amount1 == 0) revert ZeroAmount();
        if (to == address(0)) revert InvalidToken();

        IERC20(token0).safeTransferFrom(msg.sender, address(this), amount0);
        IERC20(token1).safeTransferFrom(msg.sender, address(this), amount1);

        uint256 _totalSupply = totalSupply();
        if (_totalSupply == 0) {
            // First LP — geometric mean, lock minimum dust.
            lpMinted = Math.sqrt(amount0 * amount1) - MINIMUM_LIQUIDITY;
            _mint(address(0xdead), MINIMUM_LIQUIDITY);
        } else {
            // Maintain ratio — give the smaller of the two scaled options.
            uint256 lp0 = (amount0 * _totalSupply) / _reserve0;
            uint256 lp1 = (amount1 * _totalSupply) / _reserve1;
            lpMinted = lp0 < lp1 ? lp0 : lp1;
        }
        if (lpMinted == 0) revert InsufficientLiquidity();
        _mint(to, lpMinted);
        _syncReserves();
        emit LiquidityAdded(msg.sender, amount0, amount1, lpMinted);
    }

    /// @notice Burn LP shares, withdraw underlying token0+token1 pro rata.
    function removeLiquidity(uint256 lpAmount, address to)
        external
        override
        nonReentrant
        returns (uint256 amount0, uint256 amount1)
    {
        if (lpAmount == 0) revert ZeroAmount();
        if (to == address(0)) revert InvalidToken();
        uint256 _totalSupply = totalSupply();

        uint256 bal0 = IERC20(token0).balanceOf(address(this));
        uint256 bal1 = IERC20(token1).balanceOf(address(this));
        amount0 = (lpAmount * bal0) / _totalSupply;
        amount1 = (lpAmount * bal1) / _totalSupply;
        if (amount0 == 0 || amount1 == 0) revert InsufficientLiquidity();

        _burn(msg.sender, lpAmount);
        IERC20(token0).safeTransfer(to, amount0);
        IERC20(token1).safeTransfer(to, amount1);
        _syncReserves();
        emit LiquidityRemoved(msg.sender, lpAmount, amount0, amount1);
    }

    /* ─────────── Swap ─────────── */

    /// @notice Swap exact `amountIn` of `tokenIn` for `tokenOut`.
    /// @param  minAmountOut Slippage protection; reverts if computed output is lower.
    function swap(uint256 amountIn, address tokenIn, uint256 minAmountOut, address to)
        external
        override
        nonReentrant
        returns (uint256 amountOut)
    {
        if (amountIn == 0) revert ZeroAmount();
        if (tokenIn != token0 && tokenIn != token1) revert InvalidToken();
        if (to == address(0)) revert InvalidToken();

        bool zeroIn = (tokenIn == token0);
        address tokenOut = zeroIn ? token1 : token0;
        (uint256 reserveIn, uint256 reserveOut) = zeroIn
            ? (uint256(_reserve0), uint256(_reserve1))
            : (uint256(_reserve1), uint256(_reserve0));
        if (reserveIn == 0 || reserveOut == 0) revert InsufficientLiquidity();

        amountOut = _getAmountOut(amountIn, reserveIn, reserveOut);
        if (amountOut < minAmountOut) revert InsufficientOutput();

        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        IERC20(tokenOut).safeTransfer(to, amountOut);
        _syncReserves();
        emit Swap(msg.sender, tokenIn, amountIn, amountOut, to);
    }

    /* ─────────── Internal ─────────── */

    /// @dev Uniswap V2 swap formula with 0.3% fee.
    ///      out = (reserveOut * amountIn * 997) / (reserveIn * 1000 + amountIn * 997)
    function _getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut)
        internal
        pure
        returns (uint256)
    {
        uint256 amountInWithFee = amountIn * FEE_NUMERATOR;
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = (reserveIn * FEE_DENOMINATOR) + amountInWithFee;
        return numerator / denominator;
    }

    function _syncReserves() internal {
        uint256 bal0 = IERC20(token0).balanceOf(address(this));
        uint256 bal1 = IERC20(token1).balanceOf(address(this));
        require(bal0 <= type(uint112).max && bal1 <= type(uint112).max, "OVERFLOW");
        _reserve0 = uint112(bal0);
        _reserve1 = uint112(bal1);
        _blockTimestampLast = uint32(block.timestamp);
    }

    function _pairName(address a, address b) internal view returns (string memory) {
        try ERC20(a).symbol() returns (string memory sa) {
            try ERC20(b).symbol() returns (string memory sb) {
                return string.concat("SpinTrade ", sa, "/", sb, " LP");
            } catch { return "SpinTrade LP"; }
        } catch { return "SpinTrade LP"; }
    }

    function _pairSymbol(address a, address b) internal view returns (string memory) {
        try ERC20(a).symbol() returns (string memory sa) {
            try ERC20(b).symbol() returns (string memory sb) {
                return string.concat("SPIN-", sa, "-", sb);
            } catch { return "SPIN-LP"; }
        } catch { return "SPIN-LP"; }
    }
}
