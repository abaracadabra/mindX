"""
DELTAVERSE Algorand Stack — Deployment Script
==============================================

Deploys the four-stage contract stack in dependency order using AlgoKit.

Stage 1: Core (RWA controller + oracle hub)
Stage 2: Derivatives (vault + perp + coordinator)
Stage 3: Compliance (DELTAVERSE integrator)
Stage 4: Bridge (Wormhole RWA bridge)

Each stage can be deployed independently if previous stages already exist
on the target network — the script reads their app IDs from environment
variables and only deploys what's new.

Usage:
    # Full deployment to testnet
    python scripts/deploy.py --network testnet

    # Deploy only stage 4 using already-deployed stages 1-3
    export CORE_ORACLE_APP_ID=12345
    export VAULT_APP_ID=12346
    ...
    python scripts/deploy.py --network mainnet --stage 4
"""

import argparse
import os
from pathlib import Path

from algokit_utils import (
    AlgorandClient,
    AppClient,
    AppFactory,
    CommonAppCallParams,
    TransactionComposer,
    Config,
)


CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"


def deploy_stage1_core(algorand: AlgorandClient, deployer_address: str) -> dict:
    """Deploy RWA controller and oracle hub."""
    print("\n=== STAGE 1: CORE ===")

    # RWA Controller
    print("Deploying RWAController...")
    rwa_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage1_core" / "rwa_controller.py"
    )
    rwa_client = rwa_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "compliance_officer": deployer_address,
                "yield_token": int(os.environ.get("USDC_ASA_ID", "0")),
                "maturity_ts": 4_102_444_800,  # Jan 2100
                "coupon_bps": 400,
                "supply_cap": 100_000_000_000_000,
            }
        }
    )
    print(f"  RWAController app ID: {rwa_client.app_id}")
    print(f"  RWAController address: {rwa_client.app_address}")

    # Oracle Hub
    print("Deploying RWAOracleHub...")
    oracle_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage1_core" / "rwa_oracle_hub.py"
    )
    oracle_client = oracle_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "governor": deployer_address,
            }
        }
    )
    print(f"  RWAOracleHub app ID: {oracle_client.app_id}")

    return {
        "rwa_controller_app_id": rwa_client.app_id,
        "oracle_app_id": oracle_client.app_id,
    }


def deploy_stage2_derivatives(
    algorand: AlgorandClient,
    deployer_address: str,
    core_addresses: dict,
) -> dict:
    """Deploy vault, perp, coordinator."""
    print("\n=== STAGE 2: DERIVATIVES ===")

    usdc_asa = int(os.environ.get("USDC_ASA_ID", "0"))

    # Vault
    print("Deploying CollateralVault...")
    vault_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage2_derivatives" / "collateral_vault.py"
    )
    vault_client = vault_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "stablecoin_asset_id": usdc_asa,
                "borrow_rate_bps": 400,
            }
        }
    )
    print(f"  CollateralVault app ID: {vault_client.app_id}")

    # Perpetual Engine
    print("Deploying PerpetualEngine...")
    perp_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage2_derivatives" / "perpetual_engine.py"
    )
    perp_client = perp_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "stablecoin_asset_id": usdc_asa,
                "oracle_app_id": core_addresses["oracle_app_id"],
            }
        }
    )
    print(f"  PerpetualEngine app ID: {perp_client.app_id}")

    # Coordinator
    print("Deploying DebtInheritanceCoordinator...")
    coord_factory = AppFactory.from_path(
        algorand,
        CONTRACTS_DIR / "stage2_derivatives" / "debt_inheritance_coordinator.py"
    )
    coord_client = coord_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "stablecoin_asset_id": usdc_asa,
                "oracle_app_id": core_addresses["oracle_app_id"],
                "vault_app_id": vault_client.app_id,
                "perp_app_id": perp_client.app_id,
            }
        }
    )
    print(f"  DebtInheritanceCoordinator app ID: {coord_client.app_id}")

    return {
        "vault_app_id": vault_client.app_id,
        "perp_app_id": perp_client.app_id,
        "coordinator_app_id": coord_client.app_id,
    }


