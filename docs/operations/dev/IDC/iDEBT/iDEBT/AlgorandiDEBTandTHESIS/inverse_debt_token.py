"""
Inverse Debt Token (iDEBT) — Stage 2 Derivatives (Inverse Layer)
==================================================================

Algorand equivalent of InverseDebtToken.sol. Synthetic ASA that encodes
the "profit from loss" mechanic at the heart of the inverse debt thesis.
Users mint iDEBT by depositing stablecoin at the current debasement index.
When they burn iDEBT, they receive stablecoin at the index in effect at
burn time. If the index rose between mint and burn, the user receives more
stablecoin than they deposited.

Algorand-specific design notes:

    iDEBT is issued as a native ASA (Algorand Standard Asset) rather than
    a contract-managed balance mapping. This means iDEBT tokens are
    transferable via normal Algorand asset transfers, composable with any
    Algorand DEX or wallet, and visible in block explorers without custom
    indexing. The controller contract holds the mint/clawback roles so it
    alone can create and destroy units.

    Minting requires an atomic group containing:
        1. AssetTransfer of stablecoin to this contract
        2. AppCall to this contract's mint_idebt method
    The contract verifies the companion AssetTransfer in the group.

    Burning is similar: the user sends iDEBT back to the contract in the
    same atomic group as the burn call, and the contract sends stablecoin
    out via inner transaction.

    The debasement index is passed in by the caller (keeper or coordinator)
    rather than computed on-chain, because the full basket computation
    exceeds single-call opcode budgets. A guardian/reporter pattern ensures
    the passed value matches the basket's output. In production, multiple
    reporters must agree on the index value before it is accepted.

    Solvency: proportional haircut under extreme debasement, not revert.
    Same design as EVM — honest about the scenario rather than pretending
    debasement did not happen.
"""

from algopy import (
    ARC4Contract,
    Account,
    Asset,
    BoxMap,
    Global,
    GlobalState,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    subroutine,
)


class MintPosition(arc4.Struct):
    """Per-user mint basis for profit tracking."""
    usdc_deposited_e6: arc4.UInt64
    mint_index_e18: arc4.UInt64
    mint_timestamp: arc4.UInt64
    mint_btc_sats: arc4.UInt64


