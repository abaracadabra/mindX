/**
 * S.M.A.I.R.T Presale UI – connect wallet, contribute, claim, refund, owner actions.
 * Set PRESALE_ADDRESS (and optionally CHAIN_ID) for your deployment.
 */
(function () {
  "use strict";

  const PRESALE_ADDRESS = "0x0000000000000000000000000000000000000000"; // Replace with BondingCurvePresaleSMAIRT address
  const FACTORY_ADDRESS = "0x0000000000000000000000000000000000000000"; // Replace with BondingCurveFactory address
  const CHAIN_ID = null; // e.g. 1 for mainnet, 11155111 for Sepolia; null = no check

  const STATE_NAMES = ["", "Initialized", "Active", "Canceled", "Finalized", "Failed"];

  let provider = null;
  let signer = null;
  let presaleContract = null;
  let lockerContract = null;
  let connected = false;
  let userAddress = null;
  let isOwner = false;

  const connectBtn = document.getElementById("connect-btn");
  const accountEl = document.getElementById("account");
  const messageEl = document.getElementById("message");
  const stateContent = document.getElementById("state-content");
  const contributeAmount = document.getElementById("contribute-amount");
  const contributeBtn = document.getElementById("contribute-btn");
  const claimableAmount = document.getElementById("claimable-amount");
  const claimBtn = document.getElementById("claim-btn");
  const refundAmount = document.getElementById("refund-amount");
  const refundBtn = document.getElementById("refund-btn");
  const activateBtn = document.getElementById("activate-btn");
  const finalizeBtn = document.getElementById("finalize-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const lockContent = document.getElementById("lock-content");
  const withdrawLpBtn = document.getElementById("withdraw-lp-btn");
  const launchBtn = document.getElementById("launch-btn");
  const launchResult = document.getElementById("launch-result");

  function showMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = "show " + (type || "");
    messageEl.setAttribute("aria-live", "polite");
  }

  function hideMessage() {
    messageEl.className = "";
    messageEl.textContent = "";
  }

  function shortAddr(addr) {
    if (!addr) return "";
    const s = typeof addr === "string" ? addr : (addr.toString && addr.toString());
    if (!s || s.length < 10) return s;
    return s.slice(0, 6) + "…" + s.slice(-4);
  }

  function formatEth(wei) {
    if (!wei || wei.isZero()) return "0";
    return ethers.utils.formatEther(wei);
  }

  function formatToken(amount) {
    if (!amount || amount.isZero()) return "0";
    try {
      return ethers.utils.formatUnits(amount, 18);
    } catch (_) {
      return amount.toString();
    }
  }

  function getPresale() {
    if (!signer || PRESALE_ADDRESS === "0x0000000000000000000000000000000000000000") return null;
    if (!presaleContract) presaleContract = new ethers.Contract(PRESALE_ADDRESS, PresaleABI, signer);
    return presaleContract;
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
      userAddress = await signer.getAddress();
      if (CHAIN_ID != null) {
        const network = await provider.getNetwork();
        if (Number(network.chainId) !== CHAIN_ID) {
          showMessage("Wrong network. Switch to the required chain in your wallet.", "error");
          return;
        }
      }
      connected = true;
      accountEl.textContent = shortAddr(userAddress);
      connectBtn.textContent = "Disconnect";
      connectBtn.onclick = disconnect;
      hideMessage();
      await refresh();
    } catch (e) {
      showMessage(e.message || "Connection failed.", "error");
    }
  }

  function disconnect() {
    provider = null;
    signer = null;
    presaleContract = null;
    lockerContract = null;
    connected = false;
    userAddress = null;
    isOwner = false;
    accountEl.textContent = "";
    connectBtn.textContent = "Connect wallet";
    connectBtn.onclick = connect;
    stateContent.innerHTML = "<p>Connect your wallet.</p>";
    claimableAmount.textContent = "—";
    refundAmount.textContent = "—";
    lockContent.innerHTML = "<p>—</p>";
  }

  async function refresh() {
    const c = getPresale();
    if (!c) {
      stateContent.innerHTML = "<p>Set <code>PRESALE_ADDRESS</code> in smairt.js and connect wallet.</p>";
      return;
    }
    try {
      const [state, nativeRaised, opts, owner] = await Promise.all([
        c.state(),
        c.nativeRaised(),
        c.options(),
        c.owner()
      ]);
      const stateNum = state;
      const stateName = STATE_NAMES[stateNum] || "Unknown";
      isOwner = owner && owner.toLowerCase() === userAddress.toLowerCase();

      let contribWei = ethers.BigNumber.from(0);
      let claimed = false;
      let tokensBoughtForSale = ethers.BigNumber.from(0);
      if (userAddress) {
        contribWei = await c.contributions(userAddress);
        claimed = await c.claimed(userAddress);
        tokensBoughtForSale = await c.tokensBoughtForSale();
      }

      const hardCap = opts.hardCapNative || opts[0];
      const softCap = opts.softCapNative || opts[1];
      const maxPerUser = opts.maxContributionPerUserNative || opts[2];
      const minPerUser = opts.minContributionPerUserNative || opts[3];
      const startTime = opts.startTime != null ? opts.startTime : opts[4];
      const endTime = opts.endTime != null ? opts.endTime : opts[5];

      stateContent.innerHTML =
        "<div class=\"stat\"><span class=\"label\">State</span><span class=\"value\"><span class=\"status-badge status-" + stateName.toLowerCase() + "\">" + stateName + "</span></span></div>" +
        "<div class=\"stat\"><span class=\"label\">Raised</span><span class=\"value\">" + formatEth(nativeRaised) + " ETH</span></div>" +
        "<div class=\"stat\"><span class=\"label\">Soft cap</span><span class=\"value\">" + formatEth(softCap) + " ETH</span></div>" +
        "<div class=\"stat\"><span class=\"label\">Hard cap</span><span class=\"value\">" + formatEth(hardCap) + " ETH</span></div>" +
        "<div class=\"stat\"><span class=\"label\">Min / max per wallet</span><span class=\"value\">" + formatEth(minPerUser) + " / " + formatEth(maxPerUser) + " ETH</span></div>" +
        "<div class=\"stat\"><span class=\"label\">Your contribution</span><span class=\"value\">" + formatEth(contribWei) + " ETH</span></div>";

      document.getElementById("panel-contribute").style.display = stateNum === 2 ? "block" : "none";
      document.getElementById("panel-claim").style.display = stateNum === 4 ? "block" : "none";
      document.getElementById("panel-refund").style.display = stateNum === 3 || stateNum === 5 ? "block" : "none";
      document.getElementById("panel-owner").style.display = isOwner ? "block" : "none";

      if (stateNum === 4 && !claimed && contribWei.gt(0) && tokensBoughtForSale.gt(0)) {
        const nativeRaisedAgain = await c.nativeRaised();
        const claimable = nativeRaisedAgain.isZero() ? ethers.BigNumber.from(0) : contribWei.mul(tokensBoughtForSale).div(nativeRaisedAgain);
        claimableAmount.textContent = formatToken(claimable) + " tokens";
      } else if (stateNum === 4) {
        claimableAmount.textContent = claimed ? "Already claimed" : "0";
      } else {
        claimableAmount.textContent = "—";
      }

      if (stateNum === 3 || stateNum === 5) {
        refundAmount.textContent = formatEth(contribWei) + " ETH";
      } else {
        refundAmount.textContent = "—";
      }

      const lockerAddr = await c.locker();
      const lpTokenAddr = await c.lpTokenAddress();
      if (stateNum === 4 && lockerAddr !== ethers.constants.AddressZero && lpTokenAddr !== ethers.constants.AddressZero) {
        if (!lockerContract) lockerContract = new ethers.Contract(lockerAddr, LiquidityLockerABI, signer);
        const beneficiary = opts.liquidityBeneficiaryAddress != null ? opts.liquidityBeneficiaryAddress : opts[20];
        const ben = beneficiary !== ethers.constants.AddressZero ? beneficiary : owner;
        try {
          const [amount, releaseTime, isLocked] = await lockerContract.getLockDetails(lpTokenAddr, ben);
          const releaseDate = releaseTime.gt(0) ? new Date(releaseTime.toNumber() * 1000).toISOString() : "—";
          lockContent.innerHTML =
            "<div class=\"stat\"><span class=\"label\">LP amount</span><span class=\"value\">" + amount.toString() + "</span></div>" +
            "<div class=\"stat\"><span class=\"label\">Release time</span><span class=\"value\">" + releaseDate + "</span></div>" +
            "<div class=\"stat\"><span class=\"label\">Beneficiary</span><span class=\"value\">" + shortAddr(ben) + "</span></div>";
          withdrawLpBtn.style.display = ben.toLowerCase() === userAddress.toLowerCase() ? "inline-block" : "none";
        } catch (_) {
          lockContent.innerHTML = "<p>Could not load lock details.</p>";
          withdrawLpBtn.style.display = "none";
        }
      } else {
        lockContent.innerHTML = "<p>No LP lock or presale not finalized.</p>";
        withdrawLpBtn.style.display = "none";
      }

      activateBtn.style.display = isOwner && stateNum === 1 ? "inline-block" : "none";
      finalizeBtn.style.display = isOwner && stateNum === 2 ? "inline-block" : "none";
      cancelBtn.style.display = isOwner && (stateNum === 1 || stateNum === 2) ? "inline-block" : "none";
    } catch (e) {
      stateContent.innerHTML = "<p>Error loading presale: " + (e.message || e) + "</p>";
    }
  }

  contributeBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !connected) { showMessage("Connect wallet first.", "error"); return; }
    const raw = contributeAmount.value.trim();
    if (!raw) { showMessage("Enter amount (ETH).", "error"); return; }
    let valueWei;
    try {
      valueWei = ethers.utils.parseEther(raw);
    } catch (_) {
      showMessage("Invalid ETH amount.", "error");
      return;
    }
    contributeBtn.disabled = true;
    try {
      const tx = await c.buy({ value: valueWei });
      showMessage("Transaction sent. Waiting for confirmation…", "");
      await tx.wait();
      showMessage("Contribution recorded.", "success");
      contributeAmount.value = "";
      await refresh();
    } catch (e) {
      showMessage(e.message || "Contribute failed.", "error");
    }
    contributeBtn.disabled = false;
  });

  claimBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !connected) { showMessage("Connect wallet first.", "error"); return; }
    claimBtn.disabled = true;
    try {
      const tx = await c.claim();
      showMessage("Claim sent. Waiting for confirmation…", "");
      await tx.wait();
      showMessage("Tokens claimed.", "success");
      await refresh();
    } catch (e) {
      showMessage(e.message || "Claim failed.", "error");
    }
    claimBtn.disabled = false;
  });

  refundBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !connected) { showMessage("Connect wallet first.", "error"); return; }
    refundBtn.disabled = true;
    try {
      const tx = await c.refund();
      showMessage("Refund sent. Waiting for confirmation…", "");
      await tx.wait();
      showMessage("Refund completed.", "success");
      await refresh();
    } catch (e) {
      showMessage(e.message || "Refund failed.", "error");
    }
    refundBtn.disabled = false;
  });

  activateBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !connected) { showMessage("Connect wallet first.", "error"); return; }
    activateBtn.disabled = true;
    try {
      const tx = await c.activate();
      await tx.wait();
      showMessage("Presale activated.", "success");
      await refresh();
    } catch (e) {
      showMessage(e.message || "Activate failed.", "error");
    }
    activateBtn.disabled = false;
  });

  finalizeBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !connected) { showMessage("Connect wallet first.", "error"); return; }
    finalizeBtn.disabled = true;
    try {
      const tx = await c.finalize();
      showMessage("Finalize sent. Waiting for confirmation…", "");
      await tx.wait();
      showMessage("Presale finalized.", "success");
      await refresh();
    } catch (e) {
      showMessage(e.message || "Finalize failed.", "error");
    }
    finalizeBtn.disabled = false;
  });

  cancelBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !connected) { showMessage("Connect wallet first.", "error"); return; }
    if (!confirm("Cancel the presale? Contributors will be able to refund.")) return;
    cancelBtn.disabled = true;
    try {
      const tx = await c.cancel();
      await tx.wait();
      showMessage("Presale canceled.", "success");
      await refresh();
    } catch (e) {
      showMessage(e.message || "Cancel failed.", "error");
    }
    cancelBtn.disabled = false;
  });

  withdrawLpBtn.addEventListener("click", async function () {
    const c = getPresale();
    if (!c || !lockerContract) { showMessage("Connect wallet first.", "error"); return; }
    const lpTokenAddr = await c.lpTokenAddress();
    withdrawLpBtn.disabled = true;
    try {
      const tx = await lockerContract.withdrawLP(lpTokenAddr);
      await tx.wait();
      showMessage("LP withdrawn.", "success");
      await refresh();
    } catch (e) {
      showMessage(e.message || "Withdraw LP failed.", "error");
    }
    withdrawLpBtn.disabled = false;
  });

  function defaultPresaleOptions() {
    return {
      hardCapNative: 0,
      softCapNative: 0,
      maxContributionPerUserNative: 0,
      minContributionPerUserNative: 0,
      startTime: 0,
      endTime: 0,
      useLiquidityFreePresale: false,
      useTeamAllocationFromFunds: false,
      useTeamAllocationFromSupply: false,
      teamAllocationFromFundsBps: 0,
      teamAllocationFromSupplyBps: 0,
      teamWallet: ethers.constants.AddressZero,
      nativeForLiquidityBps: 0,
      presaleNativeForMarketingBps: 0,
      presaleNativeForDevBps: 0,
      presaleNativeForDaoBps: 0,
      presaleMarketingWallet: ethers.constants.AddressZero,
      presaleDevWallet: ethers.constants.AddressZero,
      presaleDaoWallet: ethers.constants.AddressZero,
      liquidityLockDurationDays: 0,
      liquidityBeneficiaryAddress: ethers.constants.AddressZero,
      minTokensForLiquidity: 0,
      minTokensForSale: 0
    };
  }

  function defaultLiquidityTemplate() {
    return {
      mode: 0,
      enabled: false,
      v2: { router: ethers.constants.AddressZero, weth: ethers.constants.AddressZero, enabled: false },
      v3: { positionManager: ethers.constants.AddressZero, weth: ethers.constants.AddressZero, fee: 0, tickLower: 0, tickUpper: 0, enabled: false },
      v4: { poolManager: ethers.constants.AddressZero, poolId: "0x0000000000000000000000000000000000000000000000000000000000000000", hook: ethers.constants.AddressZero, enabled: false },
      token: ethers.constants.AddressZero,
      tokenAmount: 0,
      nativeAmount: 0,
      recipient: ethers.constants.AddressZero,
      deadline: 0
    };
  }

  document.querySelectorAll(".tab").forEach(function (t) {
    t.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (x) { x.classList.remove("active"); });
      document.getElementById("tab-presale").style.display = t.getAttribute("data-tab") === "presale" ? "block" : "none";
      document.getElementById("tab-launch").style.display = t.getAttribute("data-tab") === "launch" ? "block" : "none";
      t.classList.add("active");
    });
  });

  document.querySelectorAll("[data-preset]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var p = btn.getAttribute("data-preset");
      var val = p === "linear" ? "1000000000000000000" : p === "sqrt" ? "500000000000000000" : "1500000000000000000";
      document.getElementById("launch-p").value = val;
    });
  });

  launchBtn.addEventListener("click", async function () {
    if (!signer || !connected) { showMessage("Connect wallet first.", "error"); return; }
    if (FACTORY_ADDRESS === "0x0000000000000000000000000000000000000000") { showMessage("Set FACTORY_ADDRESS in smairt.js.", "error"); return; }
    var name = document.getElementById("launch-name").value.trim();
    var symbol = document.getElementById("launch-symbol").value.trim();
    var initialMint = document.getElementById("launch-initial-mint").value.trim() || "0";
    var k = document.getElementById("launch-k").value.trim() || "1000000000000";
    var pVal = document.getElementById("launch-p").value.trim() || "1000000000000000000";
    var protocolFee = document.getElementById("launch-protocol-fee").value.trim() || "0";
    var feeRecipient = document.getElementById("launch-fee-recipient").value.trim();
    var enablePresale = document.getElementById("launch-enable-presale").checked;
    launchResult.style.display = "none";
    var feeRecipientAddr = feeRecipient ? feeRecipient : ethers.constants.AddressZero;
    var args = {
      name: name || "",
      symbol: symbol || "",
      initialMintToOwner: ethers.BigNumber.from(initialMint),
      kUD60x18: ethers.BigNumber.from(k),
      pUD60x18: ethers.BigNumber.from(pVal),
      protocolFeeBps: parseInt(protocolFee, 10) || 0,
      feeRecipient: feeRecipientAddr,
      enablePresale: enablePresale,
      presaleOptions: defaultPresaleOptions(),
      provisioner: ethers.constants.AddressZero,
      liquidityTemplate: defaultLiquidityTemplate()
    };
    if (enablePresale) {
      showMessage("Presale launch requires provisioner and presale options; use curve-only for now or set in code.", "error");
      return;
    }
    launchBtn.disabled = true;
    try {
      var factory = new ethers.Contract(FACTORY_ADDRESS, FactoryABI, signer);
      var tx = await factory.launchPowerCurveNative(args);
      showMessage("Transaction sent. Waiting for confirmation…", "");
      var receipt = await tx.wait();
      var ev = receipt.events && receipt.events.find(function (e) { return e.event === "LaunchedCurve"; });
      var token = ev && ev.args ? ev.args[1] : "(see tx logs)";
      var pool = ev && ev.args ? ev.args[2] : "(see tx logs)";
      launchResult.style.display = "block";
      launchResult.textContent = "Launched.\nToken: " + token + "\nPool: " + pool + "\nTx: " + receipt.transactionHash;
      showMessage("Curve launched.", "success");
    } catch (e) {
      showMessage(e.message || "Launch failed.", "error");
    }
    launchBtn.disabled = false;
  });

  connectBtn.onclick = connect;
})();
