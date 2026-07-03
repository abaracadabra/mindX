package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"

	"github.com/gorilla/websocket"
)

// SubscribeRequest represents the subscription message
type SubscribeRequest struct {
	Type               string   `json:"type"`
	SubscriptionID     int      `json:"subscriptionId"`
	PriceFeedIDs       []int    `json:"priceFeedIds"`
	Properties         []string `json:"properties"`
	Formats            []string `json:"formats"`
	Channel            string   `json:"channel"`
	DeliveryFormat     string   `json:"deliveryFormat"`
	JsonBinaryEncoding string   `json:"jsonBinaryEncoding"`
	Parsed             bool     `json:"parsed"`
	// IgnoreInvalidFeeds bool  `json:"ignoreInvalidFeeds,omitempty"` // Ignore invalid feed IDs instead of failing
}

// StreamUpdate represents the response from the server
type StreamUpdate struct {
	Type           string      `json:"type"`
	SubscriptionID int         `json:"subscriptionId"`
	Parsed         ParsedData  `json:"parsed,omitempty"`
	EVM            *BinaryData `json:"evm,omitempty"`
	Solana         *BinaryData `json:"solana,omitempty"`
}

type ParsedData struct {
	TimestampUs string      `json:"timestampUs"`
	PriceFeeds  []PriceFeed `json:"priceFeeds"`
}

type PriceFeed struct {
	PriceFeedID    int    `json:"priceFeedId"`
	Price          string `json:"price,omitempty"`
	BestBidPrice   string `json:"bestBidPrice,omitempty"`
	BestAskPrice   string `json:"bestAskPrice,omitempty"`
	Confidence     int64  `json:"confidence,omitempty"`
	Exponent       int    `json:"exponent,omitempty"`
	PublisherCount int    `json:"publisherCount,omitempty"`
	FeedUpdateTimestamp uint64  `json:"feedUpdateTimestamp,omitempty"`
}

type BinaryData struct {
	Encoding string `json:"encoding"`
	Data     string `json:"data"`
}

func main() {
	// WebSocket endpoints for redundancy
	endpoints := []string{
		"wss://pyth-lazer-0.dourolabs.app/v1/stream",
		"wss://pyth-lazer-1.dourolabs.app/v1/stream",
		"wss://pyth-lazer-2.dourolabs.app/v1/stream",
	}

	// Read your API key from the environment (never hard-code it)
	token := os.Getenv("LAZER_TOKEN")
	if token == "" {
		log.Fatal("Set LAZER_TOKEN in your environment")
	}

	// Set up interrupt handler
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt)

	// Connect to the first endpoint (for production, connect to all)
	header := http.Header{}
	header.Add("Authorization", "Bearer "+token)

	conn, _, err := websocket.DefaultDialer.Dial(endpoints[0], header)
	if err != nil {
		log.Fatal("Failed to connect:", err)
	}
	defer conn.Close()

	log.Println("Connected to Pyth Lazer")

	// Send subscription request
	subscribeReq := SubscribeRequest{
		Type:               "subscribe",
		SubscriptionID:     1,
		PriceFeedIDs:       []int{1, 2, 3, 4, 6, 5, 7, 8, 9, 12, 10, 11, 13, 14, 15, 16, 18, 17, 19, 20, 22, 21, 23, 24, 26, 25, 27, 28, 30, 29, 50, 49, 47, 48, 46, 45, 43, 44, 42, 41, 39, 40, 38, 37, 36, 35, 33, 34, 32, 31},
		Properties:         []string{"price", "bestBidPrice", "bestAskPrice", "confidence", "fundingRate", "publisherCount", "exponent", "fundingTimestamp", "fundingRateInterval", "marketSession", "feedUpdateTimestamp"},
		Formats:            []string{"solana", "evm", "leEcdsa", "leUnsigned"},
		Channel:            "fixed_rate@200ms",
		DeliveryFormat:     "json",
		JsonBinaryEncoding: "hex",
		Parsed:             true,
	}

	if err := conn.WriteJSON(subscribeReq); err != nil {
		log.Fatal("Failed to subscribe:", err)
	}

	log.Println("Subscribed to price feeds")

	// Read messages
	done := make(chan struct{})
	go func() {
		defer close(done)
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				log.Println("Read error:", err)
				return
			}

			var update StreamUpdate
			if err := json.Unmarshal(message, &update); err != nil {
				log.Println("Parse error:", err)
				continue
			}

			if update.Type == "streamUpdated" {
				fmt.Printf("Price Update (Subscription %d):\n", update.SubscriptionID)
				for _, feed := range update.Parsed.PriceFeeds {
					fmt.Printf("  Feed %d: Price=%s FeedUpdateTimestamp=%d\n", feed.PriceFeedID, feed.Price, feed.FeedUpdateTimestamp)
				}
			}
		}
	}()

	// Wait for interrupt
	select {
	case <-done:
	case <-interrupt:
		log.Println("Shutting down...")
		conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	}
}

// go mod init pyth-lazer-example
// go get github.com/gorilla/websocket
// go run main.go
