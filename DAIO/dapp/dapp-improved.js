import React, { useState, useEffect, useCallback, useMemo } from "react";
import { ethers } from "ethers";
import "./style.css";

// Contract configuration - Update these after deployment
const DNFT_CONTRACT_ADDRESS = process.env.REACT_APP_DNFT_ADDRESS || "YOUR_DNFT_CONTRACT_ADDRESS";
const RPC_URL = process.env.REACT_APP_RPC_URL || "https://rpc.arc.network"; // ARC Testnet
const ARC_CHAIN_ID = parseInt(process.env.REACT_APP_CHAIN_ID || "1243");
const MAX_TOKEN_CHECK = parseInt(process.env.REACT_APP_MAX_TOKEN_CHECK || "1000");
const TRANSACTION_TIMEOUT = 120000; // 2 minutes

// Input validation constants
const MAX_PROMPT_LENGTH = 10000;
const MAX_AGENT_PROMPT_LENGTH = 10000;
const MIN_DIMENSIONS = 1;
const MAX_DIMENSIONS = 255;
const MIN_BATCH_SIZE = 1;
const MAX_BATCH_SIZE = 65535;
const MIN_AMOUNT = 1;

// dNFT Contract ABI - Based on DAIO/contracts/src/core/dNFT.sol
const DNFT_ABI = [
    "function createThinkBatch(address recipient, string memory prompt, string memory agentPrompt, uint8 dimensions, uint16 batchSize, uint256 amount) external returns (uint256)",
    "function updateThink(uint256 thinkId, string memory newPrompt, string memory newAgentPrompt) external",
    "function getThinkData(uint256 thinkId) external view returns (tuple(string prompt, string agentPrompt, uint40 lastUpdate, bool active, uint8 dimensions, uint16 batchSize))",
    "function balanceOf(address account, uint256 id) external view returns (uint256)",
    "function uri(uint256 thinkId) external view returns (string memory)",
    "function supportsInterface(bytes4 interfaceId) external view returns (bool)",
    "function hasRole(bytes32 role, address account) external view returns (bool)",
    "function MINTER_ROLE() external view returns (bytes32)",
    "event ThinkCreated(uint256 indexed thinkId, string prompt, uint8 dimensions, uint16 batchSize)",
    "event ThinkUpdated(uint256 indexed thinkId, string newPrompt, uint40 timestamp)"
];

// Utility functions
const isValidAddress = (address) => {
    try {
        return ethers.utils.isAddress(address);
    } catch {
        return false;
    }
};

const formatAddress = (address) => {
    if (!address) return "";
    return `${address.substring(0, 6)}...${address.substring(38)}`;
};

const sanitizeInput = (input) => {
    // Remove null bytes and control characters
    return input.replace(/\0/g, "").replace(/[\x00-\x1F\x7F]/g, "");
};

const estimateGas = async (contract, method, params) => {
    try {
        const gasEstimate = await contract.estimateGas[method](...params);
        // Add 20% buffer
        return gasEstimate.mul(120).div(100);
    } catch (error) {
        console.warn("Gas estimation failed, using default:", error);
        return null;
    }
};

