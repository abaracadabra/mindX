import { useMemo } from "react";
import { useChainId } from "wagmi";
import { type Address } from "viem";

import deployments from "../config/deployments.json";

export interface DeployedAddresses {
  oracle:    Address;
  index:     Address;
  debtToken: Address;
  x402:      Address;
  mindx:     Address;
  agents:    Address;
  bankon:    Address;
  governor:  Address;
  treasury:  Address;
  voteToken: Address;
  settlement: Address;
}

type Manifest = Record<string, Partial<DeployedAddresses>>;

/** Returns the deployed addresses for the currently connected chain, or null if undeployed. */
export function useAddresses(): DeployedAddresses | null {
  const chainId = useChainId();
  return useMemo(() => {
    const manifest = deployments as unknown as Manifest;
    const record = manifest[String(chainId)];
    if (!record) return null;
    // Only return if all required addresses are present.
    const required: (keyof DeployedAddresses)[] = [
      "oracle", "index", "debtToken", "x402", "mindx",
      "agents", "bankon", "governor", "treasury", "voteToken", "settlement"
    ];
    for (const key of required) {
      if (!record[key]) return null;
    }
    return record as DeployedAddresses;
  }, [chainId]);
}