def deploy_stage3_compliance(
    algorand: AlgorandClient,
    deployer_address: str,
) -> dict:
    """Deploy compliance integrator."""
    print("\n=== STAGE 3: COMPLIANCE ===")

    # The four DELTAVERSE subsystem app IDs come from env vars.
    algoidnft_app = int(os.environ.get("ALGOIDNFT_APP_ID", "0"))
    bonafide_app = int(os.environ.get("BONAFIDE_APP_ID", "0"))
    daio_app = int(os.environ.get("DAIO_APP_ID", "0"))
    x402_app = int(os.environ.get("X402_APP_ID", "0"))

    print("Deploying ComplianceIntegrator...")
    compliance_factory = AppFactory.from_path(
        algorand,
        CONTRACTS_DIR / "stage3_compliance" / "compliance_integrator.py"
    )
    compliance_client = compliance_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "algoidnft_app": algoidnft_app,
                "bonafide_app": bonafide_app,
                "daio_app": daio_app,
                "x402_app": x402_app,
            }
        }
    )
    print(f"  ComplianceIntegrator app ID: {compliance_client.app_id}")

    return {"compliance_app_id": compliance_client.app_id}


def deploy_stage4_bridge(
    algorand: AlgorandClient,
    deployer_address: str,
) -> dict:
    """Deploy Wormhole bridge."""
    print("\n=== STAGE 4: BRIDGE ===")

    wormhole_core = int(os.environ.get("WORMHOLE_CORE_APP_ID", "0"))

    print("Deploying WormholeBridge...")
    bridge_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage4_bridge" / "wormhole_bridge.py"
    )
    bridge_client = bridge_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "governor": deployer_address,
                "wormhole_core_app": wormhole_core,
            }
        }
    )
    print(f"  WormholeBridge app ID: {bridge_client.app_id}")

    return {"bridge_app_id": bridge_client.app_id}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        choices=["localnet", "testnet", "mainnet"],
        default="testnet",
    )
    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 0],
        default=0,
        help="Deploy specific stage only; 0=all, 5=basket, 6=idebt",
    )
    args = parser.parse_args()

    # Get algorand client for the target network.
    if args.network == "localnet":
        algorand = AlgorandClient.default_localnet()
    elif args.network == "testnet":
        algorand = AlgorandClient.testnet()
    else:
        algorand = AlgorandClient.mainnet()

    deployer = algorand.account.from_environment("DEPLOYER")
    deployer_address = deployer.address

    print(f"Deployer: {deployer_address}")
    print(f"Network: {args.network}")

    addresses = {}

    if args.stage in (0, 1):
        addresses.update(deploy_stage1_core(algorand, deployer_address))
    else:
        addresses["oracle_app_id"] = int(os.environ["ORACLE_APP_ID"])

    if args.stage in (0, 2):
        addresses.update(deploy_stage2_derivatives(
            algorand, deployer_address, addresses
        ))

    if args.stage in (0, 3):
        addresses.update(deploy_stage3_compliance(algorand, deployer_address))

    if args.stage in (0, 4):
        addresses.update(deploy_stage4_bridge(algorand, deployer_address))

    # Stage 1b: Basket Layer (depends on Stage 1 oracle hub)
    if args.stage in (0, 5):
        addresses.update(deploy_basket_layer(algorand, deployer_address, addresses))

    # Stage 2b: Inverse Debt (depends on Stage 1b basket + Stage 2 coordinator)
    if args.stage in (0, 6):
        addresses.update(deploy_inverse_debt(algorand, deployer_address, addresses))

    print("\n==============================================")
    print("DEPLOYMENT COMPLETE")
    print("==============================================")
    for name, app_id in addresses.items():
        print(f"  {name}: {app_id}")
    print("\nPOST-DEPLOYMENT CHECKLIST:")
    print("  [ ]  1. Issue RWA ASA via rwa_controller.issue_asa()")
    print("  [ ]  2. Configure 5 sub-indices on oracle hub")
    print("  [ ]  3. Authorize reporter accounts on oracle hub")
    print("  [ ]  4. Opt vault into USDC and RWA ASAs")
    print("  [ ]  5. Register RWA ASA as collateral in vault")
    print("  [ ]  6. Seed perp engine insurance fund")
    print("  [ ]  7. Issue sGDSI ASA via coordinator.issue_sgdsi_asa()")
    print("  [ ]  8. Register peer bridges in bridge (Ethereum chain ID 2)")
    print("  [ ]  9. Set epoch limits on bridge")
    print("  [ ] 10. Seed sovereign debt registry with 5 major currencies")
    print("  [ ] 11. Configure basket FX oracle sub-index IDs")
    print("  [ ] 12. Initialize basket baseline with current prices")
    print("  [ ] 13. Issue iDEBT ASA via inverse_debt.issue_idebt_asa()")
    print("  [ ] 14. Set iDEBT reporter to authorized keeper")
    print("  [ ] 15. Top up iDEBT reserve with initial stablecoin")
    print("  [ ] 16. Transfer admin roles to DAIO governance app")


