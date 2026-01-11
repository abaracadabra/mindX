import React, { useState, useEffect } from "react";
import { ethers } from "ethers";
import Chart from "chart.js/auto";
import "./style.css";

// Contract configuration - Update these after deployment
const DNFT_CONTRACT_ADDRESS = process.env.REACT_APP_DNFT_ADDRESS || "YOUR_DNFT_CONTRACT_ADDRESS";
const RPC_URL = process.env.REACT_APP_RPC_URL || "https://rpc.arc.network"; // ARC Testnet
const ARC_CHAIN_ID = parseInt(process.env.REACT_APP_CHAIN_ID || "1243");

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

function App() {
    const [provider, setProvider] = useState(null);
    const [signer, setSigner] = useState(null);
    const [contract, setContract] = useState(null);
    const [account, setAccount] = useState(null);
    const [thinkTokens, setThinkTokens] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isMinter, setIsMinter] = useState(false);
    const [networkCorrect, setNetworkCorrect] = useState(false);
    
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

    useEffect(() => {
        async function init() {
            if (window.ethereum) {
                try {
                    // Use ethers v5
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
                    
                    setProvider(tempProvider);
                    setSigner(tempSigner);
                    setContract(tempContract);
                    
                    // Get connected account
                    const accounts = await window.ethereum.request({ method: "eth_accounts" });
                    if (accounts.length > 0) {
                        const userAccount = accounts[0];
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
                    }
                    
                    // Listen for account changes
                    window.ethereum.on("accountsChanged", async (accounts) => {
                        if (accounts.length > 0) {
                            const userAccount = accounts[0];
                            setAccount(userAccount);
                            
                            // Recheck MINTER_ROLE
                            try {
                                const minterRole = await tempContract.MINTER_ROLE();
                                const hasMinterRole = await tempContract.hasRole(minterRole, userAccount);
                                setIsMinter(hasMinterRole);
                            } catch (err) {
                                console.warn("Could not check MINTER_ROLE:", err);
                                setIsMinter(false);
                            }
                            
                            await fetchThinkTokens(userAccount);
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
    }, []);

    const connectWallet = async () => {
        try {
            if (!window.ethereum) {
                alert("Please install MetaMask!");
                return;
            }
            
            const accounts = await window.ethereum.request({
                method: "eth_requestAccounts"
            });
            
            if (accounts.length > 0) {
                const userAccount = accounts[0];
                setAccount(userAccount);
                
                // Use ethers v5
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
            }
        } catch (error) {
            console.error("Connection error:", error);
            setError("Failed to connect wallet: " + error.message);
        }
    };

    const createThinkBatch = async () => {
        if (!contract || !account) {
            alert("Please connect your wallet first!");
            return;
        }
        
        if (!isMinter) {
            alert("You need MINTER_ROLE to create THINK batches. Please contact an administrator.");
            return;
        }
        
        if (!networkCorrect) {
            alert("Please switch to the correct network (ARC Testnet)");
            return;
        }
        
        if (!prompt.trim() || !agentPrompt.trim()) {
            alert("Please enter both prompt and agent prompt");
            return;
        }
        
        if (dimensions < 1 || dimensions > 255) {
            alert("Dimensions must be between 1 and 255");
            return;
        }
        
        if (batchSize < 1 || batchSize > 65535) {
            alert("Batch size must be between 1 and 65535");
            return;
        }
        
        if (amount < 1) {
            alert("Amount must be at least 1");
            return;
        }
        
        setLoading(true);
        setError(null);
        
        try {
            const tx = await contract.createThinkBatch(
                account,
                prompt,
                agentPrompt,
                dimensions,
                batchSize,
                amount,
                { gasLimit: 500000 } // Adjust as needed
            );
            
            const receipt = await tx.wait();
            
            // Find the ThinkCreated event (ethers v5 format)
            let thinkId = null;
            if (receipt.events) {
                const thinkCreatedEvent = receipt.events.find(
                    e => e.event === "ThinkCreated"
                );
                if (thinkCreatedEvent) {
                    thinkId = thinkCreatedEvent.args.thinkId.toString();
                }
            }
            
            if (thinkId) {
                alert(`THINK batch created successfully! Think ID: ${thinkId}`);
                
                // Reset form
                setPrompt("");
                setAgentPrompt("");
                setDimensions(8);
                setBatchSize(1);
                setAmount(1);
                
                // Refresh token list
                await fetchThinkTokens(account);
            } else {
                alert("THINK created but event not found. Please refresh.");
            }
        } catch (error) {
            console.error("Create error:", error);
            const errorMsg = error.reason || error.message || "Unknown error";
            setError("Failed to create THINK: " + errorMsg);
            alert("Error creating THINK: " + errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const updateThink = async () => {
        if (!contract || !selectedThinkId) {
            alert("Please select a THINK to update");
            return;
        }
        
        if (!updatePrompt.trim() || !updateAgentPrompt.trim()) {
            alert("Please enter both new prompt and agent prompt");
            return;
        }
        
        setLoading(true);
        setError(null);
        
        try {
            // Check balance first
            const balance = await contract.balanceOf(account, selectedThinkId);
            if (balance.toString() === "0") {
                alert("You don't own any tokens of this THINK");
                setLoading(false);
                return;
            }
            
            const tx = await contract.updateThink(
                selectedThinkId,
                updatePrompt,
                updateAgentPrompt,
                { gasLimit: 200000 }
            );
            
            await tx.wait();
            alert(`THINK #${selectedThinkId} updated successfully!`);
            
            // Reset form
            setUpdatePrompt("");
            setUpdateAgentPrompt("");
            setSelectedThinkId(null);
            
            // Refresh token list
            await fetchThinkTokens(account);
        } catch (error) {
            console.error("Update error:", error);
            setError("Failed to update THINK: " + (error.reason || error.message));
            alert("Error updating THINK: " + (error.reason || error.message));
        } finally {
            setLoading(false);
        }
    };

    const fetchThinkTokens = async (userAddress) => {
        if (!contract || !userAddress) return;
        
        setLoading(true);
        setError(null);
        
        try {
            // Since ERC1155 doesn't have a direct way to enumerate tokens,
            // we'll need to track created THINKs or use events
            // For now, we'll try to fetch a range of thinkIds
            const tokens = [];
            const maxCheck = 100; // Check up to 100 thinkIds
            
            for (let i = 1; i <= maxCheck; i++) {
                try {
                    const balance = await contract.balanceOf(userAddress, i);
                    if (balance.gt(0)) {
                        const thinkData = await contract.getThinkData(i);
                        const uri = await contract.uri(i);
                        
                        tokens.push({
                            thinkId: i,
                            balance: balance.toString(),
                            prompt: thinkData.prompt,
                            agentPrompt: thinkData.agentPrompt,
                            lastUpdate: new Date(thinkData.lastUpdate * 1000).toLocaleString(),
                            active: thinkData.active,
                            dimensions: thinkData.dimensions,
                            batchSize: thinkData.batchSize,
                            uri: uri
                        });
                    }
                } catch (err) {
                    // Token doesn't exist or error fetching, continue
                    continue;
                }
            }
            
            setThinkTokens(tokens);
        } catch (error) {
            console.error("Fetch error:", error);
            setError("Failed to fetch THINK tokens: " + error.message);
        } finally {
            setLoading(false);
        }
    };

    const selectThinkForUpdate = (thinkId) => {
        const think = thinkTokens.find(t => t.thinkId === thinkId);
        if (think) {
            setSelectedThinkId(thinkId);
            setUpdatePrompt(think.prompt);
            setUpdateAgentPrompt(think.agentPrompt);
        }
    };

    const generateVisualization = (think) => {
        // Generate a chart visualization based on THINK data
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        
        // Create a simple visualization
        const chart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Dimensions", "Batch Size", "Balance"],
                datasets: [{
                    label: "THINK Metrics",
                    data: [think.dimensions, think.batchSize, parseInt(think.balance)],
                    backgroundColor: ["#4CAF50", "#2196F3", "#FF9800"]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: `THINK #${think.thinkId}`
                    }
                }
            }
        });
        
        return canvas.toDataURL("image/png");
    };

    return (
        <div className="app">
            <header>
                <h1>DAIO Dynamic NFT (dNFT) dApp</h1>
                <p>Manage THINK implementations on ARC Testnet</p>
                {account && (
                    <p className="account-info">
                        Connected: {account.substring(0, 6)}...{account.substring(38)}
                    </p>
                )}
            </header>
            
            {error && (
                <div className="error-banner">
                    <p>{error}</p>
                    <button onClick={() => setError(null)}>Dismiss</button>
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
                                    />
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
                                    />
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
                                            min="1"
                                            max="255"
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
                                            min="1"
                                            max="65535"
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
                                            min="1"
                                        />
                                    </label>
                                </div>
                            </div>
                            <button 
                                onClick={createThinkBatch} 
                                disabled={loading || !isMinter}
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
                                                />
                                            </label>
                                        </div>
                                        <div className="form-group">
                                            <label>
                                                New Agent Prompt:
                                                <textarea
                                                    value={updateAgentPrompt}
                                                    onChange={(e) => setUpdateAgentPrompt(e.target.value)}
                                                    rows={3}
                                                />
                                            </label>
                                        </div>
                                        <button 
                                            onClick={updateThink} 
                                            disabled={loading}
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
                            <h2>Your THINK Tokens</h2>
                            {loading && thinkTokens.length === 0 ? (
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
                                                <p><strong>Status:</strong> {think.active ? "Active" : "Inactive"}</p>
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
                    </>
                )}
            </main>
        </div>
    );
}

export default App;
