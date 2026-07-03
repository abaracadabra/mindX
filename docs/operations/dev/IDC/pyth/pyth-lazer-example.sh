# Install wscat if not already installed
npm install -g wscat

# Export your API key so it never ends up in shell history or version control
export LAZER_TOKEN="your-api-key-here"

# Connect to Pyth Lazer WebSocket with authentication
wscat -c "wss://pyth-lazer-0.dourolabs.app/v1/stream" \
  -H "Authorization: Bearer $LAZER_TOKEN"

# Once connected, send this subscription message:
{"channel":"fixed_rate@200ms","deliveryFormat":"json","formats":["solana","evm","leEcdsa","leUnsigned"],"jsonBinaryEncoding":"hex","parsed":true,"priceFeedIds":[1,2,3,4,6,5,7,8,9,12,10,11,13,14,15,16,18,17,19,20,22,21,23,24,26,25,27,28,30,29,50,49,47,48,46,45,43,44,42,41,39,40,38,37,36,35,33,34,32,31],"properties":["price","bestBidPrice","bestAskPrice","confidence","fundingRate","publisherCount","exponent","fundingTimestamp","fundingRateInterval","marketSession","feedUpdateTimestamp"],"subscriptionId":1,"type":"subscribe"}

# To ignore invalid feed IDs instead of failing, add "ignoreInvalidFeeds": true to the message

# Alternative: Using curl for one-shot requests (HTTP API)
curl -X POST "https://pyth-lazer-0.dourolabs.app/v1/latest_price" \
  -H "Authorization: Bearer $LAZER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"formats":["solana","evm","leEcdsa","leUnsigned"],"parsed":true,"priceFeedIds":[1,2,3,4,6,5,7,8,9,12,10,11,13,14,15,16,18,17,19,20,22,21,23,24,26,25,27,28,30,29,50,49,47,48,46,45,43,44,42,41,39,40,38,37,36,35,33,34,32,31],"properties":["price","bestBidPrice","bestAskPrice","confidence","fundingRate","publisherCount","exponent","fundingTimestamp","fundingRateInterval","marketSession","feedUpdateTimestamp"]}'

# For redundancy, connect to multiple endpoints:
# - wss://pyth-lazer-0.dourolabs.app/v1/stream
# - wss://pyth-lazer-1.dourolabs.app/v1/stream
# - wss://pyth-lazer-2.dourolabs.app/v1/stream
