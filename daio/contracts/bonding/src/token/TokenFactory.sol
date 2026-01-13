// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { TokenType } from "./TokenType.sol";
import { CurveToken } from "./CurveToken.sol";
import { ReflectionRewardToken } from "./ReflectionRewardToken.sol";
import { RebaseToken } from "./RebaseToken.sol";

/// @notice Factory for creating different token types
/// @dev Supports CURVE_TOKEN, REFLECTION_REWARD, and REBASE_TOKEN types
contract TokenFactory {
    event TokenCreated(TokenType tokenType, address token, address creator);

    /// @notice Token creation parameters for ReflectionRewardToken
    struct ReflectionTokenParams {
        string name;                    // Token name (empty = "REFLECT REWARD")
        string symbol;                  // Token symbol (empty = "REWARD")
        uint256 totalSupply;            // Total supply (default: 1e35 = 100 quadrillion)
        uint256 reflectionFee;          // Reflection fee in basis points (default: 300 = 3%)
        uint256 liquidityFee;            // Liquidity fee in basis points (default: 100 = 1%)
        uint256 teamFee;                // Team fee in basis points (default: 100 = 1%)
        address teamWallet;             // Team wallet address
        address liquidityWallet;        // Liquidity wallet address
        address router;                 // Router address (Uniswap V2 compatible)
        address weth;                   // WETH address
    }

    /// @notice Token creation parameters for RebaseToken
    struct RebaseTokenParams {
        string name;                    // Token name (empty = "REB ACE")
        string symbol;                  // Token symbol (empty = "REBACE")
        uint256 initialSupply;          // Initial supply (default: 22222222 * 10^18)
        uint256 liquidityFee;          // Liquidity fee (default: 33 = 3.3%)
        uint256 treasuryFee;           // Treasury fee (default: 45 = 4.5%)
        uint256 burnFee;               // Burn fee (default: 11 = 1.1%)
        uint256 buyFeeRFV;             // Buy RFV fee (default: 22 = 2.2%)
        uint256 sellFeeTreasuryAdded;  // Additional sell treasury fee (default: 66 = 6.6%)
        uint256 sellFeeRFVAdded;       // Additional sell RFV fee (default: 45 = 4.5%)
        address liquidityReceiver;      // Liquidity receiver address
        address treasuryReceiver;       // Treasury receiver address
        address riskFreeValueReceiver;  // RFV receiver address
        address router;                 // Router address
        address weth;                   // WETH address
        address busdToken;             // BUSD token address (optional, can be address(0))
    }

    /// @notice Create a CurveToken (standard bonding curve token)
    /// @param name Token name (empty = "REFLECT REWARD")
    /// @param symbol Token symbol (empty = "REWARD")
    /// @param owner Token owner
    /// @param initialMintToOwner Initial mint amount to owner (0 = no initial mint)
    function createCurveToken(
        string memory name,
        string memory symbol,
        address owner,
        uint256 initialMintToOwner
    ) external returns (address) {
        // Use defaults if not provided
        string memory nm = bytes(name).length == 0 ? "REFLECT REWARD" : name;
        string memory sym = bytes(symbol).length == 0 ? "REWARD" : symbol;

        CurveToken token = new CurveToken(nm, sym, owner, initialMintToOwner);
        emit TokenCreated(TokenType.CURVE_TOKEN, address(token), msg.sender);
        return address(token);
    }

    /// @notice Create a ReflectionRewardToken with configurable parameters
    /// @param params Token parameters (uses defaults if values are 0 or empty)
    function createReflectionRewardToken(
        ReflectionTokenParams memory params
    ) external returns (address) {
        // Use defaults if not provided
        string memory nm = bytes(params.name).length == 0 ? "REFLECT REWARD" : params.name;
        string memory sym = bytes(params.symbol).length == 0 ? "REWARD" : params.symbol;
        
        // Default total supply: 1e35 (100 quadrillion)
        uint256 supply = params.totalSupply == 0 ? 1e35 : params.totalSupply;
        
        // Default fees: 3% reflection, 1% liquidity, 1% team
        uint256 reflectionFee = params.reflectionFee == 0 ? 300 : params.reflectionFee;
        uint256 liquidityFee = params.liquidityFee == 0 ? 100 : params.liquidityFee;
        uint256 teamFee = params.teamFee == 0 ? 100 : params.teamFee;
        
        // Require wallets and router
        require(params.teamWallet != address(0), "Team wallet required");
        require(params.liquidityWallet != address(0), "Liquidity wallet required");
        require(params.router != address(0), "Router required");
        require(params.weth != address(0), "WETH required");

        ReflectionRewardToken token = new ReflectionRewardToken(
            nm,
            sym,
            supply,
            reflectionFee,
            liquidityFee,
            teamFee,
            params.teamWallet,
            params.liquidityWallet,
            params.router,
            params.weth
        );
        
        emit TokenCreated(TokenType.REFLECTION_REWARD, address(token), msg.sender);
        return address(token);
    }

    /// @notice Create a RebaseToken with configurable parameters
    /// @param params Token parameters (uses defaults if values are 0 or empty)
    function createRebaseToken(
        RebaseTokenParams memory params
    ) external returns (address) {
        // Use defaults if not provided
        string memory nm = bytes(params.name).length == 0 ? "REB ACE" : params.name;
        string memory sym = bytes(params.symbol).length == 0 ? "REBACE" : params.symbol;
        
        // Default initial supply: 22222222 * 10^18
        uint256 initialSupply = params.initialSupply == 0 ? 22222222 * 10**18 : params.initialSupply;
        
        // Default fees (from DeltaV)
        uint256 liquidityFee = params.liquidityFee == 0 ? 33 : params.liquidityFee;
        uint256 treasuryFee = params.treasuryFee == 0 ? 45 : params.treasuryFee;
        uint256 burnFee = params.burnFee == 0 ? 11 : params.burnFee;
        uint256 buyFeeRFV = params.buyFeeRFV == 0 ? 22 : params.buyFeeRFV;
        uint256 sellFeeTreasuryAdded = params.sellFeeTreasuryAdded == 0 ? 66 : params.sellFeeTreasuryAdded;
        uint256 sellFeeRFVAdded = params.sellFeeRFVAdded == 0 ? 45 : params.sellFeeRFVAdded;
        
        // Require addresses
        require(params.liquidityReceiver != address(0), "Liquidity receiver required");
        require(params.treasuryReceiver != address(0), "Treasury receiver required");
        require(params.riskFreeValueReceiver != address(0), "RFV receiver required");
        require(params.router != address(0), "Router required");
        require(params.weth != address(0), "WETH required");

        RebaseToken token = new RebaseToken(
            nm,
            sym,
            initialSupply,
            liquidityFee,
            treasuryFee,
            burnFee,
            buyFeeRFV,
            sellFeeTreasuryAdded,
            sellFeeRFVAdded,
            params.liquidityReceiver,
            params.treasuryReceiver,
            params.riskFreeValueReceiver,
            params.router,
            params.weth,
            params.busdToken
        );
        
        emit TokenCreated(TokenType.REBASE_TOKEN, address(token), msg.sender);
        return address(token);
    }

    /// @notice Create a token based on type
    /// @param tokenType Type of token to create
    /// @param name Token name (empty = default for type)
    /// @param symbol Token symbol (empty = default for type)
    /// @param owner Token owner
    /// @param initialMint Initial mint amount (for CurveToken) or total supply (for ReflectionRewardToken) or initial supply (for RebaseToken)
    /// @param reflectionParams Additional parameters for ReflectionRewardToken (ignored for other types)
    /// @param rebaseParams Additional parameters for RebaseToken (ignored for other types)
}
    function createToken(
        TokenType tokenType,
        string memory name,
        string memory symbol,
        address owner,
        uint256 initialMint,
        ReflectionTokenParams memory reflectionParams,
        RebaseTokenParams memory rebaseParams
    ) external returns (address) {
        if (tokenType == TokenType.CURVE_TOKEN) {
            return createCurveToken(name, symbol, owner, initialMint);
        } else if (tokenType == TokenType.REFLECTION_REWARD) {
            // Use provided params or defaults
            reflectionParams.name = bytes(reflectionParams.name).length == 0 ? name : reflectionParams.name;
            reflectionParams.symbol = bytes(reflectionParams.symbol).length == 0 ? symbol : reflectionParams.symbol;
            reflectionParams.totalSupply = initialMint == 0 ? 0 : initialMint;
            return createReflectionRewardToken(reflectionParams);
        } else if (tokenType == TokenType.REBASE_TOKEN) {
            // Use provided params or defaults
            rebaseParams.name = bytes(rebaseParams.name).length == 0 ? name : rebaseParams.name;
            rebaseParams.symbol = bytes(rebaseParams.symbol).length == 0 ? symbol : rebaseParams.symbol;
            rebaseParams.initialSupply = initialMint == 0 ? 0 : initialMint;
            return createRebaseToken(rebaseParams);
        } else {
            revert("Unknown token type");
        }
    }
