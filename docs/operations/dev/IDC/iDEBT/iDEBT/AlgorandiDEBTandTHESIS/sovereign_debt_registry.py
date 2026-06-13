"""
Sovereign Debt Registry — Stage 1 Core (Basket Layer)
======================================================

On-chain registry of per-country sovereign debt and currency identifiers.
Provides the weighting input that the GlobalCurrencyBasket contract uses
to assign each currency's contribution to the global debasement signal.

A country with $38 trillion of sovereign debt (United States) should weigh
more in the basket than a country with $2 trillion (United Kingdom),
because the protocol's job is to short the systemic debasement of the
debt complex, not the bilateral move of any one pair.

Algorand-specific design notes:

    Each country record lives in a BoxMap keyed by a 3-byte ISO 4217
    currency code. Box storage is the natural fit because the number
    of countries is small (5-15 in production) and each record is
    read frequently by the basket contract.

    The deviation circuit breaker on updates is the same 20% cap used
    on EVM, looser than the GDSI oracle's 10% because debt figures
    jump on quarterly data releases from the IMF.

    Weight computation is done on-read from the registry rather than
    stored, so when reporters update country debt figures quarterly
    the basket re-weights automatically.
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
    subroutine,
)


class CountryRecord(arc4.Struct):
    """Per-country debt record. All amounts in USD-equivalent."""
    total_debt_usd_e6: arc4.UInt64     # sovereign debt in USD, 6 decimals
    gdp_usd_e6: arc4.UInt64           # nominal GDP in USD, 6 decimals
    debt_to_gdp_bps: arc4.UInt64      # ratio in basis points (10000 = 100%)
    last_updated: arc4.UInt64          # unix timestamp
    registered: arc4.Bool


class SovereignDebtRegistry(ARC4Contract):
    """
    On-chain registry of per-country sovereign debt providing basket weights.
    """

    BPS_DENOM = UInt64(10_000)
    MAX_DEVIATION_BPS = UInt64(2000)    # 20% max change per update

    def __init__(self) -> None:
        self.admin = GlobalState(Account)
        self.reporter = GlobalState(Account)

        # Total global sovereign debt in USD-equivalent (6 decimals).
        self.total_global_debt_e6 = GlobalState(UInt64)

        # Country count for iteration bounds.
        self.country_count = GlobalState(UInt64)

        # Currency code -> record. Keys are 3-byte ISO 4217 codes.
        self.records = BoxMap(Bytes, CountryRecord)

        # Currency code list stored as packed bytes in global state slots.
        # Each slot holds one 3-byte currency code. Max 16 currencies
        # (limited by global state slots available for iteration).
        # Stored in separate boxes for enumeration.
        self.currency_list = BoxMap(UInt64, Bytes)  # index -> 3-byte code

    @arc4.abimethod(create="require")
    def create(self, admin: Account, reporter: Account) -> None:
        """Initialize the registry."""
        self.admin.value = admin
        self.reporter.value = reporter
        self.total_global_debt_e6.value = UInt64(0)
        self.country_count.value = UInt64(0)

    # ------------------------------------------------------------------
    # REGISTRATION
    # ------------------------------------------------------------------

    @arc4.abimethod
    def register_country(
        self,
        currency_code: Bytes,
        total_debt_e6: UInt64,
        gdp_e6: UInt64,
    ) -> None:
        """
        Register a new country/currency in the basket. Admin only.
        Currency code must be exactly 3 bytes (ISO 4217).
        """
        assert Txn.sender == self.admin.value, "admin only"
        assert currency_code.length == UInt64(3), "code must be 3 bytes"
        assert total_debt_e6 > UInt64(0), "zero debt"
        assert gdp_e6 > UInt64(0), "zero gdp"
        assert currency_code not in self.records, "already registered"

        ratio_bps = (total_debt_e6 * self.BPS_DENOM) // gdp_e6

        self.records[currency_code] = CountryRecord(
            total_debt_usd_e6=arc4.UInt64(total_debt_e6),
            gdp_usd_e6=arc4.UInt64(gdp_e6),
            debt_to_gdp_bps=arc4.UInt64(ratio_bps),
            last_updated=arc4.UInt64(Global.latest_timestamp),
            registered=arc4.Bool(True),
        )

        # Add to enumerable list.
        idx = self.country_count.value
        self.currency_list[idx] = currency_code
        self.country_count.value = idx + UInt64(1)

        # Update global aggregate.
        self.total_global_debt_e6.value = (
            self.total_global_debt_e6.value + total_debt_e6
        )

    @arc4.abimethod
    def update_country(
        self,
        currency_code: Bytes,
        new_debt_e6: UInt64,
        new_gdp_e6: UInt64,
    ) -> None:
        """
        Update a country's debt and GDP figures. Reporter role.
        Quarterly cadence matching IMF release schedule.
        """
        assert (
            Txn.sender == self.reporter.value
            or Txn.sender == self.admin.value
        ), "reporter or admin"
        assert currency_code in self.records, "not registered"
        assert new_debt_e6 > UInt64(0), "zero debt"
        assert new_gdp_e6 > UInt64(0), "zero gdp"

        old_record = self.records[currency_code].copy()
        old_debt = old_record.total_debt_usd_e6.native

        # Deviation check.
        if new_debt_e6 > old_debt:
            deviation = ((new_debt_e6 - old_debt) * self.BPS_DENOM) // old_debt
        else:
            deviation = ((old_debt - new_debt_e6) * self.BPS_DENOM) // old_debt
        assert deviation <= self.MAX_DEVIATION_BPS, "deviation too large"

        # Update global aggregate.
        self.total_global_debt_e6.value = (
            self.total_global_debt_e6.value - old_debt + new_debt_e6
        )

        ratio_bps = (new_debt_e6 * self.BPS_DENOM) // new_gdp_e6

        self.records[currency_code] = CountryRecord(
            total_debt_usd_e6=arc4.UInt64(new_debt_e6),
            gdp_usd_e6=arc4.UInt64(new_gdp_e6),
            debt_to_gdp_bps=arc4.UInt64(ratio_bps),
            last_updated=arc4.UInt64(Global.latest_timestamp),
            registered=arc4.Bool(True),
        )

    @arc4.abimethod
    def delist_country(self, currency_code: Bytes) -> None:
        """Remove a country from the active basket."""
        assert Txn.sender == self.admin.value, "admin only"
        assert currency_code in self.records, "not registered"

        old_record = self.records[currency_code].copy()
        old_debt = old_record.total_debt_usd_e6.native

        self.total_global_debt_e6.value = (
            self.total_global_debt_e6.value - old_debt
        )

        # Mark as unregistered rather than deleting (preserves list indices).
        self.records[currency_code] = CountryRecord(
            total_debt_usd_e6=arc4.UInt64(0),
            gdp_usd_e6=arc4.UInt64(0),
            debt_to_gdp_bps=arc4.UInt64(0),
            last_updated=arc4.UInt64(Global.latest_timestamp),
            registered=arc4.Bool(False),
        )

    # ------------------------------------------------------------------
    # VIEWS
    # ------------------------------------------------------------------

    @arc4.abimethod(readonly=True)
    def weight_bps(self, currency_code: Bytes) -> UInt64:
        """
        Weight of a currency in the global debt basket, in basis points.
        Computed on-read from current debt figures.
        """
        assert currency_code in self.records, "not registered"
        rec = self.records[currency_code].copy()
        if not rec.registered.native:
            return UInt64(0)
        total = self.total_global_debt_e6.value
        if total == UInt64(0):
            return UInt64(0)
        return (rec.total_debt_usd_e6.native * self.BPS_DENOM) // total

    @arc4.abimethod(readonly=True)
    def get_record(self, currency_code: Bytes) -> CountryRecord:
        """Read a country's full record."""
        return self.records[currency_code].copy()

    @arc4.abimethod(readonly=True)
    def get_currency_at_index(self, idx: UInt64) -> Bytes:
        """Get a currency code by its list index."""
        return self.currency_list[idx]

    # ------------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------------

    @arc4.abimethod
    def set_reporter(self, new_reporter: Account) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.reporter.value = new_reporter

    @arc4.abimethod
    def transfer_admin(self, new_admin: Account) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.admin.value = new_admin
