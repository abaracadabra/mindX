// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// SMAIRT Presale Extension (Bonding Curve uses no presale; presale uses curve)
// - Raises native (ETH)
// - Finalize: (a) buy curve tokens for distribution, (b) buy curve tokens for LP, (c) add liquidity, (d) lock LP
// - Supports Uniswap V2 provisioner and ships V3/V4 mode parameters + hard-off stubs.

import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { Address } from "@openzeppelin/contracts/utils/Address.sol";

import { LiquidityLocker } from "../liquidity/LiquidityLocker.sol";
import { ILiquidityProvisioner } from "../liquidity/ILiquidityProvisioner.sol";

interface IBondingCurvePoolNative {
    function buy(uint256 minTokensOut, address to) external payable returns (uint256 tokensOut);
}

/// @notice Protocol extension. Does not modify curve, only interacts with it.
/// @dev SMAIRT presale: raises ETH, then uses bonding curve to buy tokens for sale + LP.
contract BondingCurvePresaleSMAIRT is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    using Address for address payable;

    // 1:Initialized, 2:Active, 3:Canceled, 4:Finalized, 5:Failed
    uint8 public state;

    IBondingCurvePoolNative public immutable curvePool;
    IERC20 public immutable curveToken;

    ILiquidityProvisioner public immutable provisioner; // swappable module at deployment
    ILiquidityProvisioner.LiquidityRequest public liquidityRequestTemplate;

    LiquidityLocker public locker;
    address public lpTokenAddress; // v2 pair address

    struct PresaleOptions {
        uint256 hardCapNative;
        uint256 softCapNative;

        uint256 maxContributionPerUserNative;
        uint256 minContributionPerUserNative;

        uint112 startTime;
        uint112 endTime;

        // Native allocations (sum <= 10_000)
        // Presale mode
        bool useLiquidityFreePresale; // If true, presale runs without initial liquidity

        // Team allocation options (can use both)
        bool useTeamAllocationFromFunds;     // Allocate team tokens from raised funds
        bool useTeamAllocationFromSupply;    // Allocate team tokens from token supply
        uint32 teamAllocationFromFundsBps;    // BPS of raised funds to use for team tokens
        uint32 teamAllocationFromSupplyBps;  // BPS of total token supply to allocate to team
        address payable teamWallet;          // Team wallet for token allocation

        uint32 nativeForLiquidityBps;

        uint32 presaleNativeForMarketingBps;
        uint32 presaleNativeForDevBps;
        uint32 presaleNativeForDaoBps;

        address payable presaleMarketingWallet;
        address payable presaleDevWallet;
        address payable presaleDaoWallet;

        // LP lock
        uint256 liquidityLockDurationDays; // 0 = no lock
        address payable liquidityBeneficiaryAddress;

        // Curve slippage guards
        uint256 minTokensForLiquidity; // min tokens from curve buy used for LP
        uint256 minTokensForSale;      // min tokens from curve buy used for sale
    }

    PresaleOptions public options;

    uint256 public nativeRaised;
    mapping(address => uint256) public contributions;

    uint256 public tokensBoughtForSale;
    mapping(address => bool) public claimed;

    event Purchased(address indexed buyer, uint256 amount, uint256 newTotal);
    event Finalized(uint256 nativeRaised, uint256 tokensBoughtForSale, address lpTokenAddress);
    event Canceled();
    event Refunded(address indexed user, uint256 amount);
    event TokensClaimed(address indexed user, uint256 amount);
    event LiquidityAdded(address lpTokenOrPosition, uint256 liquidityId);
    event LiquidityLocked(address locker, address lpToken, address beneficiary, uint256 amountLP, uint256 releaseTime);
    event TeamAllocatedFromFunds(address indexed teamWallet, uint256 ethAmount, uint256 tokensAmount);
    event TeamAllocatedFromSupply(address indexed teamWallet, uint256 tokensAmount);
    event LiquidityFreePresaleMode(bool enabled);


    error InvalidState(uint8 have, uint8 need);
    error PresaleNotActive();
    error PresalePeriodInvalid();
    error ContributionTooSmall();
    error ContributionTooLarge();
    error HardCapExceeded();
    error SoftCapNotMet();
    error NotRefundable();
    error NothingToRefund();
    error NothingToClaim();
    error AlreadyClaimed();
    error InvalidBps();
    error ZeroAddress();
    error ProvisionerDisabled();
    error UnexpectedMode();

    modifier inState(uint8 need) {
        if (state != need) revert InvalidState(state, need);
        _;
    }

    constructor(
        address curvePool_,
        address curveToken_,
        address provisioner_,
        PresaleOptions memory opts,
        ILiquidityProvisioner.LiquidityRequest memory liqTemplate,
        address owner_
    ) Ownable(owner_) {
        if (curvePool_ == address(0) || curveToken_ == address(0) || provisioner_ == address(0)) revert ZeroAddress();
        _validate(opts);

        curvePool = IBondingCurvePoolNative(curvePool_);
        curveToken = IERC20(curveToken_);
        provisioner = ILiquidityProvisioner(provisioner_);

        // Template includes DEX params + enabled flag + mode.
        liquidityRequestTemplate = liqTemplate;
        if (!liqTemplate.enabled) revert ProvisionerDisabled();

        options = opts;
        state = 1;

        if (opts.liquidityLockDurationDays > 0) {
            locker = new LiquidityLocker(address(this));
        }

        if (block.timestamp >= opts.startTime && opts.startTime != 0) {
            state = 2;
        }
    }

    receive() external payable { buy(); }

    function activate() external onlyOwner inState(1) {
        if (block.timestamp < options.startTime) revert PresalePeriodInvalid();
        state = 2;
    }

    function buy() public payable nonReentrant {
        if (state != 2) revert PresaleNotActive();
        if (block.timestamp < options.startTime || block.timestamp > options.endTime) revert PresalePeriodInvalid();

        uint256 amount = msg.value;
        if (amount < options.minContributionPerUserNative) revert ContributionTooSmall();
        if (contributions[msg.sender] + amount > options.maxContributionPerUserNative) revert ContributionTooLarge();
        if (nativeRaised + amount > options.hardCapNative) revert HardCapExceeded();

        nativeRaised += amount;
        contributions[msg.sender] += amount;

        emit Purchased(msg.sender, amount, nativeRaised);
    }

    function cancel() external onlyOwner nonReentrant {
        if (state != 1 && state != 2) revert InvalidState(state, 1);
        state = 3;
        emit Canceled();
    }

    function refund() external nonReentrant {
        if (state != 3 && state != 5) revert NotRefundable();
        uint256 amt = contributions[msg.sender];
        if (amt == 0) revert NothingToRefund();
        contributions[msg.sender] = 0;
        payable(msg.sender).sendValue(amt);
        emit Refunded(msg.sender, amt);
    }

    /// @notice Finalize:
    /// - Requires softcap met and end/hardcap reached.
    /// - Uses ETH splits:
    ///   * Liquidity ETH allocation is split in half:
    ///     - half stays as ETH to pair on DEX
    ///     - half buys curve tokens for pairing
    ///   * Remaining ETH (after marketing/dev/dao + liquidity allocation) buys curve tokens for sale distribution
    function finalize() external onlyOwner nonReentrant inState(2) {
        if (nativeRaised < options.softCapNative) {
            if (block.timestamp > options.endTime) {
                state = 5;
                revert SoftCapNotMet();
            }
            revert SoftCapNotMet();
        }

        bool hardCapReached = nativeRaised >= options.hardCapNative;
        bool ended = block.timestamp >= options.endTime;
        if (!hardCapReached && !ended) revert PresalePeriodInvalid();

        state = 4;

        uint256 ethForLiquidityTotal = (nativeRaised * options.nativeForLiquidityBps) / 10_000;
        uint256 ethForMkt = (nativeRaised * options.presaleNativeForMarketingBps) / 10_000;
        uint256 ethForDev = (nativeRaised * options.presaleNativeForDevBps) / 10_000;
        uint256 ethForDao = (nativeRaised * options.presaleNativeForDaoBps) / 10_000;

        uint256 allocated = ethForLiquidityTotal + ethForMkt + ethForDev + ethForDao;
        require(allocated <= nativeRaised, "alloc>raised");
        uint256 ethForSaleBuy = nativeRaised - allocated;

        // Liquidity split
        uint256 ethForRouter = ethForLiquidityTotal / 2;
        uint256 ethForCurveBuyLP = ethForLiquidityTotal - ethForRouter;

        // Buy tokens for LP
        uint256 tokenLP = 0;
        if (ethForCurveBuyLP > 0) {
            tokenLP = curvePool.buy{value: ethForCurveBuyLP}(options.minTokensForLiquidity, address(this));
        }

        // Buy tokens for distribution
        uint256 tokenSale = 0;
        if (ethForSaleBuy > 0) {
            tokenSale = curvePool.buy{value: ethForSaleBuy}(options.minTokensForSale, address(this));
        }
        tokensBoughtForSale = tokenSale;

        // Add liquidity (only if enabled and in V2 mode today)
        if (!options.useLiquidityFreePresale && ethForRouter > 0 && tokenLP > 0) {
            // template -> concrete request
            ILiquidityProvisioner.LiquidityRequest memory r = liquidityRequestTemplate;
            r.token = address(curveToken);
            r.tokenAmount = tokenLP;
            r.nativeAmount = ethForRouter;
            r.recipient = address(this);
            r.deadline = block.timestamp + 300;

            // fund tokens to provisioner (pull-based)
            curveToken.safeIncreaseAllowance(address(provisioner), tokenLP);

            (address lpOrPos, uint256 liqId) = provisioner.addLiquidity{value: ethForRouter}(r);
            emit LiquidityAdded(lpOrPos, liqId);

            // In V2 mode we expect lpOrPos to be the pair address
            if (r.mode != ILiquidityProvisioner.DexMode.V2) revert UnexpectedMode();
            lpTokenAddress = lpOrPos;

            // lock or transfer LP
            uint256 lpBal = IERC20(lpTokenAddress).balanceOf(address(this));
            address beneficiary = options.liquidityBeneficiaryAddress == address(0) ? owner() : options.liquidityBeneficiaryAddress;

            if (address(locker) != address(0) && options.liquidityLockDurationDays > 0) {
                IERC20(lpTokenAddress).safeTransfer(address(locker), lpBal);
                locker.lockLP(IERC20(lpTokenAddress), lpBal, beneficiary, options.liquidityLockDurationDays);
                emit LiquidityLocked(address(locker), lpTokenAddress, beneficiary, lpBal, block.timestamp + (options.liquidityLockDurationDays * 1 days));
                locker.transferOwnership(owner());
            } else {
                IERC20(lpTokenAddress).safeTransfer(beneficiary, lpBal);
            }
        }

        
        // Team allocation from raised funds (if enabled)
        uint256 teamTokensFromFunds = 0;
        if (options.useTeamAllocationFromFunds && options.teamAllocationFromFundsBps > 0 && options.teamWallet != address(0)) {
            uint256 ethForTeam = (nativeRaised * options.teamAllocationFromFundsBps) / 10_000;
            if (ethForTeam > 0 && ethForTeam <= address(this).balance) {
                teamTokensFromFunds = curvePool.buy{value: ethForTeam}(0, address(this));
                if (teamTokensFromFunds > 0) {
                    curveToken.safeTransfer(options.teamWallet, teamTokensFromFunds);
                    emit TeamAllocatedFromFunds(options.teamWallet, ethForTeam, teamTokensFromFunds);
                }
            }
        }

        // Team allocation from token supply (if enabled)
        if (options.useTeamAllocationFromSupply && options.teamAllocationFromSupplyBps > 0 && options.teamWallet != address(0)) {
            uint256 totalSupply = curveToken.totalSupply();
            uint256 teamTokensFromSupply = (totalSupply * options.teamAllocationFromSupplyBps) / 10_000;
            if (teamTokensFromSupply > 0) {
                // Mint tokens directly to team (requires token to support minting)
                // Note: This assumes the token contract has a mint function accessible by this contract
                // For CurveToken, we'd need to modify it or use a different approach
                // For now, we'll buy tokens from the curve using a small amount of ETH
                // This is a workaround - in production, you'd want proper minting capability
                uint256 ethForTeamSupply = (nativeRaised * 100) / 10_000; // Use 1% of raised as estimate
                if (ethForTeamSupply > 0 && ethForTeamSupply <= address(this).balance) {
                    uint256 tokensBought = curvePool.buy{value: ethForTeamSupply}(0, address(this));
                    if (tokensBought >= teamTokensFromSupply) {
                        curveToken.safeTransfer(options.teamWallet, teamTokensFromSupply);
                        emit TeamAllocatedFromSupply(options.teamWallet, teamTokensFromSupply);
                    }
                }
            }
        }
// Wallet payouts
        if (ethForMkt > 0) options.presaleMarketingWallet.sendValue(ethForMkt);
        if (ethForDev > 0) options.presaleDevWallet.sendValue(ethForDev);
        if (ethForDao > 0) options.presaleDaoWallet.sendValue(ethForDao);

        emit Finalized(nativeRaised, tokensBoughtForSale, lpTokenAddress);
    }

    function claim() external nonReentrant inState(4) {
        if (claimed[msg.sender]) revert AlreadyClaimed();
        uint256 c = contributions[msg.sender];
        if (c == 0) revert NothingToClaim();
        claimed[msg.sender] = true;

        uint256 amt = (c * tokensBoughtForSale) / nativeRaised;
        if (amt == 0) revert NothingToClaim();

        curveToken.safeTransfer(msg.sender, amt);
        emit TokensClaimed(msg.sender, amt);
    }

    function _validate(PresaleOptions memory o) internal pure {
        if (o.hardCapNative == 0) revert InvalidBps();
        if (o.softCapNative == 0 || o.softCapNative > o.hardCapNative) revert InvalidBps();

        if (o.minContributionPerUserNative == 0) revert InvalidBps();
        if (o.maxContributionPerUserNative < o.minContributionPerUserNative) revert InvalidBps();
        if (o.maxContributionPerUserNative > o.hardCapNative) revert InvalidBps();

        if (o.startTime == 0) revert InvalidBps();
        if (o.endTime <= o.startTime) revert InvalidBps();

        uint32 total = o.nativeForLiquidityBps + o.presaleNativeForMarketingBps + o.presaleNativeForDevBps + o.presaleNativeForDaoBps;
        if (total > 10_000) revert InvalidBps();

        if (o.presaleNativeForMarketingBps > 0 && o.presaleMarketingWallet == address(0)) revert ZeroAddress();
        if (o.presaleNativeForDevBps > 0 && o.presaleDevWallet == address(0)) revert ZeroAddress();
        if (o.presaleNativeForDaoBps > 0 && o.presaleDaoWallet == address(0)) revert ZeroAddress();

        // Liquidity beneficiary required if liquidity is enabled
        if (o.nativeForLiquidityBps > 0 && o.liquidityBeneficiaryAddress == address(0)) revert ZeroAddress();
    }
}
