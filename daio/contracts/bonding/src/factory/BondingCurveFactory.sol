// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { UD60x18, ud } from "prb-math/UD60x18.sol";

import { CurveToken } from "../token/CurveToken.sol";
import { BondingCurvePoolNative } from "../pool/BondingCurvePoolNative.sol";
import { CurveType } from "../math/CurveType.sol";
import { MultiCurveMath } from "../math/MultiCurveMath.sol";
import { BondingCurvePresaleSMAIRT } from "../extensions/BondingCurvePresaleSMAIRT.sol";
import { ILiquidityProvisioner } from "../liquidity/ILiquidityProvisioner.sol";

/// @notice Protocol factory / launcher.
/// @dev Deploys curve token + curve pool. Optionally deploys SMAIRT presale extension.
///      Token defaults: name="REFLECT REWARD", symbol="REWARD" (configurable at deployment).
contract BondingCurveFactory is Ownable {
    event LaunchedCurve(address indexed creator, address token, address pool);
    event LaunchedSMAIRT(address indexed creator, address presale);

    constructor(address owner_) Ownable(owner_) {}

    struct LaunchPowerCurveNativeArgs {
        // Token configuration (defaults: name="REFLECT REWARD", symbol="REWARD")
        string name;                    // Token name (empty = "REFLECT REWARD")
        string symbol;                  // Token symbol (empty = "REWARD")
        uint256 initialMintToOwner;     // Initial mint amount to owner (0 = no initial mint)

        // Curve params: price = k * S^p (UD60x18)
        uint256 kUD60x18;               // Coefficient (reserve per token^(p+1))
        uint256 pUD60x18;               // Exponent (can be fractional, e.g., 0.5e18 for sqrt, 1e18 for linear)

        // Protocol fee (optional)
        uint16 protocolFeeBps;          // Protocol fee in basis points (default 0)
        address feeRecipient;           // Fee recipient (default creator)

        // Optional presale extension
        bool enablePresale;              // Enable SMAIRT presale
        BondingCurvePresaleSMAIRT.PresaleOptions presaleOptions;
        address provisioner;            // Liquidity provisioner (e.g. UniV2Provisioner)
        ILiquidityProvisioner.LiquidityRequest liquidityTemplate; // Includes V2 router/weth + mode/enabled
    }

    /// @notice Launches a new bonding curve with optional presale.
    /// @param a Launch arguments including token config, curve params, and optional presale
    /// @return tokenAddr Address of the deployed curve token
    /// @return poolAddr Address of the deployed bonding curve pool
    /// @return presaleAddr Address of the presale contract (address(0) if not enabled)
    function launchPowerCurveNative(LaunchPowerCurveNativeArgs calldata a)
        external
        returns (address tokenAddr, address poolAddr, address presaleAddr)
    {
        // Use defaults if not provided
        string memory nm = bytes(a.name).length == 0 ? "REFLECT REWARD" : a.name;
        string memory sym = bytes(a.symbol).length == 0 ? "REWARD" : a.symbol;

        // Deploy curve token with configurable name, symbol, and initial mint
        CurveToken token = new CurveToken(nm, sym, msg.sender, a.initialMintToOwner);

        // Set up curve parameters (POWER curve: P(S) = k * S^p)
        MultiCurveMath.CurveParams memory cp;
        cp.curveType = CurveType.POWER;
        cp.k = ud(a.kUD60x18);
        cp.p = ud(a.pUD60x18);

        // Deploy bonding curve pool
        BondingCurvePoolNative pool = new BondingCurvePoolNative(token, cp, msg.sender);
        token.setPool(address(pool));

        // Configure protocol fee
        address recip = a.feeRecipient == address(0) ? msg.sender : a.feeRecipient;
        pool.setProtocolFee(a.protocolFeeBps, recip);

        emit LaunchedCurve(msg.sender, address(token), address(pool));

        tokenAddr = address(token);
        poolAddr = address(pool);

        // Deploy presale extension if enabled
        if (a.enablePresale) {
            BondingCurvePresaleSMAIRT presale = new BondingCurvePresaleSMAIRT(
                address(pool),
                address(token),
                a.provisioner,
                a.presaleOptions,
                a.liquidityTemplate,
                msg.sender
            );
            presaleAddr = address(presale);
            emit LaunchedSMAIRT(msg.sender, presaleAddr);
        }
    }
}
