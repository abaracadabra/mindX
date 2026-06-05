import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider, createConfig, http } from "wagmi";
import { mainnet, polygon, arbitrum, optimism, base, sepolia } from "wagmi/chains";
import App from "./App.js";

const queryClient = new QueryClient();

const wagmiConfig = createConfig({
  chains: [mainnet, polygon, arbitrum, optimism, base, sepolia],
  transports: {
    [mainnet.id]:  http(),
    [polygon.id]:  http(),
    [arbitrum.id]: http(),
    [optimism.id]: http(),
    [base.id]:     http(),
    [sepolia.id]:  http()
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </WagmiProvider>
  </React.StrictMode>
);
