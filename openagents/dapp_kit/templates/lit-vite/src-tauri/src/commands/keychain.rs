// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// OS-keychain commands. Backed by the cross-platform `keyring` crate:
//   - macOS / iOS: Keychain
//   - Windows:     Credential Manager
//   - Linux:       Secret Service (libsecret) / KWallet
//   - Android:     Android Keystore (via Tauri 2 mobile harness)
//
// Contract: docs/services/wallet_connection_as_a_service.md §6.1.

use keyring::Entry;
use serde::Serialize;

const SERVICE: &str = "place.agentic.openagents.dapp";

#[derive(Serialize)]
pub struct CommandError {
    message: String,
}

impl From<keyring::Error> for CommandError {
    fn from(err: keyring::Error) -> Self {
        CommandError {
            message: format!("keyring: {err}"),
        }
    }
}

/// Store a value under `key` in the OS keychain.
#[tauri::command]
pub fn keychain_store(key: String, value: String) -> Result<(), CommandError> {
    let entry = Entry::new(SERVICE, &key)?;
    entry.set_password(&value)?;
    Ok(())
}

/// Load a value previously stored under `key`. Returns the empty string
/// when nothing is stored (mirrors the TS sessionStorage behavior).
#[tauri::command]
pub fn keychain_load(key: String) -> Result<String, CommandError> {
    let entry = Entry::new(SERVICE, &key)?;
    match entry.get_password() {
        Ok(v) => Ok(v),
        Err(keyring::Error::NoEntry) => Ok(String::new()),
        Err(e) => Err(e.into()),
    }
}

/// Clear the entry under `key`.
#[tauri::command]
pub fn keychain_clear(key: String) -> Result<(), CommandError> {
    let entry = Entry::new(SERVICE, &key)?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(e.into()),
    }
}
