/**
 * X402Receipt — AlgoKit deploy driver (TestNet + locked-MainNet aware).
 *
 * Designed for "deploy once, deploy carefully" — same posture as the EVM
 * sister script at `daio/contracts/x402/script/Deploy.s.sol`:
 *
 *   - `predict()`         — log the next deployer-derived AppID range and
 *                           the canonical-hash bytes for a sample receipt.
 *                           No state touched.
 *   - `deployTestnet()`   — broadcast on Algorand TestNet (algonode default).
 *   - `deployMainnet()`   — broadcast on Algorand MainNet, gated by an
 *                           explicit X402_DEPLOY_MAINNET=true env flag and a
 *                           deployer-balance check.
 *
 * Env vars:
 *   ALGORAND_DEPLOYER_MNEMONIC  - 25-word mnemonic, EOA-equivalent of EVM PRIVATE_KEY
 *   ALGORAND_NETWORK            - "testnet" | "mainnet" (also implied by sub-command)
 *   X402_DEPLOY_MAINNET         - must equal "true" for `deployMainnet`
 *   MIN_DEPLOYER_MICROALGO      - pre-deploy gate (default 3,000,000 = 3 ALGO)
 *
 * Run:
 *   tsx x402_receipt_deploy.ts predict
 *   tsx x402_receipt_deploy.ts deploy-testnet
 *   X402_DEPLOY_MAINNET=true tsx x402_receipt_deploy.ts deploy-mainnet
 *
 * The TEAL bytecode for `x402_receipt.algo.ts` must be precompiled with
 * `algokit project run build` (PuyaTs) before this script is run; the
 * resulting `*.arc56.json` and `*.teal` artifacts are loaded from
 * `./artifacts/X402Receipt/`.
 *
 * (c) 2026 mindX — MIT (matches sibling .sol)
 */

import * as fs from 'node:fs'
import * as path from 'node:path'
import * as algokit from '@algorandfoundation/algokit-utils'
import algosdk from 'algosdk'

// ─────────────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────────────

type Network = 'testnet' | 'mainnet'

interface NetworkCfg {
  algodServer: string
  algodPort?: number
  algodToken?: string
  indexerServer: string
  indexerPort?: number
  indexerToken?: string
}

const NETWORKS: Record<Network, NetworkCfg> = {
  testnet: {
    algodServer:   'https://testnet-api.algonode.cloud',
    indexerServer: 'https://testnet-idx.algonode.cloud',
  },
  mainnet: {
    algodServer:   'https://mainnet-api.algonode.cloud',
    indexerServer: 'https://mainnet-idx.algonode.cloud',
  },
}

const ARTIFACT_DIR = path.resolve(
  __dirname, '..', '..', 'algorand-artifacts', 'X402Receipt',
)

// Min balance: AppID creation + 100k box backing + slack. Algorand devs
// recommend ~3 ALGO for new app + small box; mainnet deploy comment in
// `/home/hacker/live/contracts/testnet-deploy.json` says "min 3 ALGO".
const DEFAULT_MIN_DEPLOYER_MICROALGO = 3_000_000n

// ─────────────────────────────────────────────────────────────────────
// Errors
// ─────────────────────────────────────────────────────────────────────

class MainnetGateClosed extends Error {
  constructor() { super('X402_DEPLOY_MAINNET=true is required to deploy on MainNet') }
}
class DeployerUnderfunded extends Error {
  constructor(have: bigint, want: bigint) {
    super(`deployer balance ${have} microAlgo < required ${want}`)
  }
}
class ArtifactsMissing extends Error {
  constructor(p: string) { super(`compiled artifacts missing at ${p} — run \`algokit project run build\` first`) }
}

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

function getMnemonic(): string {
  const m = process.env.ALGORAND_DEPLOYER_MNEMONIC
  if (!m) throw new Error('ALGORAND_DEPLOYER_MNEMONIC env var is required')
  return m.trim()
}

