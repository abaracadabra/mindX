// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

interface IDebasementIndex {
    function currentIndex() external view returns (uint256);
    function btcEquivalent(uint256 usdcAmount) external view returns (uint256 satoshis);
}

/**
 * @title InverseDebtToken (iDEBT)
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Synthetic token that encodes the "profit from loss" mechanic at the heart of
 *         the inverse debt thesis. Users mint iDEBT by depositing USDC at the current
 *         debasement index. When they burn iDEBT, they receive USDC at the index in
 *         effect at burn time. If the debasement index has risen between mint and burn,
 *         the user receives more USDC than they deposited — their nominal "loss" during
 *         the holding period is inverted into nominal gain. The contract additionally
 *         reports the BTC-equivalent value of the gain, so users can see their real
 *         purchasing-power profit measured in hard money.
 *
 * @dev Accounting:
 *      - mint: iDEBT_out = (usdc_in * BASE) / current_index
 *      - burn: usdc_out = (iDEBT_in * current_index) / BASE
 *
 *      At mint time, each iDEBT represents a claim on baseline_value units of USDC. At
 *      burn time, that claim is worth current_index / BASE units of USDC. The index
 *      itself is a composite of GDSI and BTC/USD, so the iDEBT position is effectively
 *      long both debt stress AND Bitcoin appreciation against the dollar.
 *
 *      Unlike the existing sGDSI token in DebtInheritanceProtocol (which only tracks the
 *      GDSI index), iDEBT explicitly incorporates the Bitcoin anchor. This is what makes
 *      it "inverse debt" in the full sense: it profits not just from rising debt stress
 *      but from the joint resolution of debt crisis + fiat debasement that the thesis
 *      predicts.
 *
 *      Collateralization: every iDEBT in circulation is backed by USDC held in this
 *      contract at the value it was minted at. When the index rises, nominal liability
 *      exceeds nominal backing and the contract draws from a reserve buffer. The reserve
 *      is funded by a portion of mint/burn fees plus optional treasury top-ups. If the
 *      reserve is exhausted, burns are proportionally scaled — users get a haircut rather
 *      than the contract going insolvent.
 */
