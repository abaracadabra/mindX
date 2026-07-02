#!/usr/bin/env node
// Bump the patch (build) number across package.json, src-tauri/tauri.conf.json
// and src-tauri/Cargo.toml. Wired into `npm run build` (which Tauri's
// beforeBuildCommand calls), so every rebuild gets a fresh incrementing build
// number. Versioning started at 1.1.1 and counts up from there.
//
//   node scripts/bump-version.mjs            # x.y.z → x.y.(z+1)
//   node scripts/bump-version.mjs --minor    # x.y.z → x.(y+1).0
//   node scripts/bump-version.mjs --major    # x.y.z → (x+1).0.0
//   node scripts/bump-version.mjs --set 1.2.3
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pkgPath = join(root, "package.json");
const confPath = join(root, "src-tauri", "tauri.conf.json");
const cargoPath = join(root, "src-tauri", "Cargo.toml");

const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
let [maj, min, pat] = String(pkg.version).split(".").map((n) => parseInt(n, 10) || 0);

const arg = process.argv[2];
const setIdx = process.argv.indexOf("--set");
let next;
if (setIdx !== -1 && process.argv[setIdx + 1]) {
  next = process.argv[setIdx + 1];
} else if (arg === "--major") {
  next = `${maj + 1}.0.0`;
} else if (arg === "--minor") {
  next = `${maj}.${min + 1}.0`;
} else {
  next = `${maj}.${min}.${pat + 1}`; // default: bump the build number
}

// package.json — preserve 2-space JSON + trailing newline.
pkg.version = next;
writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n");

// tauri.conf.json — likewise.
const conf = JSON.parse(readFileSync(confPath, "utf8"));
conf.version = next;
writeFileSync(confPath, JSON.stringify(conf, null, 2) + "\n");

// Cargo.toml — replace only the first `version = "..."` (the [package] one,
// which sits above [lib] and any dependency tables).
let cargo = readFileSync(cargoPath, "utf8");
cargo = cargo.replace(/^version = ".*"/m, `version = "${next}"`);
writeFileSync(cargoPath, cargo);

console.log(`dojo: build version → ${next}`);
