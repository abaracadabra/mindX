/**
 * Global types for dapp (window.ethereum, MINDX_*).
 */

interface Window {
  ethereum?: {
    request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  };
  MINDX_API_URL?: string;
  MINDX_BACKEND_PORT?: string;
}
