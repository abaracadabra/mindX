import { PythLazerClient } from "@pythnetwork/pyth-lazer-sdk";

// Read your API key from the environment (never hard-code it)
const token = process.env.LAZER_TOKEN;
if (!token) throw new Error("Set LAZER_TOKEN in your environment");

// Create the Pyth Lazer client with WebSocket pool configuration
const client = await PythLazerClient.create({
  token,
  webSocketPoolConfig: {
    urls: [
      "wss://pyth-lazer-0.dourolabs.app/v1/stream",
      "wss://pyth-lazer-1.dourolabs.app/v1/stream",
      "wss://pyth-lazer-2.dourolabs.app/v1/stream",
    ],
  },
});

// Subscribe to price feeds
client.subscribe({
  type: "subscribe",
  subscriptionId: 1,
  priceFeedIds: [1, 2, 3, 4, 6, 5, 7, 8, 9, 12, 10, 11, 13, 14, 15, 16, 18, 17, 19, 20, 22, 21, 23, 24, 26, 25, 27, 28, 30, 29, 50, 49, 47, 48, 46, 45, 43, 44, 42, 41, 39, 40, 38, 37, 36, 35, 33, 34, 32, 31],
  properties: ["price", "bestBidPrice", "bestAskPrice", "confidence", "fundingRate", "publisherCount", "exponent", "fundingTimestamp", "fundingRateInterval", "marketSession", "feedUpdateTimestamp"],
  formats: ["solana", "evm", "leEcdsa", "leUnsigned"],
  channel: "fixed_rate@200ms",
  deliveryFormat: "json",
  jsonBinaryEncoding: "hex",
  parsed: true,
  // ignoreInvalidFeeds: true, // Ignore invalid feed IDs instead of failing
});

// Listen for price updates
client.addMessageListener((message) => {
  if (message.type === "json") {
    console.log("Received JSON update:", JSON.stringify(message.value, null, 2));
  } else {
    console.log("Received binary update:", {
      subscriptionId: message.value.subscriptionId,
      parsed: message.value.parsed,
    });
  }
});

// Handle connection errors
client.addAllConnectionsDownListener(() => {
  console.error("All WebSocket connections are down!");
});

// To unsubscribe later:
// client.unsubscribe(1);

// To shutdown the client:
// client.shutdown();