function App() {
    const [provider, setProvider] = useState(null);
    const [signer, setSigner] = useState(null);
    const [contract, setContract] = useState(null);
    const [account, setAccount] = useState(null);
    const [thinkTokens, setThinkTokens] = useState([]);
    const [loading, setLoading] = useState(false);
    const [fetchingTokens, setFetchingTokens] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [isMinter, setIsMinter] = useState(false);
    const [networkCorrect, setNetworkCorrect] = useState(false);
    const [pendingTx, setPendingTx] = useState(null);
    const [transactionHistory, setTransactionHistory] = useState([]);
    
    // Form states for creating THINK
    const [prompt, setPrompt] = useState("");
    const [agentPrompt, setAgentPrompt] = useState("");
    const [dimensions, setDimensions] = useState(8);
    const [batchSize, setBatchSize] = useState(1);
    const [amount, setAmount] = useState(1);
    
    // Form states for updating THINK
    const [selectedThinkId, setSelectedThinkId] = useState(null);
    const [updatePrompt, setUpdatePrompt] = useState("");
    const [updateAgentPrompt, setUpdateAgentPrompt] = useState("");

    // Validate contract address
    const contractAddressValid = useMemo(() => {
        return DNFT_CONTRACT_ADDRESS && 
               DNFT_CONTRACT_ADDRESS !== "YOUR_DNFT_CONTRACT_ADDRESS" &&
               isValidAddress(DNFT_CONTRACT_ADDRESS);
    }, []);

    // Cleanup function for event listeners
    useEffect(() => {
        return () => {
            if (window.ethereum) {
                window.ethereum.removeAllListeners("accountsChanged");
                window.ethereum.removeAllListeners("chainChanged");
            }
        };
    }, []);

    // Initialize connection
    useEffect(() => {
        async function init() {
            if (!contractAddressValid) {
                setError("Invalid contract address. Please configure REACT_APP_DNFT_ADDRESS.");
                return;
            }

            if (window.ethereum) {
                try {
                    const tempProvider = new ethers.providers.Web3Provider(window.ethereum);
                    const network = await tempProvider.getNetwork();
                    const chainId = network.chainId ? network.chainId.toString() : network.chainId;
                    const correctNetwork = chainId === ARC_CHAIN_ID.toString();
                    setNetworkCorrect(correctNetwork);
                    
                    if (!correctNetwork) {
                        setError(`Please switch to ARC Testnet (Chain ID: ${ARC_CHAIN_ID}). Current: ${chainId}`);
                    }
                    
                    const tempSigner = tempProvider.getSigner();
                    const tempContract = new ethers.Contract(
                        DNFT_CONTRACT_ADDRESS,
                        DNFT_ABI,
                        tempSigner
                    );
                    
                    // Verify contract is deployed
                    try {
                        const code = await tempProvider.getCode(DNFT_CONTRACT_ADDRESS);
                        if (code === "0x") {
                            setError("Contract not deployed at this address.");
                            return;
                        }
                    } catch (err) {
                        console.warn("Could not verify contract deployment:", err);
                    }
                    
                    setProvider(tempProvider);
                    setSigner(tempSigner);
                    setContract(tempContract);
                    
                    // Get connected account
                    const accounts = await window.ethereum.request({ method: "eth_accounts" });
                    if (accounts.length > 0) {
                        await handleAccountChange(accounts[0], tempContract);
                    }
                    
                    // Listen for account changes
                    window.ethereum.on("accountsChanged", async (accounts) => {
                        if (accounts.length > 0) {
                            await handleAccountChange(accounts[0], tempContract);
                        } else {
                            setAccount(null);
                            setThinkTokens([]);
                            setIsMinter(false);
                        }
                    });
                    
                    // Listen for chain changes
                    window.ethereum.on("chainChanged", () => {
                        window.location.reload();
                    });
                } catch (err) {
                    console.error("Initialization error:", err);
                    setError("Failed to initialize: " + err.message);
                }
            } else {
                setError("Please install MetaMask to use this dApp!");
            }
        }
        init();
    }, [contractAddressValid]);

    const handleAccountChange = useCallback(async (userAccount, tempContract) => {
        setAccount(userAccount);
        
        // Check if user has MINTER_ROLE
        try {
            const minterRole = await tempContract.MINTER_ROLE();
            const hasMinterRole = await tempContract.hasRole(minterRole, userAccount);
            setIsMinter(hasMinterRole);
        } catch (err) {
            console.warn("Could not check MINTER_ROLE:", err);
            setIsMinter(false);
        }
        
        await fetchThinkTokens(userAccount);
    }, []);

    const connectWallet = async () => {
        try {
            if (!window.ethereum) {
                setError("Please install MetaMask!");
                return;
            }
            
            const accounts = await window.ethereum.request({
                method: "eth_requestAccounts"
            });
            
            if (accounts.length > 0) {
                const userAccount = accounts[0];
                
                const tempProvider = new ethers.providers.Web3Provider(window.ethereum);
                const network = await tempProvider.getNetwork();
                const chainId = network.chainId ? network.chainId.toString() : network.chainId;
                const correctNetwork = chainId === ARC_CHAIN_ID.toString();
                setNetworkCorrect(correctNetwork);
                
                if (!correctNetwork) {
                    setError(`Please switch to ARC Testnet (Chain ID: ${ARC_CHAIN_ID}). Current: ${chainId}`);
                    return;
                }
                
                const tempSigner = tempProvider.getSigner();
                const tempContract = new ethers.Contract(
                    DNFT_CONTRACT_ADDRESS,
                    DNFT_ABI,
                    tempSigner
                );
                
                setProvider(tempProvider);
                setSigner(tempSigner);
                setContract(tempContract);
                
                await handleAccountChange(userAccount, tempContract);
            }
        } catch (error) {
            console.error("Connection error:", error);
            if (error.code === 4001) {
                setError("Connection rejected. Please approve the connection request.");
            } else {
                setError("Failed to connect wallet: " + error.message);
            }
        }
    };

    const showNotification = (message, type = "info") => {
        if (type === "error") {
            setError(message);
            setSuccess(null);
        } else if (type === "success") {
            setSuccess(message);
            setError(null);
        }
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (type === "error") setError(null);
            else setSuccess(null);
        }, 5000);
    };

    const createThinkBatch = async () => {
        if (!contract || !account) {
            showNotification("Please connect your wallet first!", "error");
            return;
        }
        
        if (!isMinter) {
            showNotification("You need MINTER_ROLE to create THINK batches. Please contact an administrator.", "error");
            return;
        }
        
        if (!networkCorrect) {
            showNotification("Please switch to the correct network (ARC Testnet)", "error");
            return;
        }
        
        // Input validation
        const sanitizedPrompt = sanitizeInput(prompt.trim());
        const sanitizedAgentPrompt = sanitizeInput(agentPrompt.trim());
        
        if (!sanitizedPrompt || !sanitizedAgentPrompt) {
            showNotification("Please enter both prompt and agent prompt", "error");
            return;
        }
        
        if (sanitizedPrompt.length > MAX_PROMPT_LENGTH) {
            showNotification(`Prompt exceeds maximum length of ${MAX_PROMPT_LENGTH} characters`, "error");
            return;
        }
        
        if (sanitizedAgentPrompt.length > MAX_AGENT_PROMPT_LENGTH) {
            showNotification(`Agent prompt exceeds maximum length of ${MAX_AGENT_PROMPT_LENGTH} characters`, "error");
            return;
        }
        
        if (dimensions < MIN_DIMENSIONS || dimensions > MAX_DIMENSIONS) {
            showNotification(`Dimensions must be between ${MIN_DIMENSIONS} and ${MAX_DIMENSIONS}`, "error");
            return;
        }
        
        if (batchSize < MIN_BATCH_SIZE || batchSize > MAX_BATCH_SIZE) {
            showNotification(`Batch size must be between ${MIN_BATCH_SIZE} and ${MAX_BATCH_SIZE}`, "error");
            return;
        }
        
        if (amount < MIN_AMOUNT) {
            showNotification(`Amount must be at least ${MIN_AMOUNT}`, "error");
            return;
        }
        
        setLoading(true);
        setError(null);
        setSuccess(null);
        
        try {
            // Estimate gas first
            const gasEstimate = await estimateGas(
                contract,
                "createThinkBatch",
                [account, sanitizedPrompt, sanitizedAgentPrompt, dimensions, batchSize, amount]
            );
            
            const gasOptions = gasEstimate 
                ? { gasLimit: gasEstimate }
                : { gasLimit: 500000 };
            
            const tx = await contract.createThinkBatch(
                account,
                sanitizedPrompt,
                sanitizedAgentPrompt,
                dimensions,
                batchSize,
                amount,
                gasOptions
            );
            
            setPendingTx(tx.hash);
            showNotification(`Transaction submitted: ${formatAddress(tx.hash)}`, "info");
            
            // Set timeout
            const timeoutId = setTimeout(() => {
                setPendingTx(null);
                showNotification("Transaction is taking longer than expected. Please check on a block explorer.", "error");
            }, TRANSACTION_TIMEOUT);
            
            const receipt = await tx.wait();
            clearTimeout(timeoutId);
            setPendingTx(null);
            
            // Find the ThinkCreated event
            let thinkId = null;
            if (receipt.events) {
                const thinkCreatedEvent = receipt.events.find(
                    e => e.event === "ThinkCreated"
                );
                if (thinkCreatedEvent) {
                    thinkId = thinkCreatedEvent.args.thinkId.toString();
                }
            }
            
            // Add to transaction history
            setTransactionHistory(prev => [{
                hash: receipt.transactionHash,
                type: "create",
                thinkId: thinkId,
                timestamp: Date.now()
            }, ...prev]);
            
            if (thinkId) {
                showNotification(`THINK batch created successfully! Think ID: ${thinkId}`, "success");
                
                // Reset form
                setPrompt("");
                setAgentPrompt("");
                setDimensions(8);
                setBatchSize(1);
                setAmount(1);
                
                // Refresh token list
                await fetchThinkTokens(account);
            } else {
                showNotification("THINK created but event not found. Please refresh.", "info");
            }
        } catch (error) {
            console.error("Create error:", error);
            setPendingTx(null);
            let errorMsg = "Unknown error";
            
            if (error.code === 4001) {
                errorMsg = "Transaction rejected by user";
            } else if (error.reason) {
                errorMsg = error.reason;
            } else if (error.message) {
                errorMsg = error.message;
            }
            
            showNotification("Failed to create THINK: " + errorMsg, "error");
        } finally {
            setLoading(false);
        }
    };

    const updateThink = async () => {
        if (!contract || !selectedThinkId) {
            showNotification("Please select a THINK to update", "error");
            return;
        }
        
        const sanitizedPrompt = sanitizeInput(updatePrompt.trim());
        const sanitizedAgentPrompt = sanitizeInput(updateAgentPrompt.trim());
        
        if (!sanitizedPrompt || !sanitizedAgentPrompt) {
            showNotification("Please enter both new prompt and agent prompt", "error");
            return;
        }
        
        if (sanitizedPrompt.length > MAX_PROMPT_LENGTH) {
            showNotification(`Prompt exceeds maximum length of ${MAX_PROMPT_LENGTH} characters`, "error");
            return;
        }
        
        if (sanitizedAgentPrompt.length > MAX_AGENT_PROMPT_LENGTH) {
            showNotification(`Agent prompt exceeds maximum length of ${MAX_AGENT_PROMPT_LENGTH} characters`, "error");
            return;
        }
        
        setLoading(true);
        setError(null);
        setSuccess(null);
        
        try {
            // Check balance first
            const balance = await contract.balanceOf(account, selectedThinkId);
            if (balance.toString() === "0") {
                showNotification("You don't own any tokens of this THINK", "error");
                setLoading(false);
                return;
            }
            
            // Estimate gas
            const gasEstimate = await estimateGas(
                contract,
                "updateThink",
                [selectedThinkId, sanitizedPrompt, sanitizedAgentPrompt]
            );
            
            const gasOptions = gasEstimate 
                ? { gasLimit: gasEstimate }
                : { gasLimit: 200000 };
            
            const tx = await contract.updateThink(
                selectedThinkId,
                sanitizedPrompt,
                sanitizedAgentPrompt,
                gasOptions
            );
            
            setPendingTx(tx.hash);
            showNotification(`Transaction submitted: ${formatAddress(tx.hash)}`, "info");
            
            const timeoutId = setTimeout(() => {
                setPendingTx(null);
                showNotification("Transaction is taking longer than expected.", "error");
            }, TRANSACTION_TIMEOUT);
            
            const receipt = await tx.wait();
            clearTimeout(timeoutId);
            setPendingTx(null);
            
            // Add to transaction history
            setTransactionHistory(prev => [{
                hash: receipt.transactionHash,
                type: "update",
                thinkId: selectedThinkId,
                timestamp: Date.now()
            }, ...prev]);
            
            showNotification(`THINK #${selectedThinkId} updated successfully!`, "success");
            
            // Reset form
            setUpdatePrompt("");
            setUpdateAgentPrompt("");
            setSelectedThinkId(null);
            
            // Refresh token list
            await fetchThinkTokens(account);
        } catch (error) {
            console.error("Update error:", error);
            setPendingTx(null);
            let errorMsg = "Unknown error";
            
            if (error.code === 4001) {
                errorMsg = "Transaction rejected by user";
            } else if (error.reason) {
                errorMsg = error.reason;
            } else if (error.message) {
                errorMsg = error.message;
            }
            
            showNotification("Failed to update THINK: " + errorMsg, "error");
        } finally {
            setLoading(false);
        }
    };

    const fetchThinkTokens = useCallback(async (userAddress) => {
        if (!contract || !userAddress) return;
        
        setFetchingTokens(true);
        setError(null);
        
        try {
            const tokens = [];
            const batchSize = 10; // Process in batches for better performance
            const promises = [];
            
            for (let i = 1; i <= MAX_TOKEN_CHECK; i += batchSize) {
                const batch = [];
                for (let j = i; j < i + batchSize && j <= MAX_TOKEN_CHECK; j++) {
                    batch.push(
                        (async () => {
                            try {
                                const balance = await contract.balanceOf(userAddress, j);
                                if (balance.gt(0)) {
                                    const thinkData = await contract.getThinkData(j);
                                    const uri = await contract.uri(j);
                                    
                                    return {
                                        thinkId: j,
                                        balance: balance.toString(),
                                        prompt: thinkData.prompt,
                                        agentPrompt: thinkData.agentPrompt,
                                        lastUpdate: new Date(thinkData.lastUpdate * 1000).toLocaleString(),
                                        active: thinkData.active,
                                        dimensions: thinkData.dimensions,
                                        batchSize: thinkData.batchSize,
                                        uri: uri
                                    };
                                }
                            } catch (err) {
                                // Token doesn't exist or error fetching, continue
                                return null;
                            }
                        })()
                    );
                }
                
                const batchResults = await Promise.all(batch);
                tokens.push(...batchResults.filter(t => t !== null));
            }
            
            setThinkTokens(tokens);
        } catch (error) {
            console.error("Fetch error:", error);
            setError("Failed to fetch THINK tokens: " + error.message);
        } finally {
            setFetchingTokens(false);
        }
    }, [contract]);

    const selectThinkForUpdate = (thinkId) => {
        const think = thinkTokens.find(t => t.thinkId === thinkId);
        if (think) {
            setSelectedThinkId(thinkId);
            setUpdatePrompt(think.prompt);
            setUpdateAgentPrompt(think.agentPrompt);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text).then(() => {
            showNotification("Copied to clipboard!", "success");
        }).catch(() => {
            showNotification("Failed to copy to clipboard", "error");
        });
    };

    const getExplorerUrl = (hash) => {
        // Update with actual block explorer URL for ARC Testnet
        return `https://explorer.arc.network/tx/${hash}`;
    };

    return (
        <div className="app">
            <header>
                <h1>DAIO Dynamic NFT (dNFT) dApp</h1>
                <p>Manage THINK implementations on ARC Testnet</p>
                {account && (
                    <p className="account-info">
                        Connected: {formatAddress(account)}
                        <button 
                            className="copy-btn"
                            onClick={() => copyToClipboard(account)}
                            title="Copy address"
                        >
                            📋
                        </button>
                    </p>
                )}
            </header>
            
            {error && (
                <div className="error-banner">
                    <p>{error}</p>
                    <button onClick={() => setError(null)}>Dismiss</button>
                </div>
            )}
            
            {success && (
                <div className="success-banner">
                    <p>{success}</p>
                    <button onClick={() => setSuccess(null)}>Dismiss</button>
                </div>
            )}
            
            {pendingTx && (
                <div className="pending-banner">
                    <p>⏳ Transaction pending: <a href={getExplorerUrl(pendingTx)} target="_blank" rel="noopener noreferrer">{formatAddress(pendingTx)}</a></p>
                </div>
            )}
            
            <main>
                {!account ? (
                    <div className="connect-section">
                        <h2>Connect Your Wallet</h2>
                        <p>Please connect your MetaMask wallet to continue</p>
                        <button onClick={connectWallet} className="connect-btn">
                            Connect Wallet
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Create THINK Section */}
                        <section className="create-section">
                            <h2>Create New THINK Batch</h2>
                            {!isMinter && (
                                <div className="warning-banner">
                                    <p>⚠️ You need MINTER_ROLE to create THINK batches. Contact an administrator to grant this role.</p>
                                </div>
                            )}
                            <div className="form-group">
                                <label>
                                    Prompt:
                                    <textarea
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                        placeholder="Enter the THINK prompt"
                                        rows={3}
                                        maxLength={MAX_PROMPT_LENGTH}
                                    />
                                    <span className="char-count">{prompt.length}/{MAX_PROMPT_LENGTH}</span>
                                </label>
                            </div>
                            <div className="form-group">
                                <label>
                                    Agent Prompt:
                                    <textarea
                                        value={agentPrompt}
                                        onChange={(e) => setAgentPrompt(e.target.value)}
                                        placeholder="Enter the agent-specific prompt"
                                        rows={3}
                                        maxLength={MAX_AGENT_PROMPT_LENGTH}
                                    />
                                    <span className="char-count">{agentPrompt.length}/{MAX_AGENT_PROMPT_LENGTH}</span>
                                </label>
                            </div>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>
                                        Dimensions:
                                        <input
                                            type="number"
                                            value={dimensions}
                                            onChange={(e) => setDimensions(parseInt(e.target.value) || 8)}
                                            min={MIN_DIMENSIONS}
                                            max={MAX_DIMENSIONS}
                                        />
                                    </label>
                                </div>
                                <div className="form-group">
                                    <label>
                                        Batch Size:
                                        <input
                                            type="number"
                                            value={batchSize}
                                            onChange={(e) => setBatchSize(parseInt(e.target.value) || 1)}
                                            min={MIN_BATCH_SIZE}
                                            max={MAX_BATCH_SIZE}
                                        />
                                    </label>
                                </div>
                                <div className="form-group">
                                    <label>
                                        Amount:
                                        <input
                                            type="number"
                                            value={amount}
                                            onChange={(e) => setAmount(parseInt(e.target.value) || 1)}
                                            min={MIN_AMOUNT}
                                        />
                                    </label>
                                </div>
                            </div>
                            <button 
                                onClick={createThinkBatch} 
                                disabled={loading || !isMinter || fetchingTokens}
                                className="action-btn"
                                title={!isMinter ? "MINTER_ROLE required" : ""}
                            >
                                {loading ? "Creating..." : "Create THINK Batch"}
                            </button>
                        </section>

                        {/* Update THINK Section */}
                        {thinkTokens.length > 0 && (
                            <section className="update-section">
                                <h2>Update Existing THINK</h2>
                                <div className="form-group">
                                    <label>
                                        Select THINK to Update:
                                        <select
                                            value={selectedThinkId || ""}
                                            onChange={(e) => {
                                                const thinkId = e.target.value ? parseInt(e.target.value) : null;
                                                if (thinkId) selectThinkForUpdate(thinkId);
                                            }}
                                        >
                                            <option value="">-- Select THINK --</option>
                                            {thinkTokens.map(think => (
                                                <option key={think.thinkId} value={think.thinkId}>
                                                    THINK #{think.thinkId} (Balance: {think.balance})
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                </div>
                                {selectedThinkId && (
                                    <>
                                        <div className="form-group">
                                            <label>
                                                New Prompt:
                                                <textarea
                                                    value={updatePrompt}
                                                    onChange={(e) => setUpdatePrompt(e.target.value)}
                                                    rows={3}
                                                    maxLength={MAX_PROMPT_LENGTH}
                                                />
                                                <span className="char-count">{updatePrompt.length}/{MAX_PROMPT_LENGTH}</span>
                                            </label>
                                        </div>
                                        <div className="form-group">
                                            <label>
                                                New Agent Prompt:
                                                <textarea
                                                    value={updateAgentPrompt}
                                                    onChange={(e) => setUpdateAgentPrompt(e.target.value)}
                                                    rows={3}
                                                    maxLength={MAX_AGENT_PROMPT_LENGTH}
                                                />
                                                <span className="char-count">{updateAgentPrompt.length}/{MAX_AGENT_PROMPT_LENGTH}</span>
                                            </label>
                                        </div>
                                        <button 
                                            onClick={updateThink} 
                                            disabled={loading || fetchingTokens}
                                            className="action-btn"
                                        >
                                            {loading ? "Updating..." : "Update THINK"}
                                        </button>
                                    </>
                                )}
                            </section>
                        )}

                        {/* Your THINK Tokens Section */}
                        <section className="tokens-section">
                            <div className="section-header">
                                <h2>Your THINK Tokens</h2>
                                <button 
                                    onClick={() => fetchThinkTokens(account)}
                                    disabled={fetchingTokens}
                                    className="refresh-btn"
                                >
                                    {fetchingTokens ? "Refreshing..." : "🔄 Refresh"}
                                </button>
                            </div>
                            {fetchingTokens && thinkTokens.length === 0 ? (
                                <p>Loading your THINK tokens...</p>
                            ) : thinkTokens.length === 0 ? (
                                <p>You don't own any THINK tokens yet. Create one above!</p>
                            ) : (
                                <div className="tokens-container">
                                    {thinkTokens.map((think) => (
                                        <div className="token-card" key={think.thinkId}>
                                            <h3>THINK #{think.thinkId}</h3>
                                            <div className="token-info">
                                                <p><strong>Balance:</strong> {think.balance}</p>
                                                <p><strong>Dimensions:</strong> {think.dimensions}</p>
                                                <p><strong>Batch Size:</strong> {think.batchSize}</p>
                                                <p><strong>Status:</strong> {think.active ? "✅ Active" : "❌ Inactive"}</p>
                                                <p><strong>Last Update:</strong> {think.lastUpdate}</p>
                                            </div>
                                            <div className="token-prompts">
                                                <details>
                                                    <summary>Prompt</summary>
                                                    <p className="prompt-text">{think.prompt}</p>
                                                </details>
                                                <details>
                                                    <summary>Agent Prompt</summary>
                                                    <p className="prompt-text">{think.agentPrompt}</p>
                                                </details>
                                            </div>
                                            <button
                                                onClick={() => selectThinkForUpdate(think.thinkId)}
                                                className="update-btn"
                                            >
                                                Update This THINK
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* Transaction History */}
                        {transactionHistory.length > 0 && (
                            <section className="history-section">
                                <h2>Recent Transactions</h2>
                                <div className="history-list">
                                    {transactionHistory.slice(0, 10).map((tx, idx) => (
                                        <div key={idx} className="history-item">
                                            <span className="tx-type">{tx.type}</span>
                                            <a 
                                                href={getExplorerUrl(tx.hash)} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="tx-link"
                                            >
                                                {formatAddress(tx.hash)}
                                            </a>
                                            {tx.thinkId && <span className="tx-think">THINK #{tx.thinkId}</span>}
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}
                    </>
                )}
            </main>
        </div>
    );
}

export default App;



<<<<<<< Current (Your changes)


=======
>>>>>>> Incoming (Background Agent changes)