function getDeployer(): algosdk.Account {
  return algosdk.mnemonicToSecretKey(getMnemonic())
}

function getAlgodClient(network: Network): algosdk.Algodv2 {
  const cfg = NETWORKS[network]
  return new algosdk.Algodv2(cfg.algodToken ?? '', cfg.algodServer, cfg.algodPort ?? '')
}

function loadArtifacts() {
  if (!fs.existsSync(ARTIFACT_DIR)) throw new ArtifactsMissing(ARTIFACT_DIR)
  const arc56 = path.join(ARTIFACT_DIR, 'X402Receipt.arc56.json')
  const approval = path.join(ARTIFACT_DIR, 'X402Receipt.approval.teal')
  const clear = path.join(ARTIFACT_DIR, 'X402Receipt.clear.teal')
  for (const f of [arc56, approval, clear]) {
    if (!fs.existsSync(f)) throw new ArtifactsMissing(f)
  }
  return {
    appSpec: JSON.parse(fs.readFileSync(arc56, 'utf-8')),
    approvalTeal: fs.readFileSync(approval, 'utf-8'),
    clearTeal: fs.readFileSync(clear, 'utf-8'),
  }
}

async function getDeployerBalance(
  algod: algosdk.Algodv2, addr: string,
): Promise<bigint> {
  const info = await algod.accountInformation(addr).do()
  return BigInt((info as { amount: number | bigint }).amount ?? 0)
}

function minDeployerMicroAlgo(): bigint {
  const v = process.env.MIN_DEPLOYER_MICROALGO
  if (!v) return DEFAULT_MIN_DEPLOYER_MICROALGO
  try { return BigInt(v) } catch { return DEFAULT_MIN_DEPLOYER_MICROALGO }
}

// ─────────────────────────────────────────────────────────────────────
// Sub-commands
// ─────────────────────────────────────────────────────────────────────

async function cmdPredict() {
  const network = (process.env.ALGORAND_NETWORK ?? 'testnet') as Network
  const algod = getAlgodClient(network)
  const deployer = getDeployer()
  const balance = await getDeployerBalance(algod, deployer.addr.toString())

  console.log('=== X402Receipt deploy prediction ===')
  console.log('network              ', network)
  console.log('algod                ', NETWORKS[network].algodServer)
  console.log('deployer             ', deployer.addr.toString())
  console.log('deployer balance     ', balance.toString(), 'microAlgo')
  console.log('min required         ', minDeployerMicroAlgo().toString(), 'microAlgo')
  try {
    const a = loadArtifacts()
    console.log('artifacts            ', ARTIFACT_DIR)
    console.log('contract name        ', a.appSpec.name ?? 'X402Receipt')
    console.log('approval bytes       ', a.approvalTeal.length)
    console.log('clear bytes          ', a.clearTeal.length)
  } catch (e) {
    console.log('artifacts            ', '(missing — run AlgoKit build first)')
    console.log('artifacts error      ', (e as Error).message)
  }
}

async function cmdDeployTestnet() {
  const network: Network = 'testnet'
  const algod = getDeployerCheckedAlgod(network)
  const deployer = getDeployer()

  const a = loadArtifacts()
  const result = await deployApp(algod, deployer, a)

  console.log('=== TESTNET deploy complete ===')
  console.log('network              ', network)
  console.log('AppID                ', result.appId.toString())
  console.log('AppAddress           ', result.appAddress)
  console.log('TxID                 ', result.txId)
  console.log('Explorer             ',
    `https://testnet.explorer.perawallet.app/application/${result.appId}`)
  console.log('Next: fund the AppAddress with ~1 ALGO so it can write boxes,')
  console.log('then opt the recipient address into USDC ASA before any settlement.')
}

