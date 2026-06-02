// SPDX-License-Identifier: Apache-2.0
// bankoneth reference dApp — Tauri 2 shell. Empty Rust side; the dApp is
// pure web tech. The shell exists so the same UI can ship as a desktop
// application with no browser dependency.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
