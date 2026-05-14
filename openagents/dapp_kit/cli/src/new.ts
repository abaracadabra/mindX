// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// `openagents-dapp new <dir>` — copy the lit-vite template to <dir>,
// then rewrite the project name in package.json.

import { cp, readFile, writeFile, mkdir } from "node:fs/promises";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

export async function newCmd(args: string[]): Promise<number> {
  const dir = args[0];
  if (!dir) {
    console.error("openagents-dapp new: missing <project-dir>");
    return 2;
  }
  const here = fileURLToPath(import.meta.url);
  // dist/new.js → ../../templates/lit-vite (cli/dist/new.js)
  const templateDir = join(dirname(here), "..", "..", "templates", "lit-vite");

  await mkdir(dir, { recursive: true });
  await cp(templateDir, dir, {
    recursive: true,
    filter: (src) => !src.includes("node_modules") && !src.endsWith("dist"),
  });

  // Rewrite project name + drop the workspace marker
  const pkgPath = join(dir, "package.json");
  try {
    const text = await readFile(pkgPath, "utf-8");
    const pkg = JSON.parse(text) as Record<string, unknown>;
    pkg.name = basename(dir);
    pkg.private = true;
    delete pkg.workspaces;
    await writeFile(pkgPath, JSON.stringify(pkg, null, 2), "utf-8");
  } catch {
    /* template may not have package.json — that's fine */
  }

  console.log(`Scaffolded ${basename(dir)} at ${dir}`);
  console.log(`Next: cd ${dir} && pnpm install && pnpm dev`);
  return 0;
}
