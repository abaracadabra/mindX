// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// openagents/ dApp kit Tauri 2 shell.
// Contract: docs/services/wallet_connection_as_a_service.md §2.2, §6.

mod commands;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::keychain::keychain_store,
            commands::keychain::keychain_load,
            commands::keychain::keychain_clear,
        ])
        .setup(|_app| Ok(()))
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