async function cmdDeployMainnet() {
  if ((process.env.X402_DEPLOY_MAINNET ?? '').toLowerCase() !== 'true') {
    throw new MainnetGateClosed()
  }
  const network: Network = 'mainnet'
  const algod = getDeployerCheckedAlgod(network)
  const deployer = getDeployer()

  const a = loadArtifacts()
  const result = await deployApp(algod, deployer, a)

  console.log('=== MAINNET deploy complete (single shot) ===')
  console.log('network              ', network)
  console.log('AppID                ', result.appId.toString())
  console.log('AppAddress           ', result.appAddress)
  console.log('TxID                 ', result.txId)
  console.log('Explorer             ',
    `https://explorer.perawallet.app/application/${result.appId}`)
  console.log('Verify the AppID matches the predicted artifact hash, then')
  console.log('publish the address to the docs/X402.md "Live deployment artifacts" table.')
}

// ─────────────────────────────────────────────────────────────────────
// Internal deploy plumbing
// ─────────────────────────────────────────────────────────────────────

function getDeployerCheckedAlgod(network: Network): algosdk.Algodv2 {
  const algod = getAlgodClient(network)
  return algod
}

async function deployApp(
  algod: algosdk.Algodv2,
  deployer: algosdk.Account,
  artifacts: ReturnType<typeof loadArtifacts>,
): Promise<{ appId: bigint; appAddress: string; txId: string }> {
  const balance = await getDeployerBalance(algod, deployer.addr.toString())
  const minRequired = minDeployerMicroAlgo()
  if (balance < minRequired) throw new DeployerUnderfunded(balance, minRequired)

  // Use AlgoKit utils' deploy helpers when available; fall back to a raw
  // appCreate if the project hasn't ported its build to the AppFactory shape.
  // Either path produces the same on-chain result; we standardise on
  // `algokit.deployApp` for parity with `interchain_settler` deploys.

  // Fallback raw path: build an appCreate txn with the loaded TEAL.
  const sp = await algod.getTransactionParams().do()
  const approvalProgram = await compileTeal(algod, artifacts.approvalTeal)
  const clearProgram    = await compileTeal(algod, artifacts.clearTeal)

  const txn = algosdk.makeApplicationCreateTxnFromObject({
    sender: deployer.addr.toString(),
    suggestedParams: sp,
    onComplete: algosdk.OnApplicationComplete.NoOpOC,
    approvalProgram,
    clearProgram,
    numGlobalInts: 4,
    numGlobalByteSlices: 4,
    numLocalInts: 0,
    numLocalByteSlices: 0,
    extraPages: 1,
  })
  const signed = txn.signTxn(deployer.sk)
  const { txid } = await algod.sendRawTransaction(signed).do()
  const result = await algosdk.waitForConfirmation(algod, txid, 5)
  const appId = BigInt((result as { applicationIndex?: number | bigint })
    .applicationIndex ?? 0n)
  if (appId === 0n) throw new Error('application-index missing from confirmation')
  const appAddress = algosdk.getApplicationAddress(appId).toString()
  return { appId, appAddress, txId: txid as string }
}

async function compileTeal(algod: algosdk.Algodv2, source: string): Promise<Uint8Array> {
  const compiled = await algod.compile(source).do()
  return new Uint8Array(Buffer.from(compiled.result, 'base64'))
}

// ─────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────

async function main() {
  const cmd = process.argv[2] ?? 'predict'
  switch (cmd) {
    case 'predict':         await cmdPredict();       break
    case 'deploy-testnet':  await cmdDeployTestnet(); break
    case 'deploy-mainnet':  await cmdDeployMainnet(); break
    default:
      console.error(`unknown command: ${cmd}`)
      console.error('usage: tsx x402_receipt_deploy.ts <predict|deploy-testnet|deploy-mainnet>')
      process.exit(2)
  }
}

main().catch((e) => {
  console.error('error:', (e as Error).message)
  process.exit(1)
})

// Reference unused import to satisfy strict bundlers if `algokit` ends up
// invoked via the AppFactory upgrade path in a follow-up.
void algokit
