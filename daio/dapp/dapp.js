/**
 * DAIO voting UI – daio.pythai.net
 * Connect wallet, list proposals, vote, create proposal.
 * Set DAIO_BRIDGE_ADDRESS and optionally CHAIN_ID for your deployment.
 */
(function () {
  "use strict";

  const DAIO_BRIDGE_ADDRESS = "0x0000000000000000000000000000000000000000"; // Replace with your DAIOBridge address
  const CHAIN_ID = null; // e.g. 1 for mainnet, 11155111 for Sepolia; null = no check

  let provider = null;
  let signer = null;
  let contract = null;
  let connected = false;

  const connectBtn = document.getElementById("connect-btn");
  const accountEl = document.getElementById("account");
  const proposalList = document.getElementById("proposal-list");
  const messageEl = document.getElementById("message");
  const loadingEl = document.getElementById("loading");
  const createBtn = document.getElementById("create-btn");
  const titleInput = document.getElementById("title");
  const descriptionInput = document.getElementById("description");
  const projectIdInput = document.getElementById("project-id");

  function showMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = "show " + (type || "");
    messageEl.setAttribute("aria-live", "polite");
  }

  function hideMessage() {
    messageEl.className = "";
    messageEl.textContent = "";
  }

  function getContract() {
    if (!contract && signer && DAIO_BRIDGE_ADDRESS !== "0x0000000000000000000000000000000000000000") {
      contract = new ethers.Contract(DAIO_BRIDGE_ADDRESS, DAIO_BRIDGE_ABI, signer);
    }
    return contract;
  }

  async function connect() {
    try {
      if (!window.ethereum) {
        showMessage("Install MetaMask or another Web3 wallet.", "error");
        return;
      }
      provider = new ethers.providers.Web3Provider(window.ethereum);
      const accounts = await provider.send("eth_requestAccounts", []);
      if (accounts.length === 0) {
        showMessage("No account selected.", "error");
        return;
      }
      signer = provider.getSigner();
      if (CHAIN_ID != null) {
        const network = await provider.getNetwork();
        if (Number(network.chainId) !== CHAIN_ID) {
          showMessage("Wrong network. Switch to the required chain in your wallet.", "error");
          return;
        }
      }
      connected = true;
      const addr = await signer.getAddress();
      accountEl.textContent = addr.slice(0, 6) + "…" + addr.slice(-4);
      connectBtn.textContent = "Disconnect";
      connectBtn.onclick = disconnect;
      hideMessage();
      await loadProposals();
    } catch (e) {
      showMessage(e.message || "Connection failed.", "error");
    }
  }

  function disconnect() {
    provider = null;
    signer = null;
    contract = null;
    connected = false;
    accountEl.textContent = "";
    connectBtn.textContent = "Connect wallet";
    connectBtn.onclick = connect;
    proposalList.innerHTML = "";
    loadingEl.style.display = "block";
    loadingEl.textContent = "Connect your wallet.";
  }

  function statusClass(s) {
    const i = Number(s);
    if (i === 0) return "status-pending";
    if (i === 1) return "status-active";
    if (i === 2) return "status-succeeded";
    if (i === 3) return "status-defeated";
    if (i === 4) return "status-executed";
    if (i === 5) return "status-cancelled";
    return "status-pending";
  }

  async function loadProposals() {
    const c = getContract();
    if (!c) {
      loadingEl.textContent = "Set DAIO_BRIDGE_ADDRESS in dapp.js and connect wallet.";
      return;
    }
    loadingEl.textContent = "Loading proposals…";
    loadingEl.style.display = "block";
    proposalList.innerHTML = "";
    try {
      const count = await c.proposalCount();
      const n = count.toNumber ? count.toNumber() : Number(count);
      if (n === 0) {
        loadingEl.textContent = "No proposals yet.";
        return;
      }
      loadingEl.style.display = "none";
      for (let i = 1; i <= n; i++) {
        const [proposer, title, status, forVotes, againstVotes] = await c.getProposal(i);
        const statusName = PROPOSAL_STATUS[Number(status)] || "Unknown";
        const li = document.createElement("li");
        li.innerHTML =
          "<h3>" + escapeHtml(title || "#" + i) + "</h3>" +
          "<div class=\"meta\">#" + i + " · " + escapeHtml(shortAddr(proposer)) + " · <span class=\"status-badge " + statusClass(status) + "\">" + statusName + "</span></div>" +
          "<div class=\"votes\"><span class=\"for\">For: " + (forVotes.toString ? forVotes.toString() : forVotes) + "</span> <span class=\"against\">Against: " + (againstVotes.toString ? againstVotes.toString() : againstVotes) + "</span></div>" +
          "<div class=\"actions\">" +
          "<button type=\"button\" class=\"btn btn-success\" data-id=\"" + i + "\" data-vote=\"1\">Vote for</button>" +
          "<button type=\"button\" class=\"btn btn-danger\" data-id=\"" + i + "\" data-vote=\"0\">Vote against</button>" +
          "</div>";
        proposalList.appendChild(li);
      }
      proposalList.querySelectorAll(".actions button").forEach(function (btn) {
        btn.addEventListener("click", onVoteClick);
      });
    } catch (e) {
      loadingEl.textContent = "Error loading proposals: " + (e.message || e);
    }
  }

  function escapeHtml(s) {
    if (s == null) return "";
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function shortAddr(addr) {
    if (!addr) return "";
    const s = typeof addr === "string" ? addr : (addr.toString && addr.toString());
    if (!s || s.length < 10) return s;
    return s.slice(0, 6) + "…" + s.slice(-4);
  }

  async function onVoteClick(ev) {
    const id = ev.target.getAttribute("data-id");
    const support = ev.target.getAttribute("data-vote") === "1";
    const c = getContract();
    if (!c || !connected) {
      showMessage("Connect wallet first.", "error");
      return;
    }
    ev.target.disabled = true;
    try {
      const tx = await c.vote(id, support);
      showMessage("Transaction sent. Waiting for confirmation…", "");
      await tx.wait();
      showMessage("Vote recorded.", "success");
      await loadProposals();
    } catch (e) {
      showMessage(e.message || "Vote failed.", "error");
      ev.target.disabled = false;
    }
  }

  createBtn.addEventListener("click", async function () {
    const c = getContract();
    if (!c || !connected) {
      showMessage("Connect wallet first.", "error");
      return;
    }
    const title = titleInput.value.trim();
    const description = descriptionInput.value.trim();
    const projectId = projectIdInput.value.trim() || "mindx";
    if (!title) {
      showMessage("Enter a title.", "error");
      return;
    }
    createBtn.disabled = true;
    try {
      const tx = await c.createProposal(
        title,
        description || title,
        0, // Generic
        projectId,
        "0x0000000000000000000000000000000000000000",
        "0x"
      );
      showMessage("Create proposal sent. Waiting for confirmation…", "");
      await tx.wait();
      showMessage("Proposal created.", "success");
      titleInput.value = "";
      descriptionInput.value = "";
      await loadProposals();
    } catch (e) {
      showMessage(e.message || "Create proposal failed.", "error");
    }
    createBtn.disabled = false;
  });

  connectBtn.onclick = connect;
})();
