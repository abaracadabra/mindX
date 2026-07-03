"""
Global Currency Basket — Stage 1 Core (Basket Layer)
======================================================

Aggregates multiple fiat-vs-BTC price ratios into a single weighted index
of global fiat strength relative to Bitcoin. Weights come from the
SovereignDebtRegistry. The result captures debasement of the debt complex
as a whole, not just bilateral movement of any single pair.

This is the Algorand equivalent of GlobalCurrencyBasket.sol on EVM.

Algorand-specific design notes:

    On EVM, the basket reads Chainlink fx feeds directly via interface
    calls. On Algorand, there are no native Chainlink aggregators. Instead,
    the basket reads from the RWA Oracle Hub (stage 1 core), which
    implements a hybrid push-pull model where oracle runners push periodic
    attestations and consumers can request on-demand updates.

    Each currency's FX rate is stored as a sub-index in the oracle hub.
    The basket contract stores a mapping from currency code to the oracle
    hub's sub-index ID for that currency's C/USD rate. This indirection
    lets the oracle hub manage staleness, deviation checks, and reporter
    authorization independently of the basket.

    BTC/USD is another sub-index in the same oracle hub. The basket reads
    it once per computation and uses it to derive BTC/C for each currency.

    The fiat debasement index is the reciprocal of the fiat strength index.
    When fiat weakens against BTC, debasement rises. The DebasementIndexV2
    equivalent (the coordinator's index computation) consumes this signal.
"""

from algopy import (
    ARC4Contract,
    Account,
    BoxMap,
    Bytes,
    Global,
    GlobalState,
    Txn,
    UInt64,
    arc4,
    itxn,
    subroutine,
)


class CurrencyConfig(arc4.Struct):
    """Per-currency oracle configuration."""
    oracle_sub_index_id: arc4.UInt8   # sub-index in oracle hub for C/USD
    max_staleness_s: arc4.UInt32
    baseline_btc_per_c_e18: arc4.UInt64   # BTC price in currency C at baseline
    enabled: arc4.Bool


