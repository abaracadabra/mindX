# Bonding Curve Types

The DAIO Bonding Curve Protocol supports multiple curve types, each providing different price discovery mechanisms.

## Available Curve Types

### 1. POWER Curve (Default)
**Formula**: `P(S) = k * S^p`

- **Description**: Configurable power curve with adjustable exponent; supports flexible custom behavior patterns via `k` and `p`.
- **Behavior**:
  - `p = 1e18` (1.0): Linear pricing — constant marginal cost per token.
  - `p > 1e18`: Accelerating — price increases faster as supply grows; rewards very early participants.
  - `p < 1e18`: Decelerating — price increases slower as supply grows; more stability at higher supply.
- **Use Cases**: Flexible pricing for various tokenomics models, custom presale shapes, and tunable early/late participant incentives.
- **Parameters**:
  - `k`: Base coefficient (reserve per token^(p+1)); scales overall price level.
  - `p`: Exponent (UD60x18, can be fractional); defines curve shape.

#### POWER settings for flexible custom behavior patterns

Use these patterns when launching with `CurveType.POWER` (e.g. via `BondingCurveFactory.launchPowerCurveNative` with `curveType` implied as POWER and args `kUD60x18`, `pUD60x18`).

| Pattern | p (UD60x18) | k (example) | Behavior |
|--------|-------------|-------------|----------|
| **Linear** | `1e18` | e.g. `1e12` | Constant slope; simple, predictable. |
| **Sub-linear (gentle)** | `0.5e18` (sqrt) | e.g. `1e12` | Price grows slower as S increases; early spike then flatter. |
| **Sub-linear (mild)** | e.g. `0.8e18` | e.g. `1e12` | Between linear and sqrt; moderate deceleration. |
| **Super-linear (mild)** | e.g. `1.2e18` | e.g. `1e12` | Price grows faster with S; slight FOMO. |
| **Super-linear (aggressive)** | e.g. `1.5e18`–`2e18` | e.g. `1e11` | Strong early advantage; later buys much more expensive. |
| **Near-flat then rise** | e.g. `0.3e18` | e.g. `1e13` | Very flat at first, then gradual rise. |

- **k**: Increase `k` to raise the whole curve (higher cost per token at a given supply); decrease for cheaper entry. Scale with desired total reserve and supply (e.g. `1e12` for small units, `1e10` for larger).
- **p**: Fixed-point; `1e18` = 1.0. Use `0.5e18` for sqrt-like, `1e18` for linear, `1.5e18` for accelerating. Fractional values (e.g. `0.7e18`) give fine-grained behavior.
- **Combining**: Lower `k` + higher `p` = cheap start, steep later. Higher `k` + lower `p` = higher floor, gentler growth. Tune to match presale or DEX transition goals.

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

All five curve types are implemented in `MultiCurveMath.sol` in a fixed order: **POWER, LINEAR, EXPONENTIAL, DECELERATING, TIERED**. Select via `CurveType` enum when deploying a bonding curve pool.

- **POWER**: uses `k`, `p` (and delegates to `CurveMath`).
- **LINEAR**: uses `k` only (constant slope).
- **EXPONENTIAL**: uses `k`, `a`; spot price `P(S) = k * (e^(a*S) - 1)`; cost/mint use integral and iterative inverse.
- **DECELERATING**: uses `k`; implemented as power curve with `p = 0.5` (sqrt) for spot and matching integral.
- **TIERED**: uses `k`, `threshold1`, `threshold2`, `k2`; piecewise linear/flat/linear with phase helpers.

```solidity
MultiCurveMath.CurveParams memory params;
params.curveType = CurveType.EXPONENTIAL;
params.k = ud(1e12);
params.a = ud(1e17); // Growth rate
```
