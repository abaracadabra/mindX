#!/usr/bin/env python3
"""
Pyth Lazer WebSocket Client Example

This example demonstrates how to connect to Pyth Lazer and subscribe to price feeds.

Requirements:
    pip install websockets

Usage:
    python pyth_lazer_client.py
"""

import asyncio
import json
import os
import signal
from typing import Any

try:
    import websockets
except ImportError:
    print("Please install websockets: pip install websockets")
    exit(1)


# Read your API key from the environment (never hard-code it)
TOKEN = os.environ["LAZER_TOKEN"]
ENDPOINTS = [
    "wss://pyth-lazer-0.dourolabs.app/v1/stream",
    "wss://pyth-lazer-1.dourolabs.app/v1/stream",
    "wss://pyth-lazer-2.dourolabs.app/v1/stream",
]


async def subscribe_to_prices():
    """Connect to Pyth Lazer and subscribe to price feeds."""
    
    # Subscription request
    subscribe_request = {
        "type": "subscribe",
        "subscriptionId": 1,
        "priceFeedIds": [1, 2, 3, 4, 6, 5, 7, 8, 9, 12, 10, 11, 13, 14, 15, 16, 18, 17, 19, 20, 22, 21, 23, 24, 26, 25, 27, 28, 30, 29, 50, 49, 47, 48, 46, 45, 43, 44, 42, 41, 39, 40, 38, 37, 36, 35, 33, 34, 32, 31],
        "properties": ["price", "bestBidPrice", "bestAskPrice", "confidence", "fundingRate", "publisherCount", "exponent", "fundingTimestamp", "fundingRateInterval", "marketSession", "feedUpdateTimestamp"],
        "formats": ["solana", "evm", "leEcdsa", "leUnsigned"],
        "channel": "fixed_rate@200ms",
        "deliveryFormat": "json",
        "jsonBinaryEncoding": "hex",
        "parsed": True,
        # "ignoreInvalidFeeds": True,  # Ignore invalid feed IDs instead of failing
    }

    # Headers for authentication
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    # Connect to the first endpoint (for production, connect to all for redundancy)
    uri = ENDPOINTS[0]
    
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        print("Connected! Sending subscription...")
        
        # Send subscription request
        await websocket.send(json.dumps(subscribe_request))
        print("Subscribed to price feeds. Waiting for updates...")
        
        # Listen for messages
        try:
            async for message in websocket:
                data = json.loads(message)
                handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")


def handle_message(data: dict[str, Any]) -> None:
    """Process incoming WebSocket messages."""
    
    msg_type = data.get("type")
    
    if msg_type == "streamUpdated":
        subscription_id = data.get("subscriptionId")
        parsed = data.get("parsed", {})
        timestamp = parsed.get("timestampUs", "N/A")
        price_feeds = parsed.get("priceFeeds", [])
        
        print(f"\n--- Price Update (Subscription {subscription_id}) ---")
        print(f"Timestamp: {timestamp}")
        
        for feed in price_feeds:
            feed_id = feed.get("priceFeedId")
            price = feed.get("price", "N/A")
            exponent = feed.get("exponent", 0)
            feed_update_ts = feed.get("feedUpdateTimestamp", "N/A")

            # Calculate actual price if both values are present
            if price != "N/A" and exponent:
                actual_price = int(price) * (10 ** exponent)
                print(f"  Feed {feed_id}: {actual_price:.8f} (feedUpdateTimestamp={feed_update_ts})")
            else:
                print(f"  Feed {feed_id}: {price} (feedUpdateTimestamp={feed_update_ts})")
    
    elif msg_type == "subscribed":
        print(f"Successfully subscribed: {data}")
    
    elif msg_type == "error":
        print(f"Error: {data.get('message', 'Unknown error')}")
    
    else:
        print(f"Received: {data}")


def main():
    """Main entry point."""
    
    # Set up graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def shutdown():
        print("\nShutting down...")
        for task in asyncio.all_tasks(loop):
            task.cancel()
    
    # Handle Ctrl+C
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)
    
    try:
        loop.run_until_complete(subscribe_to_prices())
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