def deploy_basket_layer(
    algorand: AlgorandClient,
    deployer_address: str,
    existing: dict,
) -> dict:
    """Deploy sovereign debt registry and global currency basket."""
    print("\n=== STAGE 1b: BASKET LAYER ===")

    usdc_asa = int(os.environ.get("USDC_ASA_ID", "0"))

    # Sovereign Debt Registry
    print("Deploying SovereignDebtRegistry...")
    registry_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage1_core" / "sovereign_debt_registry.py"
    )
    registry_client = registry_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "reporter": deployer_address,
            }
        }
    )
    print(f"  SovereignDebtRegistry app ID: {registry_client.app_id}")

    # Global Currency Basket
    print("Deploying GlobalCurrencyBasket...")
    oracle_app = existing.get("oracle_app_id", int(os.environ.get("ORACLE_APP_ID", "0")))
    basket_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage1_core" / "global_currency_basket.py"
    )
    basket_client = basket_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "oracle_hub_app_id": oracle_app,
                "registry_app_id": registry_client.app_id,
                "btc_sub_index_id": 0,  # BTC/USD is sub-index 0 by convention
            }
        }
    )
    print(f"  GlobalCurrencyBasket app ID: {basket_client.app_id}")

    return {
        "registry_app_id": registry_client.app_id,
        "basket_app_id": basket_client.app_id,
    }


def deploy_inverse_debt(
    algorand: AlgorandClient,
    deployer_address: str,
    existing: dict,
) -> dict:
    """Deploy inverse debt token."""
    print("\n=== STAGE 2b: INVERSE DEBT ===")

    usdc_asa = int(os.environ.get("USDC_ASA_ID", "0"))

    print("Deploying InverseDebtToken...")
    idebt_factory = AppFactory.from_path(
        algorand, CONTRACTS_DIR / "stage2_derivatives" / "inverse_debt_token.py"
    )
    idebt_client = idebt_factory.deploy(
        create_params={
            "args": {
                "admin": deployer_address,
                "reporter": deployer_address,
                "stablecoin_asset_id": usdc_asa,
                "mint_fee_bps": 30,
                "burn_fee_bps": 30,
                "reserve_share_bps": 5000,
                "max_index_age": 21600,  # 6 hours
            }
        }
    )
    print(f"  InverseDebtToken app ID: {idebt_client.app_id}")

    return {"idebt_app_id": idebt_client.app_id}


if __name__ == "__main__":
    main()