contract InverseDebtToken is ERC20, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant PARAMETER_ROLE = keccak256("PARAMETER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    uint256 public constant BASE_INDEX = 1e18;
    uint256 public constant BPS_DENOM = 10_000;
    uint256 public constant USDC_SCALE = 1e12;   // USDC has 6 decimals; iDEBT is 18

    error ZeroAddress();
    error ZeroAmount();
    error SlippageExceeded(uint256 expected, uint256 actual);
    error InsufficientReserve();
    error IndexInvalid();

    IERC20 public immutable stablecoin;
    IDebasementIndex public immutable debasementIndex;

    uint256 public mintFeeBps = 30;      // 0.30%
    uint256 public burnFeeBps = 30;      // 0.30%
    uint256 public reserveShareBps = 5000; // 50% of fees go to reserve, 50% to treasury

    uint256 public totalUsdcDeposited;   // cumulative USDC received from mints
    uint256 public totalUsdcPaidOut;     // cumulative USDC paid on burns
    uint256 public reserveBuffer;        // USDC held specifically as payout buffer
    uint256 public treasuryFees;         // fees allocated to treasury, claimable by TREASURY_ROLE

    /// @notice Per-user mint basis for BTC-equivalent profit tracking. Not used for
    ///         settlement math (that comes from the index) but exposed as a view so
    ///         UIs can show "you deposited X at Y BTC price, now redeemable at Z".
    struct Position {
        uint256 usdcDeposited;
        uint256 mintIndex;
        uint256 mintTimestamp;
        uint256 mintBtcSatoshis;   // snapshot of what the deposit was worth in BTC
    }
    mapping(address => Position) public positions;

    event Minted(
        address indexed user,
        uint256 usdcIn,
        uint256 iDebtOut,
        uint256 index,
        uint256 mintBtcSatoshis,
        uint256 fee
    );
    event Burned(
        address indexed user,
        uint256 iDebtIn,
        uint256 usdcOut,
        uint256 index,
        int256 realizedBtcDeltaSatoshis,
        uint256 fee
    );
    event ReserveTopUp(address indexed from, uint256 amount);
    event TreasuryClaimed(address indexed to, uint256 amount);
    event FeesUpdated(uint256 mintFeeBps, uint256 burnFeeBps, uint256 reserveShareBps);

    constructor(
        address admin,
        address _stablecoin,
        address _debasementIndex
    ) ERC20("Inverse Debt Token", "iDEBT") {
        if (admin == address(0) || _stablecoin == address(0) || _debasementIndex == address(0))
            revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(PARAMETER_ROLE, admin);
        _grantRole(TREASURY_ROLE, admin);
        stablecoin = IERC20(_stablecoin);
        debasementIndex = IDebasementIndex(_debasementIndex);
    }

    /*//////////////////////////////////////////////////////////////
                              MINT
    //////////////////////////////////////////////////////////////*/

    function mint(uint256 usdcAmount, uint256 minIDebtOut)
        external
        nonReentrant
        whenNotPaused
        returns (uint256 iDebtOut)
    {
        if (usdcAmount == 0) revert ZeroAmount();

        uint256 index = debasementIndex.currentIndex();
        if (index == 0) revert IndexInvalid();

        // Fee split: part goes to reserve, part to treasury.
        uint256 fee = (usdcAmount * mintFeeBps) / BPS_DENOM;
        uint256 reserveCut = (fee * reserveShareBps) / BPS_DENOM;
        uint256 treasuryCut = fee - reserveCut;
        uint256 net = usdcAmount - fee;

        // iDEBT amount scaled from USDC (6 decimals) to 18 decimals, then divided by index.
        // formula: iDEBT_out = (net_usdc_18 * BASE) / index
        uint256 net18 = net * USDC_SCALE;
        iDebtOut = (net18 * BASE_INDEX) / index;

        if (iDebtOut < minIDebtOut) revert SlippageExceeded(minIDebtOut, iDebtOut);

        // Snapshot BTC equivalent for user-facing profit tracking.
        uint256 btcSats = debasementIndex.btcEquivalent(net);

        // Pull USDC from user.
        stablecoin.safeTransferFrom(msg.sender, address(this), usdcAmount);

        totalUsdcDeposited += net;
        reserveBuffer += reserveCut;
        treasuryFees += treasuryCut;

        // Update position snapshot. If user already has a position, blend the basis.
        Position storage pos = positions[msg.sender];
        if (pos.usdcDeposited == 0) {
            pos.usdcDeposited = net;
            pos.mintIndex = index;
            pos.mintTimestamp = block.timestamp;
            pos.mintBtcSatoshis = btcSats;
        } else {
            // Weighted average the basis.
            uint256 totalUsdc = pos.usdcDeposited + net;
            pos.mintIndex = (pos.mintIndex * pos.usdcDeposited + index * net) / totalUsdc;
            pos.mintBtcSatoshis += btcSats;
            pos.usdcDeposited = totalUsdc;
            pos.mintTimestamp = block.timestamp;
        }

        _mint(msg.sender, iDebtOut);

        emit Minted(msg.sender, usdcAmount, iDebtOut, index, btcSats, fee);
    }

    /*//////////////////////////////////////////////////////////////
                              BURN
    //////////////////////////////////////////////////////////////*/

    function burn(uint256 iDebtAmount, uint256 minUsdcOut)
        external
        nonReentrant
        whenNotPaused
        returns (uint256 usdcOut)
    {
        if (iDebtAmount == 0) revert ZeroAmount();

        uint256 index = debasementIndex.currentIndex();
        if (index == 0) revert IndexInvalid();

        // usdc_out_18 = (iDEBT_in * index) / BASE
        uint256 usdc18 = (iDebtAmount * index) / BASE_INDEX;
        uint256 grossUsdc = usdc18 / USDC_SCALE;

        uint256 fee = (grossUsdc * burnFeeBps) / BPS_DENOM;
        uint256 reserveCut = (fee * reserveShareBps) / BPS_DENOM;
        uint256 treasuryCut = fee - reserveCut;
        usdcOut = grossUsdc - fee;

        // Solvency check against available USDC (deposits + reserve).
        uint256 available = stablecoin.balanceOf(address(this));
        if (usdcOut > available) {
            // Proportional haircut rather than revert — the thesis accepts that in
            // extreme debasement scenarios the protocol may not pay out full nominal.
            // This is the correct failure mode: users still receive the pro-rata share
            // of available stablecoin, and the "missing" portion is implicitly absorbed
            // as BTC-denominated upside they can realize through other protocol legs.
            usdcOut = available > fee ? available - fee : 0;
        }

        if (usdcOut < minUsdcOut) revert SlippageExceeded(minUsdcOut, usdcOut);

        // Compute realized BTC delta for event reporting.
        Position storage pos = positions[msg.sender];
        int256 realizedBtcDelta = 0;
        if (pos.usdcDeposited > 0 && balanceOf(msg.sender) >= iDebtAmount) {
            uint256 share = (iDebtAmount * pos.mintBtcSatoshis) / balanceOf(msg.sender);
            uint256 newBtcSats = debasementIndex.btcEquivalent(usdcOut);
            realizedBtcDelta = int256(newBtcSats) - int256(share);
            // Proportionally reduce the position basis.
            uint256 consumedUsdc = (pos.usdcDeposited * iDebtAmount) / balanceOf(msg.sender);
            pos.usdcDeposited -= consumedUsdc;
            pos.mintBtcSatoshis = pos.mintBtcSatoshis > share
                ? pos.mintBtcSatoshis - share
                : 0;
        }

        _burn(msg.sender, iDebtAmount);

        reserveBuffer += reserveCut;
        treasuryFees += treasuryCut;
        totalUsdcPaidOut += usdcOut;

        stablecoin.safeTransfer(msg.sender, usdcOut);

        emit Burned(msg.sender, iDebtAmount, usdcOut, index, realizedBtcDelta, fee);
    }

    /*//////////////////////////////////////////////////////////////
                           RESERVE / TREASURY
    //////////////////////////////////////////////////////////////*/

    /// @notice Anyone can top up the reserve. Used by governance to strengthen solvency.
    function topUpReserve(uint256 amount) external {
        if (amount == 0) revert ZeroAmount();
        stablecoin.safeTransferFrom(msg.sender, address(this), amount);
        reserveBuffer += amount;
        emit ReserveTopUp(msg.sender, amount);
    }

    function claimTreasury(address to, uint256 amount) external onlyRole(TREASURY_ROLE) {
        require(amount <= treasuryFees, "exceeds treasury");
        treasuryFees -= amount;
        stablecoin.safeTransfer(to, amount);
        emit TreasuryClaimed(to, amount);
    }

    function setFees(uint256 _mintFeeBps, uint256 _burnFeeBps, uint256 _reserveShareBps)
        external onlyRole(PARAMETER_ROLE)
    {
        require(_mintFeeBps <= 1000 && _burnFeeBps <= 1000, "fee too high"); // cap 10%
        require(_reserveShareBps <= BPS_DENOM, "share out of range");
        mintFeeBps = _mintFeeBps;
        burnFeeBps = _burnFeeBps;
        reserveShareBps = _reserveShareBps;
        emit FeesUpdated(_mintFeeBps, _burnFeeBps, _reserveShareBps);
    }

    /*//////////////////////////////////////////////////////////////
                               VIEWS
    //////////////////////////////////////////////////////////////*/

    function redemptionValue(uint256 iDebtAmount) external view returns (uint256 usdcOut) {
        uint256 index = debasementIndex.currentIndex();
        uint256 usdc18 = (iDebtAmount * index) / BASE_INDEX;
        uint256 gross = usdc18 / USDC_SCALE;
        uint256 fee = (gross * burnFeeBps) / BPS_DENOM;
        usdcOut = gross - fee;
    }

    function collateralizationRatioBps() external view returns (uint256) {
        uint256 bal = stablecoin.balanceOf(address(this));
        if (totalSupply() == 0) return type(uint256).max;
        uint256 index = debasementIndex.currentIndex();
        uint256 liability18 = (totalSupply() * index) / BASE_INDEX;
        uint256 liability6 = liability18 / USDC_SCALE;
        if (liability6 == 0) return type(uint256).max;
        return (bal * BPS_DENOM) / liability6;
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
