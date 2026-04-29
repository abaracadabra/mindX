.PHONY: test-vault test-vault-rotate

# BANKON Vault — rotation contract tests.
# Invokes pytest with addopts cleared because the repo-wide --cov=mindx
# in pyproject.toml references a package that no longer exists. When the
# repo's coverage story gets fixed, drop the override.
PYTHON ?= .mindx_env/bin/python
PYTEST_VAULT_OPTS = --override-ini=addopts= -q

test-vault: test-vault-rotate

test-vault-rotate:
	$(PYTHON) -m pytest tests/bankon_vault/ $(PYTEST_VAULT_OPTS)
