// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title RebaseToken - Parameterized Rebase Token with Auto-Rebase Mechanics
/// @notice Configurable rebase token based on DeltaV THRUST design
/// @dev Default name: "REB ACE", default symbol: "REBACE"
/// @dev Uses gons/fragments system for rebase mechanics
contract RebaseToken is ERC20, Ownable, ReentrancyGuard {
    // ============ REBASE MECHANICS ============
    uint256 private constant MAX_UINT256 = type(uint256).max;
    uint256 private constant MAX_SUPPLY = type(uint128).max;
    
    uint256 private _totalSupply;
    uint256 private _gonsPerFragment;
    uint256 private gonSwapThreshold;
    
    // Configurable initial supply (default: 22222222 * 10^18)
    uint256 public immutable INITIAL_FRAGMENTS_SUPPLY;
    uint256 private immutable TOTAL_GONS;
    
    // ============ CONFIGURABLE PARAMETERS ============
    bool public initialDistributionFinished = true;
    bool public swapEnabled = true;
    bool public autoRebase = true;
    bool public feesOnNormalTransfers = false;
    bool public isLiquidityInBnb = true;
    
    // Rebase parameters (defaults from DeltaV)
    uint256 public rebaseFrequency = 120; // seconds between rebases
    uint256 public rewardYield = 1543701; // rebase yield
    uint256 public rewardYieldDenominator = 1 * 10**11;
    uint256 private constant MAX_REBASE_FREQUENCY = 3600;
    
    // Fee parameters (defaults from DeltaV)
    uint256 public liquidityFee = 33;      // 3.3% (basis points / 10)
    uint256 public treasuryFee = 45;       // 4.5% (basis points / 10)
    uint256 public burnFee = 11;           // 1.1% (basis points / 10)
    uint256 public buyFeeRFV = 22;        // 2.2% (basis points / 10)
    uint256 public sellFeeTreasuryAdded = 66;  // 6.6% (basis points / 10)
    uint256 public sellFeeRFVAdded = 45;       // 4.5% (basis points / 10)
    uint256 public feeDenominator = 1000;
    uint256 public totalBuyFee;
    uint256 public totalSellFee;
    
    // Max transaction limits
    uint256 public maxSellTransactionAmount;
    uint256 public maxBuyTransactionAmount;
    
    // Addresses
    address public liquidityReceiver;
    address public treasuryReceiver;
    address public riskFreeValueReceiver;
    address public router;
    address public pair;
    address public busdToken;
    address public immutable WETH;
    
    // State
    uint256 private DeltaCounter = 0;
    uint256 internal inception;
    uint256 internal DeltaT;
    uint256 internal TotalRewards;
    uint256 private epoch;
    uint256 targetLiquidity = 33;
    uint256 targetLiquidityDenominator = 100;
    
    bool inSwap;
    
    // Exemptions
    mapping(address => bool) public _isFeeExempt;
    mapping(address => bool) public automatedMarketMakerPairs;
    address[] public _markerPairs;
    
    // Gons balances
    mapping(address => uint256) private _gonBalances;
    mapping(address => mapping(address => uint256)) private _allowedFragments;
    
    address constant DEAD = 0x000000000000000000000000000000000000dEaD;
    address constant ZERO = 0x0000000000000000000000000000000000000000;
    
    // ============ EVENTS ============
    event LogRebase(uint256 indexed epoch, uint256 totalSupply);
    event SwapBack(uint256 contractTokenBalance, uint256 amountToLiquify, uint256 amountToRFV, uint256 amountToTreasury);
    event SwapAndLiquify(uint256 tokensSwapped, uint256 bnbReceived, uint256 tokensIntoLiqudity);
    event SetAutomatedMarketMakerPair(address indexed pair, bool indexed value);
    
    // ============ MODIFIERS ============
    modifier swapping() {
        inSwap = true;
        _;
        inSwap = false;
    }
    
    modifier validRecipient(address to) {
        require(to != address(0), "Invalid recipient");
        _;
    }
    
    // ============ CONSTRUCTOR ============
    /// @param _name Token name (default: "REB ACE")
    /// @param _symbol Token symbol (default: "REBACE")
    /// @param _initialSupply Initial supply (default: 22222222 * 10^18)
    /// @param _liquidityFee Liquidity fee (default: 33 = 3.3%)
    /// @param _treasuryFee Treasury fee (default: 45 = 4.5%)
    /// @param _burnFee Burn fee (default: 11 = 1.1%)
    /// @param _buyFeeRFV Buy RFV fee (default: 22 = 2.2%)
    /// @param _sellFeeTreasuryAdded Additional sell treasury fee (default: 66 = 6.6%)
    /// @param _sellFeeRFVAdded Additional sell RFV fee (default: 45 = 4.5%)
    /// @param _liquidityReceiver Liquidity receiver address
    /// @param _treasuryReceiver Treasury receiver address
    /// @param _riskFreeValueReceiver RFV receiver address
    /// @param _router Router address
    /// @param _weth WETH address
    /// @param _busdToken BUSD token address (optional, can be address(0))
    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _initialSupply,
        uint256 _liquidityFee,
        uint256 _treasuryFee,
        uint256 _burnFee,
        uint256 _buyFeeRFV,
        uint256 _sellFeeTreasuryAdded,
        uint256 _sellFeeRFVAdded,
        address _liquidityReceiver,
        address _treasuryReceiver,
        address _riskFreeValueReceiver,
        address _router,
        address _weth,
        address _busdToken
    ) ERC20(_name, _symbol) Ownable(msg.sender) {
        require(_initialSupply > 0, "Invalid initial supply");
        require(_liquidityReceiver != address(0), "Invalid liquidity receiver");
        require(_treasuryReceiver != address(0), "Invalid treasury receiver");
        require(_riskFreeValueReceiver != address(0), "Invalid RFV receiver");
        require(_router != address(0), "Invalid router");
        require(_weth != address(0), "Invalid WETH");
        
        INITIAL_FRAGMENTS_SUPPLY = _initialSupply;
        TOTAL_GONS = MAX_UINT256 - (MAX_UINT256 % INITIAL_FRAGMENTS_SUPPLY);
        
        // Set fees
        liquidityFee = _liquidityFee;
        treasuryFee = _treasuryFee;
        burnFee = _burnFee;
        buyFeeRFV = _buyFeeRFV;
        sellFeeTreasuryAdded = _sellFeeTreasuryAdded;
        sellFeeRFVAdded = _sellFeeRFVAdded;
        totalBuyFee = liquidityFee + treasuryFee + buyFeeRFV + burnFee;
        totalSellFee = totalBuyFee + sellFeeTreasuryAdded + sellFeeRFVAdded;
        
        // Set addresses
        liquidityReceiver = _liquidityReceiver;
        treasuryReceiver = _treasuryReceiver;
        riskFreeValueReceiver = _riskFreeValueReceiver;
        router = _router;
        WETH = _weth;
        busdToken = _busdToken;
        
        // Initialize rebase mechanics
        _totalSupply = INITIAL_FRAGMENTS_SUPPLY;
        _gonBalances[msg.sender] = TOTAL_GONS;
        _gonsPerFragment = TOTAL_GONS / _totalSupply;
        gonSwapThreshold = (TOTAL_GONS * 10) / 10000;
        
        // Initialize max transactions (default: 1% and 2% of supply)
        maxSellTransactionAmount = _totalSupply / 100;
        maxBuyTransactionAmount = _totalSupply / 50;
        
        inception = block.timestamp;
        epoch = block.timestamp;
        
        // Exemptions
        _isFeeExempt[treasuryReceiver] = true;
        _isFeeExempt[riskFreeValueReceiver] = true;
        _isFeeExempt[address(this)] = true;
        _isFeeExempt[msg.sender] = true;
        
        emit Transfer(address(0), msg.sender, _totalSupply);
    }
    
    // ============ REBASE FUNCTIONS ============
    function _rebase() private {
        if (!inSwap) {
            uint256 circulatingSupply = getCirculatingSupply();
            int256 supplyDelta = int256((circulatingSupply * rewardYield) / rewardYieldDenominator);
            coreRebase(supplyDelta);
        }
    }
    
    function coreRebase(int256 supplyDelta) private returns (uint256) {
        epoch = block.timestamp;
        if (supplyDelta == 0) {
            emit LogRebase(epoch, _totalSupply);
            return _totalSupply;
        }
        
        if (supplyDelta > 0) {
            _totalSupply = _totalSupply + uint256(supplyDelta);
        } else {
            _totalSupply = _totalSupply - uint256(-supplyDelta);
        }
        
        if (_totalSupply > MAX_SUPPLY) {
            _totalSupply = MAX_SUPPLY;
        }
        
        _gonsPerFragment = TOTAL_GONS / _totalSupply;
        emit LogRebase(epoch, _totalSupply);
        return _totalSupply;
    }
    
    function deltaV() internal returns (bool) {
        DeltaT = block.timestamp - inception;
        TotalRewards = DeltaT / rebaseFrequency;
        if (DeltaCounter <= TotalRewards) {
            DeltaCounter = DeltaCounter + 1;
            return true;
        } else {
            return false;
        }
    }
    
    function SlingShot() private view returns (bool) {
        return epoch != block.timestamp;
    }
    
    // ============ VIEW FUNCTIONS ============
    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address who) public view override returns (uint256) {
        return _gonBalances[who] / _gonsPerFragment;
    }
    
    function allowance(address owner_, address spender) public view override returns (uint256) {
        return _allowedFragments[owner_][spender];
    }
    
    function getCirculatingSupply() public view returns (uint256) {
        return (TOTAL_GONS - _gonBalances[DEAD] - _gonBalances[ZERO]) / _gonsPerFragment;
    }
    
    function shouldTakeFee(address from, address to) internal view returns (bool) {
        if (_isFeeExempt[from] || _isFeeExempt[to]) {
            return false;
        } else if (feesOnNormalTransfers) {
            return true;
        } else {
            return (automatedMarketMakerPairs[from] || automatedMarketMakerPairs[to]);
        }
    }
    
    function shouldSwapBack() public view returns (bool) {
        return !automatedMarketMakerPairs[msg.sender] && !inSwap && swapEnabled && 
               totalBuyFee + totalSellFee > 0 && _gonBalances[address(this)] >= gonSwapThreshold;
    }
    
    // ============ TRANSFER FUNCTIONS ============
    function transfer(address to, uint256 value) public override validRecipient(to) returns (bool) {
        _transferFrom(msg.sender, to, value);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 value) public override validRecipient(to) returns (bool) {
        if (_allowedFragments[from][msg.sender] != type(uint256).max) {
            _allowedFragments[from][msg.sender] = _allowedFragments[from][msg.sender] - value;
        }
        _transferFrom(from, to, value);
        return true;
    }
    
    function _basicTransfer(address from, address to, uint256 amount) internal returns (bool) {
        uint256 gonAmount = amount * _gonsPerFragment;
        _gonBalances[from] = _gonBalances[from] - gonAmount;
        _gonBalances[to] = _gonBalances[to] + gonAmount;
        emit Transfer(from, to, amount);
        return true;
    }
    
    function _transferFrom(address sender, address recipient, uint256 amount) internal returns (bool) {
        bool excludedAccount = _isFeeExempt[sender] || _isFeeExempt[recipient];
        require(initialDistributionFinished || excludedAccount, "Initial distribution not finished");
        
        if (automatedMarketMakerPairs[recipient] && !excludedAccount) {
            require(amount <= maxSellTransactionAmount, "Max sell exceeded");
        }
        if (automatedMarketMakerPairs[sender] && !excludedAccount) {
            require(amount <= maxBuyTransactionAmount, "Max buy exceeded");
        }
        
        if (deltaV() && autoRebase && SlingShot()) {
            _rebase();
        }
        
        if (inSwap) {
            return _basicTransfer(sender, recipient, amount);
        }
        
        uint256 gonAmount = amount * _gonsPerFragment;
        
        if (shouldSwapBack() && recipient != DEAD) {
            swapBack();
        }
        
        _gonBalances[sender] = _gonBalances[sender] - gonAmount;
        uint256 gonAmountReceived = shouldTakeFee(sender, recipient) ? takeFee(sender, recipient, gonAmount) : gonAmount;
        _gonBalances[recipient] = _gonBalances[recipient] + gonAmountReceived;
        
        emit Transfer(sender, recipient, gonAmountReceived / _gonsPerFragment);
        return true;
    }
    
    function takeFee(address sender, address recipient, uint256 gonAmount) internal returns (uint256) {
        uint256 _realFee = totalBuyFee;
        if (automatedMarketMakerPairs[recipient]) {
            _realFee = totalSellFee;
        }
        
        uint256 feeAmount = (gonAmount * _realFee) / feeDenominator;
        _gonBalances[address(this)] = _gonBalances[address(this)] + feeAmount;
        
        // Burn fee
        uint256 burnAmount = (gonAmount / _gonsPerFragment * burnFee) / feeDenominator;
        if (burnAmount > 0) {
            _gonBalances[DEAD] = _gonBalances[DEAD] + (burnAmount * _gonsPerFragment);
            emit Transfer(sender, DEAD, burnAmount);
        }
        
        emit Transfer(sender, address(this), feeAmount / _gonsPerFragment);
        return gonAmount - feeAmount;
    }
    
    // ============ SWAP FUNCTIONS ============
    function swapBack() internal swapping {
        uint256 realTotalFee = totalBuyFee + totalSellFee;
        uint256 dynamicLiquidityFee = isOverLiquified(targetLiquidity, targetLiquidityDenominator) ? 0 : liquidityFee;
        uint256 contractTokenBalance = _gonBalances[address(this)] / _gonsPerFragment;
        uint256 amountToLiquify = (contractTokenBalance * dynamicLiquidityFee * 2) / realTotalFee;
        uint256 amountToRFV = (contractTokenBalance * (buyFeeRFV * 2 + sellFeeRFVAdded)) / realTotalFee;
        uint256 amountToTreasury = contractTokenBalance - amountToLiquify - amountToRFV;
        
        // Note: Actual swap implementation would require router interface
        // This is a stub for bonding curve integration
        
        emit SwapBack(contractTokenBalance, amountToLiquify, amountToRFV, amountToTreasury);
    }
    
    function isOverLiquified(uint256 target, uint256 accuracy) public view returns (bool) {
        return getLiquidityBacking(accuracy) > target;
    }
    
    function getLiquidityBacking(uint256 accuracy) public view returns (uint256) {
        uint256 liquidityBalance = 0;
        for (uint i = 0; i < _markerPairs.length; i++) {
            liquidityBalance = liquidityBalance + balanceOf(_markerPairs[i]) / 1e18;
        }
        return (accuracy * liquidityBalance * 2) / (getCirculatingSupply() / 1e18);
    }
    
    // ============ ADMIN FUNCTIONS ============
    function approve(address spender, uint256 value) public override returns (bool) {
        _allowedFragments[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }
    
    function setAutomatedMarketMakerPair(address _pair, bool _value) public onlyOwner {
        require(automatedMarketMakerPairs[_pair] != _value, "Value already set");
        automatedMarketMakerPairs[_pair] = _value;
        if (_value) {
            _markerPairs.push(_pair);
        } else {
            require(_markerPairs.length > 1, "Required 1 pair");
            for (uint256 i = 0; i < _markerPairs.length; i++) {
                if (_markerPairs[i] == _pair) {
                    _markerPairs[i] = _markerPairs[_markerPairs.length - 1];
                    _markerPairs.pop();
                    break;
                }
            }
        }
        emit SetAutomatedMarketMakerPair(_pair, _value);
    }
    
    function setFees(
        uint256 _liquidityFee,
        uint256 _treasuryFee,
        uint256 _burnFee,
        uint256 _buyFeeRFV,
        uint256 _sellFeeRFVAdded,
        uint256 _sellFeeTreasuryAdded,
        uint256 _feeDenominator
    ) external onlyOwner {
        liquidityFee = _liquidityFee;
        treasuryFee = _treasuryFee;
        burnFee = _burnFee;
        buyFeeRFV = _buyFeeRFV;
        sellFeeRFVAdded = _sellFeeRFVAdded;
        sellFeeTreasuryAdded = _sellFeeTreasuryAdded;
        feeDenominator = _feeDenominator;
        totalBuyFee = liquidityFee + treasuryFee + buyFeeRFV + burnFee;
        totalSellFee = totalBuyFee + sellFeeTreasuryAdded + sellFeeRFVAdded;
    }
    
    function setAutoRebase(bool _autoRebase) external onlyOwner {
        autoRebase = _autoRebase;
    }
    
    function setRebaseFrequency(uint256 _rebaseFrequency) external onlyOwner {
        require(_rebaseFrequency <= MAX_REBASE_FREQUENCY, "Max frequency exceeded");
        rebaseFrequency = _rebaseFrequency;
    }
    
    function setRewardYield(uint256 _rewardYield, uint256 _rewardYieldDenominator) external onlyOwner {
        rewardYield = _rewardYield;
        rewardYieldDenominator = _rewardYieldDenominator;
    }
    
    function setMaxSellTransaction(uint256 _maxTxn) external onlyOwner {
        maxSellTransactionAmount = _maxTxn;
    }
    
    function setMaxBuyTransaction(uint256 _maxTxn) external onlyOwner {
        maxBuyTransactionAmount = _maxTxn;
    }
    
    function setFeeExempt(address _addr, bool _value) external onlyOwner {
        _isFeeExempt[_addr] = _value;
    }
    
    function setFeeReceivers(
        address _liquidityReceiver,
        address _treasuryReceiver,
        address _riskFreeValueReceiver
    ) external onlyOwner {
        liquidityReceiver = _liquidityReceiver;
        treasuryReceiver = _treasuryReceiver;
        riskFreeValueReceiver = _riskFreeValueReceiver;
    }
}
