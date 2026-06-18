# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato — a DAIO-owned data-DAO + permanence-naming suite (modular extension).

A `dato` is a data controller the DAIO spawns and owns: it holds data at a
permanence tier (immortal = Arweave 200-yr guarantee · immutable = hash-locked
anchor · mutable = editable), carries a tiered name (`<handle>.<tier>.<root>`),
records the spawning participant/client wallet, and admits members via a
request-to-join flow that takes a fee + settings.

Modeled on the AO DAO pattern (spawn → configure → join → govern → commit). Ships
across three substrates unified by the Python orchestrator: this package (runs
now), an AO Lua process (`dato/ao/dato.lua`), and EVM contracts (`dato/contracts/`).

This is a SEPARATE MODULAR EXTENSION "for consideration as inclusion" — it does not
touch live DAIO state until a governance proposal opts it in (see dato/INTEGRATION.md).
"""

from dato.core.model import (
    DataRecord,
    DatoInstance,
    Member,
    PermanenceTier,
    Settings,
)

__all__ = ["PermanenceTier", "Settings", "Member", "DataRecord", "DatoInstance"]
__version__ = "0.1.0"
