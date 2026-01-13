# Bonding Curve Types

The DAIO Bonding Curve Protocol supports multiple curve types, each providing different price discovery mechanisms.

## Available Curve Types

### 1. POWER Curve (Default)
**Formula**: `P(S) = k * S^p`

- **Description**: Configurable power curve with adjustable exponent
- **Behavior**: 
  - `p = 1`: Linear pricing
  - `p > 1`: Accelerating (price increases faster as supply grows)
  - `p < 1`: Decelerating (price increases slower as supply grows)
- **Use Cases**: Flexible pricing for various tokenomics models
- **Parameters**:
  - `k`: Base coefficient
  - `p`: Exponent (UD60x18, can be fractional)

### 2. LINEAR Curve
**Formula**: `P(S) = k * S`

- **Description**: Constant slope pricing
- **Behavior**: Price increases at a constant rate per token
- **Use Cases**: Predictable, simple pricing model
- **Parameters**:
  - `k`: Slope coefficient

### 3. EXPONENTIAL Curve (Spike)
**Formula**: `P(S) = k * (e^(a*S) - 1)`

- **Description**: Starts slow, spikes exponentially
- **Behavior**: 
  - Early buyers get better prices
  - Price accelerates dramatically as supply increases
  - Creates urgency for early participation
- **Use Cases**: 
  - Presales with early bird incentives
  - Tokens with limited supply
  - FOMO-driven launches
- **Parameters**:
  - `k`: Base coefficient
  - `a`: Exponential growth rate

### 4. DECELERATING Curve (Stable)

### 5. TIERED Curve
**Formula**: Piecewise function with three phases:
- Phase 1 (0 to threshold1): `P(S) = k * S` (linear increase)
- Phase 2 (threshold1 to threshold2): `P(S) = k * threshold1` (flatline, constant price)
- Phase 3 (threshold2+): `P(S) = k * threshold1 + k2 * (S - threshold2)` (linear increase again)

- **Description**: Tiered pricing with flatline period
- **Behavior**: 
  - Starts with linear price increase
  - Enters flatline period at threshold1 (constant price)
  - Resumes linear increase at threshold2 with potentially different slope
- **Use Cases**: 
  - Presale periods with price stability
  - Milestone-based pricing
  - Controlled price discovery with stability windows
- **Parameters**: 
  - `k`: Initial slope coefficient
  - `threshold1`: Start of flatline (supply threshold)
  - `threshold2`: End of flatline (supply threshold)
  - `k2`: Second slope coefficient (after flatline)

**Formula**: `P(S) = k * sqrt(S)`

- **Description**: Starts fast, becomes more stable over time
- **Behavior**:
  - Price increases quickly at low supply
  - Price growth slows as supply increases
  - More price stability at higher supply levels
- **Use Cases**:
  - Long-term price stability
  - Reducing volatility
  - Sustainable growth models
- **Parameters**:
  - `k`: Base coefficient

## Price Comparison with DEX Pairs

The protocol includes a DEX price oracle system to compare bonding curve prices with live DEX pairs.

### Features

1. **Real-time Price Comparison**: Compare bonding curve price with Uniswap V2 style pairs
2. **Price Ratio Calculation**: Shows how bonding curve price compares to DEX price
3. **Premium Calculation**: Calculates premium/discount in basis points
4. **Equivalent Price Calculation**: Shows what price would be if bonding curve had same liquidity ratio as DEX

### Usage

```solidity
DEXPriceOracle oracle = new DEXPriceOracle();

// Get DEX price
(uint256 dexPrice, uint256 reserveToken, uint256 reserveWeth) = 
    oracle.getDEXPrice(token, weth, pair);

// Compare prices
(uint256 priceRatio, int256 premiumBps) = 
    oracle.comparePrices(bondingCurvePrice, dexPrice);

// Calculate equivalent price
uint256 equivalentPrice = oracle.calculateEquivalentPrice(
    bondingCurvePrice,
    dexReserveToken,
    dexReserveWeth,
    bondingCurveSupply,
    bondingCurveReserve
);
```

### Price Ratio Interpretation

- `priceRatio = 1e18`: Same price (1:1)
- `priceRatio > 1e18`: Bonding curve is more expensive
- `priceRatio < 1e18`: Bonding curve is cheaper

### Premium Calculation

- `premiumBps > 0`: Bonding curve premium (more expensive)
- `premiumBps < 0`: Bonding curve discount (cheaper)
- `premiumBps = 0`: Same price

## Choosing a Curve Type

### For Presales
- **EXPONENTIAL**: Creates urgency, rewards early buyers
- **LINEAR**: Simple, predictable pricing

### For Long-term Stability
- **DECELERATING**: Reduces volatility over time
- **POWER with p < 1**: Gradual price stabilization

### For Flexible Models
- **POWER**: Adjustable exponent for custom behavior

## Implementation

All curve types are implemented in `MultiCurveMath.sol` and can be selected via `CurveType` enum when deploying a bonding curve pool.

```solidity
MultiCurveMath.CurveParams memory params;
params.curveType = CurveType.EXPONENTIAL;
params.k = ud(1e12);
params.a = ud(1e17); // Growth rate
```
