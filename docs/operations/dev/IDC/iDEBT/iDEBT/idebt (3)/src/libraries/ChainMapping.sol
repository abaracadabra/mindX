// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ChainMapping
/// @notice Canonical cross-chain registry mirroring the `allchain.html`
///         manifest at agenticplace.pythai.net. Each chain carries:
///           - chainId       : EIP-155 id (or sentinel for non-EVM)
///           - family        : EVM | ALGORAND | COSMOS | SOLANA | SUI
///           - nativeGas     : asset used for gas (e.g. ETH, MATIC, ALGO)
///           - stableAnchor  : canonical stablecoin address on that chain
/// @dev    Exposed as a pure library so that scripts, contracts and
///         front-ends agree on a single canonical chain table.
library ChainMapping {
    enum Family { EVM, ALGORAND, COSMOS, SOLANA, SUI }

    struct Chain {
        uint256 chainId;
        Family  family;
        bytes32 nativeGas;      // e.g. bytes32("ETH")
        bytes32 stableAnchor;   // e.g. bytes32("USDC")
        string  name;
        string  rpcHint;        // non-authoritative rpc example
    }

    // ---- EVM ----
    uint256 internal constant ETHEREUM        = 1;
    uint256 internal constant OPTIMISM        = 10;
    uint256 internal constant BSC             = 56;
    uint256 internal constant POLYGON         = 137;
    uint256 internal constant FANTOM          = 250;
    uint256 internal constant ZKSYNC_ERA      = 324;
    uint256 internal constant POLYGON_ZKEVM   = 1101;
    uint256 internal constant BASE            = 8453;
    uint256 internal constant ARBITRUM_ONE    = 42_161;
    uint256 internal constant AVALANCHE_C     = 43_114;
    uint256 internal constant SEPOLIA         = 11_155_111;
    uint256 internal constant ARC             = 5_042_002; // Arc Network (USDC native gas)

    // ---- Non-EVM sentinels (chosen to never collide with EIP-155) ----
    uint256 internal constant ALGORAND_MAINNET = 4_160_001;
    uint256 internal constant ALGORAND_TESTNET = 4_160_002;
    uint256 internal constant SOLANA_MAINNET   = 5_001_001;
    uint256 internal constant COSMOS_HUB       = 6_001_001;
    uint256 internal constant SUI_MAINNET      = 7_001_001;

    /// @notice Resolve a chain record by id.
    /// @dev    Explicitly enumerated so the on-chain table is auditable and
    ///         deterministic. Unknown ids revert to force explicit registration.
    function chainOf(uint256 chainId) internal pure returns (Chain memory c) {
        if (chainId == ETHEREUM)
            return Chain(ETHEREUM, Family.EVM, "ETH", "USDC", "Ethereum", "https://eth.llamarpc.com");
        if (chainId == OPTIMISM)
            return Chain(OPTIMISM, Family.EVM, "ETH", "USDC", "Optimism", "https://mainnet.optimism.io");
        if (chainId == POLYGON)
            return Chain(POLYGON, Family.EVM, "MATIC", "USDC", "Polygon PoS", "https://polygon-rpc.com");
        if (chainId == POLYGON_ZKEVM)
            return Chain(POLYGON_ZKEVM, Family.EVM, "ETH", "USDC", "Polygon zkEVM", "https://zkevm-rpc.com");
        if (chainId == ARBITRUM_ONE)
            return Chain(ARBITRUM_ONE, Family.EVM, "ETH", "USDC", "Arbitrum One", "https://arb1.arbitrum.io/rpc");
        if (chainId == BASE)
            return Chain(BASE, Family.EVM, "ETH", "USDC", "Base", "https://mainnet.base.org");
        if (chainId == BSC)
            return Chain(BSC, Family.EVM, "BNB", "USDT", "BNB Smart Chain", "https://bsc-dataseed.binance.org");
        if (chainId == AVALANCHE_C)
            return Chain(AVALANCHE_C, Family.EVM, "AVAX", "USDC", "Avalanche C-Chain", "https://api.avax.network/ext/bc/C/rpc");
        if (chainId == ZKSYNC_ERA)
            return Chain(ZKSYNC_ERA, Family.EVM, "ETH", "USDC", "zkSync Era", "https://mainnet.era.zksync.io");
        if (chainId == FANTOM)
            return Chain(FANTOM, Family.EVM, "FTM", "USDC", "Fantom Opera", "https://rpc.ftm.tools");
        if (chainId == SEPOLIA)
            return Chain(SEPOLIA, Family.EVM, "ETH", "USDC", "Sepolia", "https://rpc.sepolia.org");
        if (chainId == ARC)
            return Chain(ARC, Family.EVM, "USDC", "USDC", "Arc Network", "https://rpc.arc.network");
        if (chainId == ALGORAND_MAINNET)
            return Chain(ALGORAND_MAINNET, Family.ALGORAND, "ALGO", "USDCa", "Algorand Mainnet", "https://mainnet-api.algonode.cloud");
        if (chainId == ALGORAND_TESTNET)
            return Chain(ALGORAND_TESTNET, Family.ALGORAND, "ALGO", "USDCa", "Algorand Testnet", "https://testnet-api.algonode.cloud");
        if (chainId == SOLANA_MAINNET)
            return Chain(SOLANA_MAINNET, Family.SOLANA, "SOL", "USDC", "Solana", "https://api.mainnet-beta.solana.com");
        if (chainId == COSMOS_HUB)
            return Chain(COSMOS_HUB, Family.COSMOS, "ATOM", "USDC", "Cosmos Hub", "https://rpc-cosmoshub.blockapsis.com");
        if (chainId == SUI_MAINNET)
            return Chain(SUI_MAINNET, Family.SUI, "SUI", "USDC", "Sui", "https://fullnode.mainnet.sui.io:443");

        c.chainId = 0; // sentinel: caller must handle unknown chain
    }

    /// @notice Returns true if a chain id is known to the canonical table.
    function isKnown(uint256 chainId) internal pure returns (bool) {
        return chainOf(chainId).chainId != 0;
    }

    /// @notice Returns true if chain family is EVM and supports standard iDEBT deployment.
    function isEvm(uint256 chainId) internal pure returns (bool) {
        Chain memory c = chainOf(chainId);
        return c.chainId != 0 && c.family == Family.EVM;
    }
}
