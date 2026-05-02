/**
 * 0G Storage Sidecar — agnostic HTTP bridge
 *
 * 0G Storage's only first-party SDKs are Go and TypeScript. Any non-Go/non-TS
 * framework — mindX (Python), but also any other agent stack — can talk to
 * this Node process over HTTP:
 *
 *   POST /upload          → multipart bytes → { rootHash, txHash, uri }
 *   GET  /retrieve/:root  → bytes for that root (Content-Type: octet-stream)
 *   GET  /health          → reachability + RPC + balance probe
 *
 * mindX consumes this via `agents/storage/zerog_provider.py` against
 * http://127.0.0.1:7878. The sidecar binds to localhost only — never exposed
 * externally. Production deployments run sidecar + framework on the same host
 * (or in the same pod with shared loopback).
 *
 * Mandatory SDK calls baked in (per 0G integration guide):
 *   - merkleTree() before upload() (computes root deterministically)
 *   - downloadToBlob() supported via /retrieve route (browser-friendly)
 *
 * SDK package: @0gfoundation/0g-ts-sdk@^1.2.6 (the legacy @0glabs package
 * is unmaintained as of 2026-04).
 *
 * Env:
 *   ZEROG_RPC_URL       (default https://evmrpc-testnet.0g.ai = Galileo)
 *   ZEROG_INDEXER_URL   (default https://indexer-storage-testnet-turbo.0g.ai)
 *   ZEROG_PRIVATE_KEY   (signer for upload tx; required for /upload)
 *   ZEROG_NETWORK_NAME  (default 'galileo' — used in uri scheme)
 *   PORT                (default 7878)
 */

import express from "express";
import multer from "multer";
import { ethers } from "ethers";
import { Indexer, ZgFile } from "@0gfoundation/0g-ts-sdk";
import { Readable } from "node:stream";

const PORT = parseInt(process.env.PORT ?? "7878", 10);
const RPC = process.env.ZEROG_RPC_URL ?? "https://evmrpc-testnet.0g.ai";
const INDEXER_URL =
  process.env.ZEROG_INDEXER_URL ?? "https://indexer-storage-testnet-turbo.0g.ai";
const PRIVATE_KEY = process.env.ZEROG_PRIVATE_KEY ?? "";
const NETWORK_NAME = process.env.ZEROG_NETWORK_NAME ?? "galileo";
const EXPLORER_BASE = process.env.ZEROG_EXPLORER ??
  (NETWORK_NAME === "aristotle" ? "https://chainscan.0g.ai" : "https://chainscan-galileo.0g.ai");

const app = express();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 64 * 1024 * 1024 } });

const provider = new ethers.JsonRpcProvider(RPC);
// Cast to any — the v6 ethers Wallet type isn't structurally compatible with
// the v5-typed signer the SDK still expects on some methods (per OG guide).
const wallet = PRIVATE_KEY ? (new ethers.Wallet(PRIVATE_KEY, provider) as any) : null;
const indexer = new Indexer(INDEXER_URL);

function explorerLink(txHash: string): string {
  return `${EXPLORER_BASE}/tx/${txHash}`;
}

/* -------------------------- health ------------------------------------- */

app.get("/health", async (_req, res) => {
  try {
    const blockNumber = await provider.getBlockNumber();
    const balance = wallet ? await provider.getBalance(wallet.address) : null;
    res.json({
      ok: true,
      network: NETWORK_NAME,
      rpc: RPC,
      indexer: INDEXER_URL,
      explorer: EXPLORER_BASE,
      blockNumber,
      signer: wallet ? wallet.address : null,
      balance: balance ? ethers.formatEther(balance) : null,
      uptime_s: Math.round(process.uptime()),
      sdk: "@0gfoundation/0g-ts-sdk@^1.2.6",
    });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message ?? e) });
  }
});

/* -------------------------- upload ------------------------------------- */

app.post("/upload", upload.single("file"), async (req, res) => {
  if (!wallet) {
    return res.status(503).json({ ok: false, error: "ZEROG_PRIVATE_KEY not configured" });
  }
  if (!req.file?.buffer) {
    return res.status(400).json({ ok: false, error: "no file in multipart 'file' field" });
  }
  try {
    // Build the ZgFile from the in-memory buffer.
    const file = ZgFile.fromBuffer(req.file.buffer);

    // MANDATORY: compute the merkle tree BEFORE upload(). The SDK refuses
    // upload() without a precomputed tree; this is the single most common
    // first-call failure for new integrators.
    const [tree, treeErr] = await file.merkleTree();
    if (treeErr) throw treeErr;
    if (!tree) throw new Error("merkleTree() returned null");
    const rootHash = tree.rootHash();
    if (!rootHash) throw new Error("merkleTree() returned empty rootHash");

    // upload() returns [txHash, error] tuple per SDK convention.
    const [tx, uploadErr] = await indexer.upload(file, RPC, wallet);
    if (uploadErr) throw uploadErr;

    res.json({
      ok: true,
      rootHash,
      txHash: tx,
      uri: `0g://${NETWORK_NAME}/${rootHash}`,
      explorer: tx ? explorerLink(tx) : null,
      bytes: req.file.buffer.length,
    });
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message ?? e) });
  }
});

/* -------------------------- retrieve ----------------------------------- */

app.get("/retrieve/:root", async (req, res) => {
  const root = req.params.root;
  if (!root || !root.startsWith("0x") || root.length !== 66) {
    return res.status(400).json({ ok: false, error: "root must be 0x-prefixed 32-byte hex" });
  }
  try {
    const buf = await indexer.download(root);
    if (!buf) {
      return res.status(404).json({ ok: false, error: "not found" });
    }
    res.setHeader("Content-Type", "application/octet-stream");
    res.setHeader("X-0G-Root", root);
    Readable.from(buf).pipe(res);
  } catch (e: any) {
    res.status(500).json({ ok: false, error: String(e?.message ?? e) });
  }
});

/* -------------------------- start -------------------------------------- */

app.listen(PORT, "127.0.0.1", () => {
  // eslint-disable-next-line no-console
  console.log(
    JSON.stringify({
      msg: "mindx-zerog-sidecar listening",
      port: PORT,
      rpc: RPC,
      indexer: INDEXER_URL,
      signer: wallet?.address ?? null,
    })
  );
});