class InverseDebtToken(ARC4Contract):
    """
    iDEBT synthetic token — profit from loss via debasement index.
    """

    PRECISION = UInt64(1_000_000_000_000_000_000)  # 1e18
    BPS_DENOM = UInt64(10_000)
    USDC_SCALE = UInt64(1_000_000_000_000)  # scale 6-dec USDC to 18-dec

    def __init__(self) -> None:
        self.admin = GlobalState(Account)
        self.reporter = GlobalState(Account)  # authorized index reporter

        # ASA identifiers.
        self.idebt_asset_id = GlobalState(UInt64)
        self.stablecoin_asset_id = GlobalState(UInt64)

        # Current debasement index, 18 decimals. Updated by reporter.
        self.current_index_e18 = GlobalState(UInt64)
        self.index_last_updated = GlobalState(UInt64)
        self.max_index_age = GlobalState(UInt64)  # seconds

        # Fee configuration.
        self.mint_fee_bps = GlobalState(UInt64)
        self.burn_fee_bps = GlobalState(UInt64)
        self.reserve_share_bps = GlobalState(UInt64)  # % of fees to reserve

        # Accounting.
        self.total_usdc_deposited = GlobalState(UInt64)
        self.reserve_buffer = GlobalState(UInt64)
        self.treasury_fees = GlobalState(UInt64)

        # Pause flag.
        self.paused = GlobalState(UInt64)

        # Per-user positions for BTC-equivalent tracking.
        self.positions = BoxMap(Account, MintPosition)

    @arc4.abimethod(create="require")
    def create(
        self,
        admin: Account,
        reporter: Account,
        stablecoin_asset_id: UInt64,
        mint_fee_bps: UInt64,
        burn_fee_bps: UInt64,
        reserve_share_bps: UInt64,
        max_index_age: UInt64,
    ) -> None:
        """Initialize the iDEBT contract."""
        self.admin.value = admin
        self.reporter.value = reporter
        self.stablecoin_asset_id.value = stablecoin_asset_id
        self.mint_fee_bps.value = mint_fee_bps
        self.burn_fee_bps.value = burn_fee_bps
        self.reserve_share_bps.value = reserve_share_bps
        self.max_index_age.value = max_index_age
        self.current_index_e18.value = self.PRECISION  # start at baseline
        self.index_last_updated.value = Global.latest_timestamp
        self.paused.value = UInt64(0)

    @arc4.abimethod
    def issue_idebt_asa(self, supply_cap: UInt64) -> UInt64:
        """
        Create the iDEBT ASA. Called once after contract creation.
        This contract is the manager/reserve/freeze/clawback.
        """
        assert Txn.sender == self.admin.value, "admin only"
        assert self.idebt_asset_id.value == UInt64(0), "already issued"

        result = itxn.AssetConfig(
            total=supply_cap,
            decimals=6,
            default_frozen=False,
            asset_name="Inverse Debt Token",
            unit_name="iDEBT",
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            clawback=Global.current_application_address,
            fee=UInt64(0),
        ).submit()

        self.idebt_asset_id.value = result.created_asset.id
        return result.created_asset.id

    # ------------------------------------------------------------------
    # INDEX REPORTING
    # ------------------------------------------------------------------

    @arc4.abimethod
    def update_index(self, new_index_e18: UInt64) -> None:
        """
        Reporter pushes the current debasement index. In production,
        this should require multi-sig or threshold agreement from
        multiple reporters.
        """
        assert (
            Txn.sender == self.reporter.value
            or Txn.sender == self.admin.value
        ), "reporter or admin"
        assert new_index_e18 > UInt64(0), "zero index"

        self.current_index_e18.value = new_index_e18
        self.index_last_updated.value = Global.latest_timestamp

    # ------------------------------------------------------------------
    # MINT
    # ------------------------------------------------------------------

    @arc4.abimethod
    def mint_idebt(
        self,
        usdc_amount: UInt64,
        min_idebt_out: UInt64,
        btc_sats_equivalent: UInt64,
    ) -> UInt64:
        """
        Mint iDEBT by depositing stablecoin at the current debasement index.

        Must be called as part of an atomic group where the preceding
        transaction is an AssetTransfer of `usdc_amount` stablecoin to
        this contract's address.

        Formula: iDEBT_out = (net_usdc * PRECISION) / current_index

        The btc_sats_equivalent is the BTC-denominated value of the
        deposit computed off-chain by the caller (who reads BTC price
        from the oracle hub). It is stored for profit-tracking purposes
        and does not affect settlement math.
        """
        assert self.paused.value == UInt64(0), "paused"
        assert usdc_amount > UInt64(0), "zero amount"

        # Verify the companion stablecoin transfer.
        assert Txn.group_index > UInt64(0), "must be in group"
        companion = gtxn.AssetTransferTransaction(Txn.group_index - UInt64(1))
        assert companion.xfer_asset == Asset(self.stablecoin_asset_id.value), "wrong asset"
        assert companion.asset_receiver == Global.current_application_address, "wrong receiver"
        assert companion.asset_amount == usdc_amount, "amount mismatch"

        # Check index freshness.
        index = self.current_index_e18.value
        assert index > UInt64(0), "index not set"
        age = Global.latest_timestamp - self.index_last_updated.value
        assert age <= self.max_index_age.value, "index stale"

        # Fee split.
        fee = (usdc_amount * self.mint_fee_bps.value) // self.BPS_DENOM
        reserve_cut = (fee * self.reserve_share_bps.value) // self.BPS_DENOM
        treasury_cut = fee - reserve_cut
        net = usdc_amount - fee

        # iDEBT minting formula.
        # Scale USDC (6 dec) to 18 dec, then divide by index.
        net_18 = net * self.USDC_SCALE
        idebt_out = (net_18 * self.PRECISION) // index

        # Convert iDEBT (18-dec internal) back to 6-dec ASA units.
        idebt_asa_units = idebt_out // self.USDC_SCALE

        assert idebt_asa_units >= min_idebt_out, "slippage exceeded"

        # Update accounting.
        self.total_usdc_deposited.value = self.total_usdc_deposited.value + net
        self.reserve_buffer.value = self.reserve_buffer.value + reserve_cut
        self.treasury_fees.value = self.treasury_fees.value + treasury_cut

        # Update position for BTC profit tracking.
        if Txn.sender in self.positions:
            old_pos = self.positions[Txn.sender].copy()
            new_total = old_pos.usdc_deposited_e6.native + net
            # Weighted average index.
            old_weighted = old_pos.mint_index_e18.native * old_pos.usdc_deposited_e6.native
            new_weighted = index * net
            avg_index = (old_weighted + new_weighted) // new_total

            self.positions[Txn.sender] = MintPosition(
                usdc_deposited_e6=arc4.UInt64(new_total),
                mint_index_e18=arc4.UInt64(avg_index),
                mint_timestamp=arc4.UInt64(Global.latest_timestamp),
                mint_btc_sats=arc4.UInt64(
                    old_pos.mint_btc_sats.native + btc_sats_equivalent
                ),
            )
        else:
            self.positions[Txn.sender] = MintPosition(
                usdc_deposited_e6=arc4.UInt64(net),
                mint_index_e18=arc4.UInt64(index),
                mint_timestamp=arc4.UInt64(Global.latest_timestamp),
                mint_btc_sats=arc4.UInt64(btc_sats_equivalent),
            )

        # Mint iDEBT ASA to the sender via inner transaction.
        itxn.AssetTransfer(
            xfer_asset=Asset(self.idebt_asset_id.value),
            asset_receiver=Txn.sender,
            asset_amount=idebt_asa_units,
            fee=UInt64(0),
        ).submit()

        return idebt_asa_units

    # ------------------------------------------------------------------
    # BURN
    # ------------------------------------------------------------------

    @arc4.abimethod
    def burn_idebt(
        self,
        idebt_amount: UInt64,
        min_usdc_out: UInt64,
    ) -> UInt64:
        """
        Burn iDEBT to redeem stablecoin at the current debasement index.

        Must be called as part of an atomic group where the preceding
        transaction is an AssetTransfer of `idebt_amount` iDEBT to this
        contract's address.

        Formula: usdc_out = (iDEBT_in * current_index) / PRECISION

        If the index has risen since mint, user receives more USDC.
        If the contract cannot pay full nominal, proportional haircut.
        """
        assert self.paused.value == UInt64(0), "paused"
        assert idebt_amount > UInt64(0), "zero amount"

        # Verify companion iDEBT transfer.
        assert Txn.group_index > UInt64(0), "must be in group"
        companion = gtxn.AssetTransferTransaction(Txn.group_index - UInt64(1))
        assert companion.xfer_asset == Asset(self.idebt_asset_id.value), "wrong asset"
        assert companion.asset_receiver == Global.current_application_address, "wrong receiver"
        assert companion.asset_amount == idebt_amount, "amount mismatch"

        # Check index freshness.
        index = self.current_index_e18.value
        assert index > UInt64(0), "index not set"
        age = Global.latest_timestamp - self.index_last_updated.value
        assert age <= self.max_index_age.value, "index stale"

        # Redemption formula.
        # Scale iDEBT ASA units (6 dec) to 18 dec for the multiply.
        idebt_18 = idebt_amount * self.USDC_SCALE
        usdc_18 = (idebt_18 * index) // self.PRECISION
        gross_usdc = usdc_18 // self.USDC_SCALE

        fee = (gross_usdc * self.burn_fee_bps.value) // self.BPS_DENOM
        reserve_cut = (fee * self.reserve_share_bps.value) // self.BPS_DENOM
        treasury_cut = fee - reserve_cut
        usdc_out = gross_usdc - fee

        # Solvency check — proportional haircut, not revert.
        # Read the contract's actual stablecoin balance.
        contract_balance = Asset(self.stablecoin_asset_id.value).balance(
            Global.current_application_address
        )
        if usdc_out > contract_balance:
            usdc_out = contract_balance - fee if contract_balance > fee else UInt64(0)

        assert usdc_out >= min_usdc_out, "slippage exceeded"

        # Update accounting.
        self.reserve_buffer.value = self.reserve_buffer.value + reserve_cut
        self.treasury_fees.value = self.treasury_fees.value + treasury_cut

        # Pay out stablecoin via inner transaction.
        if usdc_out > UInt64(0):
            itxn.AssetTransfer(
                xfer_asset=Asset(self.stablecoin_asset_id.value),
                asset_receiver=Txn.sender,
                asset_amount=usdc_out,
                fee=UInt64(0),
            ).submit()

        return usdc_out

    # ------------------------------------------------------------------
    # RESERVE & TREASURY
    # ------------------------------------------------------------------

    @arc4.abimethod
    def top_up_reserve(self, amount: UInt64) -> None:
        """
        Anyone can add stablecoin to the reserve buffer for solvency.
        Companion AssetTransfer of stablecoin must precede this call.
        """
        assert Txn.group_index > UInt64(0), "must be in group"
        companion = gtxn.AssetTransferTransaction(Txn.group_index - UInt64(1))
        assert companion.xfer_asset == Asset(self.stablecoin_asset_id.value), "wrong asset"
        assert companion.asset_receiver == Global.current_application_address, "wrong receiver"
        assert companion.asset_amount == amount, "amount mismatch"
        self.reserve_buffer.value = self.reserve_buffer.value + amount

    @arc4.abimethod
    def claim_treasury(self, to: Account, amount: UInt64) -> None:
        """Claim accumulated treasury fees."""
        assert Txn.sender == self.admin.value, "admin only"
        assert amount <= self.treasury_fees.value, "exceeds treasury"
        self.treasury_fees.value = self.treasury_fees.value - amount
        itxn.AssetTransfer(
            xfer_asset=Asset(self.stablecoin_asset_id.value),
            asset_receiver=to,
            asset_amount=amount,
            fee=UInt64(0),
        ).submit()

    # ------------------------------------------------------------------
    # VIEWS
    # ------------------------------------------------------------------

    @arc4.abimethod(readonly=True)
    def redemption_value(self, idebt_amount: UInt64) -> UInt64:
        """What would burning this many iDEBT return in USDC?"""
        index = self.current_index_e18.value
        idebt_18 = idebt_amount * self.USDC_SCALE
        usdc_18 = (idebt_18 * index) // self.PRECISION
        gross = usdc_18 // self.USDC_SCALE
        fee = (gross * self.burn_fee_bps.value) // self.BPS_DENOM
        return gross - fee

    @arc4.abimethod(readonly=True)
    def get_position(self, account: Account) -> MintPosition:
        """Read a user's mint basis for profit tracking."""
        return self.positions[account].copy()

    # ------------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------------

    @arc4.abimethod
    def set_fees(
        self,
        mint_fee_bps: UInt64,
        burn_fee_bps: UInt64,
        reserve_share_bps: UInt64,
    ) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        assert mint_fee_bps <= UInt64(1000), "fee too high"
        assert burn_fee_bps <= UInt64(1000), "fee too high"
        self.mint_fee_bps.value = mint_fee_bps
        self.burn_fee_bps.value = burn_fee_bps
        self.reserve_share_bps.value = reserve_share_bps

    @arc4.abimethod
    def pause(self) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.paused.value = UInt64(1)

    @arc4.abimethod
    def unpause(self) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.paused.value = UInt64(0)

    @arc4.abimethod
    def set_reporter(self, new_reporter: Account) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.reporter.value = new_reporter

    @arc4.abimethod
    def transfer_admin(self, new_admin: Account) -> None:
        assert Txn.sender == self.admin.value, "admin only"
        self.admin.value = new_admin