class GlobalCurrencyBasket(ARC4Contract):
    """
    Weighted multi-currency fiat-vs-BTC basket measurement.
    """

    PRECISION = UInt64(1_000_000_000_000_000_000)  # 1e18
    BPS_DENOM = UInt64(10_000)

    def __init__(self) -> None:
        self.admin = GlobalState(Account)

        # Oracle hub app ID — provides all fx rates and BTC price.
        self.oracle_hub_app_id = GlobalState(UInt64)

        # Sovereign debt registry app ID — provides basket weights.
        self.registry_app_id = GlobalState(UInt64)

        # BTC/USD sub-index ID in the oracle hub.
        self.btc_sub_index_id = GlobalState(UInt64)

        # Per-currency config. Key = 3-byte ISO currency code.
        self.configs = BoxMap(Bytes, CurrencyConfig)

        # Baseline BTC/USD price at initialization, 18 decimals.
        self.baseline_btc_usd_e18 = GlobalState(UInt64)

        # Initialization flag.
        self.initialized = GlobalState(UInt64)

        # Number of configured currencies.
        self.currency_count = GlobalState(UInt64)

        # Currency list for iteration.
        self.currency_list = BoxMap(UInt64, Bytes)

    @arc4.abimethod(create="require")
    def create(
        self,
        admin: Account,
        oracle_hub_app_id: UInt64,
        registry_app_id: UInt64,
        btc_sub_index_id: UInt64,
    ) -> None:
        """Initialize the basket contract."""
        self.admin.value = admin
        self.oracle_hub_app_id.value = oracle_hub_app_id
        self.registry_app_id.value = registry_app_id
        self.btc_sub_index_id.value = btc_sub_index_id
        self.initialized.value = UInt64(0)
        self.currency_count.value = UInt64(0)

    # ------------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------------

    @arc4.abimethod
    def configure_currency(
        self,
        currency_code: Bytes,
        oracle_sub_index_id: UInt64,
        max_staleness_s: UInt64,
    ) -> None:
        """
        Register a currency for basket inclusion. Must be called before
        initialize_baseline.
        """
        assert Txn.sender == self.admin.value, "admin only"
        assert currency_code.length == UInt64(3), "code must be 3 bytes"
        assert self.initialized.value == UInt64(0), "already initialized"

        self.configs[currency_code] = CurrencyConfig(
            oracle_sub_index_id=arc4.UInt8(oracle_sub_index_id),
            max_staleness_s=arc4.UInt32(max_staleness_s),
            baseline_btc_per_c_e18=arc4.UInt64(0),
            enabled=arc4.Bool(True),
        )

        idx = self.currency_count.value
        self.currency_list[idx] = currency_code
        self.currency_count.value = idx + UInt64(1)

    @arc4.abimethod
    def initialize_baseline(
        self,
        btc_usd_e18: UInt64,
        fx_rates_e18: arc4.DynamicArray[arc4.UInt64],
    ) -> None:
        """
        Lock baseline values for all configured currencies. Single-shot.

        Because Algorand contracts cannot make arbitrary cross-app reads
        for arbitrary numbers of sub-indices in one call (opcode budget),
        the baselines are passed in by the deployer who reads them off-chain
        from the oracle hub.

        fx_rates_e18 is ordered to match the currency_list indices.
        Each value is "how many units of currency C per 1 USD", 18 decimals.
        """
        assert Txn.sender == self.admin.value, "admin only"
        assert self.initialized.value == UInt64(0), "already initialized"
        assert btc_usd_e18 > UInt64(0), "btc price zero"

        self.baseline_btc_usd_e18.value = btc_usd_e18

        count = self.currency_count.value
        assert fx_rates_e18.length == count, "wrong number of fx rates"

        idx = UInt64(0)
        while idx < count:
            code = self.currency_list[idx]
            cfg = self.configs[code].copy()
            fx_per_usd = fx_rates_e18[idx].native
            assert fx_per_usd > UInt64(0), "fx rate zero"

            # BTC priced in C = btc_usd * fx_per_usd / 1e18
            btc_per_c = (btc_usd_e18 * fx_per_usd) // self.PRECISION

            self.configs[code] = CurrencyConfig(
                oracle_sub_index_id=cfg.oracle_sub_index_id,
                max_staleness_s=cfg.max_staleness_s,
                baseline_btc_per_c_e18=arc4.UInt64(btc_per_c),
                enabled=cfg.enabled,
            )
            idx += UInt64(1)

        self.initialized.value = UInt64(1)

    # ------------------------------------------------------------------
    # BASKET MEASUREMENT
    # ------------------------------------------------------------------

    @arc4.abimethod
    def compute_fiat_debasement(
        self,
        current_btc_usd_e18: UInt64,
        current_fx_rates_e18: arc4.DynamicArray[arc4.UInt64],
        weights_bps: arc4.DynamicArray[arc4.UInt16],
    ) -> UInt64:
        """
        Compute the basket-weighted fiat debasement index.

        Because Algorand contracts have limited opcode budgets for cross-app
        reads, the caller (typically a keeper or the coordinator contract)
        pre-fetches the current prices and weights and passes them in. The
        contract validates structural integrity but trusts the caller's
        data freshness. For production hardening, a guardian pattern can
        be layered on top where multiple reporters must agree.

        Returns the debasement index in 1e18 fixed point. Value > 1e18
        means fiat has weakened against BTC since baseline.

        Parameters:
            current_btc_usd_e18: Current BTC/USD price, 18 decimals
            current_fx_rates_e18: Current C/USD rates per currency, 18 dec
            weights_bps: Per-currency basket weights from registry, bps
        """
        assert self.initialized.value == UInt64(1), "not initialized"
        assert current_btc_usd_e18 > UInt64(0), "btc price zero"

        count = self.currency_count.value
        assert current_fx_rates_e18.length == count, "fx count mismatch"
        assert weights_bps.length == count, "weight count mismatch"

        weighted_sum = UInt64(0)
        total_weight = UInt64(0)

        idx = UInt64(0)
        while idx < count:
            code = self.currency_list[idx]
            cfg = self.configs[code].copy()

            if cfg.enabled.native and cfg.baseline_btc_per_c_e18.native > UInt64(0):
                fx_per_usd = current_fx_rates_e18[idx].native
                w = weights_bps[idx].native

                if fx_per_usd > UInt64(0) and w > UInt64(0):
                    # Current BTC priced in C.
                    current_btc_per_c = (
                        (current_btc_usd_e18 * fx_per_usd) // self.PRECISION
                    )

                    if current_btc_per_c > UInt64(0):
                        # Strength ratio: baseline / current.
                        # > 1e18 means fiat strengthened.
                        strength_ratio = (
                            (cfg.baseline_btc_per_c_e18.native * self.PRECISION)
                            // current_btc_per_c
                        )

                        weighted_sum = weighted_sum + strength_ratio * w
                        total_weight = total_weight + w

            idx += UInt64(1)

        assert total_weight > UInt64(0), "no live sources"

        # Fiat strength index.
        strength = weighted_sum // total_weight

        # Debasement = 1 / strength = PRECISION^2 / strength.
        assert strength > UInt64(0), "strength zero"
        debasement = (self.PRECISION * self.PRECISION) // strength

        return debasement

    # ------------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------------

    @arc4.abimethod
    def disable_currency(self, currency_code: Bytes) -> None:
        """Disable a currency from basket computation without deleting."""
        assert Txn.sender == self.admin.value, "admin only"
        assert currency_code in self.configs, "not configured"
        cfg = self.configs[currency_code].copy()
        self.configs[currency_code] = CurrencyConfig(
            oracle_sub_index_id=cfg.oracle_sub_index_id,
            max_staleness_s=cfg.max_staleness_s,
            baseline_btc_per_c_e18=cfg.baseline_btc_per_c_e18,
            enabled=arc4.Bool(False),
        )

    @arc4.abimethod
    def transfer_admin(self, new_admin: Account) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.admin.value = new_admin
