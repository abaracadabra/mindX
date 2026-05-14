// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Prevents additional console window on Windows in release.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    openagents_lit_template_lib::run()
}
