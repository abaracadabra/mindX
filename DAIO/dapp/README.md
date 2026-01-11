# DAIO dNFT dApp

A React-based decentralized application for interacting with the DAIO Dynamic NFT (dNFT) contract on ARC Testnet.

## Features

- **Create THINK Batches**: Mint new dynamic NFT batches with custom prompts, dimensions, and batch sizes
- **Update THINK Metadata**: Update existing THINK prompts and agent prompts (if you own tokens)
- **View Your THINK Tokens**: Display all THINK tokens you own with their metadata
- **Real-time Updates**: Automatically refresh token list after transactions
- **Modern UI**: Clean, responsive design with gradient styling

## Prerequisites

- Node.js 14+ and npm
- MetaMask browser extension
- Access to ARC Testnet (or configure for your network)

## Setup

1. **Install Dependencies**
   ```bash
   npm install react react-dom ethers chart.js
   ```

2. **Configure Contract Address**
   
   Update `dapp.js` with your deployed dNFT contract address:
   ```javascript
   const DNFT_CONTRACT_ADDRESS = "YOUR_DEPLOYED_CONTRACT_ADDRESS";
   ```

   Or set environment variable:
   ```bash
   export REACT_APP_DNFT_ADDRESS="0x..."
   export REACT_APP_RPC_URL="https://rpc.arc.network"
   ```

3. **Update Contract ABI**
   
   If you've modified the dNFT contract, update the `DNFT_ABI` array in `dapp.js` with the complete ABI from your compiled contract.

## Usage

### Development

If using Create React App:
```bash
npm start
```

If using Vite:
```bash
npm run dev
```

### Production Build

```bash
npm run build
```

## Contract Integration

This dApp integrates with `DAIO/contracts/src/core/dNFT.sol`:

### Key Functions Used

- `createThinkBatch()`: Creates a new THINK batch
- `updateThink()`: Updates THINK metadata (requires token ownership)
- `getThinkData()`: Retrieves THINK metadata
- `balanceOf()`: Checks token balance
- `uri()`: Gets token URI

### Events Monitored

- `ThinkCreated`: Emitted when a new THINK is created
- `ThinkUpdated`: Emitted when THINK metadata is updated

## Network Configuration

### ARC Testnet

- Chain ID: 1243 (update if different)
- RPC URL: `https://rpc.arc.network`

To switch networks in MetaMask:
1. Open MetaMask
2. Click network dropdown
3. Add ARC Testnet if not present
4. Configure with RPC URL above

## Improvements Over Original

1. **ERC1155 Support**: Updated from ERC721 to ERC1155 (batch tokens)
2. **Real Contract Integration**: Uses actual DAIO dNFT contract functions
3. **Better Error Handling**: Comprehensive error messages and validation
4. **Form Validation**: Input validation for all fields
5. **Token Enumeration**: Attempts to fetch user's tokens (limited by design)
6. **Modern UI**: Improved styling and responsive design
7. **Loading States**: Visual feedback during transactions
8. **Account Management**: Handles wallet connection and account changes
9. **Network Detection**: Warns if not on correct network

## Limitations

- **Token Enumeration**: ERC1155 doesn't support direct enumeration. The dApp checks a range of token IDs (1-100). For production, consider:
  - Using events to track created tokens
  - Implementing a separate indexer
  - Using The Graph for subgraph indexing

## Future Enhancements

- [ ] Event-based token tracking
- [ ] The Graph integration for better token discovery
- [ ] Batch operations UI
- [ ] THINK visualization charts
- [ ] Transaction history
- [ ] Multi-wallet support (WalletConnect, etc.)
- [ ] Dark mode
- [ ] IPFS integration for metadata storage

## Troubleshooting

### "Please switch to ARC Testnet"
- Ensure MetaMask is connected to ARC Testnet
- Check chain ID in code matches your network

### "Failed to fetch THINK tokens"
- Contract may not be deployed
- Check contract address is correct
- Verify RPC endpoint is accessible

### "You don't own any tokens"
- Make sure you've minted tokens first
- Check if token enumeration range needs to be increased

## License

MIT

## Related Documentation

- [DAIO dNFT Contract](../contracts/src/core/dNFT.sol)
- [DAIO Documentation](../docs/DAIO.md)
- [ERC-1155 Standard](https://eips.ethereum.org/EIPS/eip-1155)
