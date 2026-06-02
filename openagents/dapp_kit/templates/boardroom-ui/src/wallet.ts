/**
 * Minimal wallet adapter — uses window.ethereum (MetaMask + EIP-1193).
 *
 * We deliberately don't pull wagmi or RainbowKit; the surface we need is
 * tiny: connect, get an address, sign a personal_sign message. viem's
 * walletClient could do this too but window.ethereum directly keeps the
 * bundle a fraction of the size.
 */

declare global {
  interface Window {
    ethereum?: {
      request<T = unknown>(args: { method: string; params?: unknown[] }): Promise<T>;
      on?: (event: string, handler: (...args: unknown[]) => void) => void;
    };
  }
}

export async function connectWallet(): Promise<string> {
  if (!window.ethereum) throw new Error('No injected wallet — install MetaMask, Rabby, or another EIP-1193 wallet.');
  const accounts = await window.ethereum.request<string[]>({ method: 'eth_requestAccounts' });
  if (!accounts?.length) throw new Error('User declined wallet connection.');
  return accounts[0]!.toLowerCase();
}

export async function signMessage(wallet: string, message: string): Promise<string> {
  if (!window.ethereum) throw new Error('No injected wallet');
  // personal_sign expects [message, address] in MetaMask, [address, message] in some others.
  // MetaMask is the dominant case; we use that order.
  return window.ethereum.request<string>({
    method: 'personal_sign',
    params: [message, wallet],
  });
}
