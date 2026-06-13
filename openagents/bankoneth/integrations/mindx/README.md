# bankoneth — mindX integration

Drop-in mindX BaseTool wrapper around the `@bankoneth/cli` command. Registered
under `bankoneth_tool`. Lets mindX agents claim their own `bankon.eth` subname,
derive their ERC-6551 TBA wallet, and optionally publish a marketplace listing
on agenticplace.pythai.net.

## Install

The bankoneth Python package is published from `openagents/bankoneth/pyproject.toml`.
From inside the mindX project:

```bash
pip install -e /home/hacker/mindX/openagents/bankoneth
```

## Register with mindX's tool registry

```python
from openagents.bankoneth.integrations.mindx import BankonethTool

tool = BankonethTool(BankonethToolConfig(
    cli_path="/usr/local/bin/bankoneth",       # or the dist/index.js path
    rpc_url=os.environ["BANKONETH_RPC_URL"],
    chain="mainnet",
    addresses_json="/etc/bankoneth/addresses.json",
))
tool_registry.register(tool)
```

## Agent calls

```python
result = await tool.execute(
    action="claim",
    label="agent-001",
    duration_years=1,
    payment="eth",
    inft_mode_a=True,
    list_on_agenticplace=False,
)
# → {"status": "ok", "stdout": "tx: 0x...", "stderr": ""}
```

## Why a CLI wrapper, not direct Python contract calls?

The Python ecosystem doesn't yet have a viem-equivalent that we'd want to
ship as a dependency from bankoneth. The CLI is already a thin viem wrapper;
this Python tool runs it as a subprocess. When/if we switch to a native
Python implementation (web3.py-based), this file's interface stays the same —
only `_spawn` changes.

## License

Apache-2.0
