"""Unit tests for the participant-tier deploy authorization gate."""

from agents.deployer.authorization import DeploymentAuthorization, tier_to_int

CFG = {
    "default": {"min_tier": "tier2", "rate_limit_per_hour": 3},
    "entities": {
        "guardian_agent_main": {
            "authorized_chains": ["anvil-local", "base"],
            "min_tier": "tier3", "rate_limit_per_hour": 10,
        }
    },
    "mainnet_required_approvers": ["guardian_agent_main"],
}


def _authz():
    return DeploymentAuthorization(CFG)


def test_tier_to_int():
    assert tier_to_int("tier0") == 0
    assert tier_to_int("tier4") == 4


def test_allow_when_tier_met():
    d = _authz().check(recovered_signer="0x1", entity_id="guardian_agent_main", tier=3,
                       chain="anvil-local", required_min_tier="tier2", is_mainnet=False)
    assert d.allowed and d.tier == 3


def test_reject_under_tier():
    # entity rule requires tier3; signer at tier2
    d = _authz().check(recovered_signer="0x1", entity_id="guardian_agent_main", tier=2,
                       chain="anvil-local", required_min_tier="tier2", is_mainnet=False)
    assert not d.allowed and "tier" in d.reason


def test_reject_unauthorized_chain():
    d = _authz().check(recovered_signer="0x1", entity_id="guardian_agent_main", tier=3,
                       chain="algorand-testnet", required_min_tier="tier2", is_mainnet=False)
    assert not d.allowed and "not authorized for chain" in d.reason


def test_reject_unknown_entity():
    d = _authz().check(recovered_signer="0xdead", entity_id=None, tier=0,
                       chain="anvil-local", required_min_tier="tier2", is_mainnet=False)
    assert not d.allowed and "no known participant" in d.reason


def test_mainnet_requires_operator_confirm():
    d = _authz().check(recovered_signer="0x1", entity_id="guardian_agent_main", tier=3,
                       chain="base", required_min_tier="tier2", is_mainnet=True)
    assert d.allowed and d.requires_operator_confirm


def test_default_fail_closed_when_unknown_entity_in_empty_cfg():
    # empty entities -> default min_tier tier2 applies; unknown entity rejected
    a = DeploymentAuthorization({"default": {"min_tier": "tier2", "rate_limit_per_hour": 3}, "entities": {}})
    d = a.check(recovered_signer="0x1", entity_id=None, tier=4, chain="x",
                required_min_tier="tier0", is_mainnet=False)
    assert not d.allowed
