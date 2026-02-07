// SPDX-License-Identifier: MIT
pragma solidity ^0.7.4;

/// @author demiurge
/// Deflationary counterpart to DAIORebaseToken: negative rebase (burn) with equivalent ratios.
/// Same fee structure and settings; supply decreases on each rebase instead of increasing.

/*
 * DAIO Deflate Token
 * Hyper-deflationary: negative rebase (burn) on the same schedule as the inflationary token.
 * BUY fee 11.1% = 3.3% liquidity, 2.3% marketing, 2.2% development, 2.2% afterburner, 1.1% burn
 * SELL fee 22.2% = +3.3% marketing, +3.3% development, +4.5% afterburner = 11.1%
 * Rebase reduces total supply (burn) at equivalent rate; supply floor prevents zero.
 */

library SafeMathIntDeflate {
    int256 private constant MIN_INT256 = int256(1) << 255;
    int256 private constant MAX_INT256 = ~(int256(1) << 255);
    function mul(int256 a, int256 b) internal pure returns (int256) {
        int256 c = a * b;
        require(c != MIN_INT256 || (a & MIN_INT256) != (b & MIN_INT256));
        require((b == 0) || (c / b == a));
        return c;
    }
    function div(int256 a, int256 b) internal pure returns (int256) {
        require(b != -1 || a != MIN_INT256);
        return a / b;
    }
    function sub(int256 a, int256 b) internal pure returns (int256) {
        int256 c = a - b;
        require((b >= 0 && c <= a) || (b < 0 && c > a));
        return c;
    }
    function add(int256 a, int256 b) internal pure returns (int256) {
        int256 c = a + b;
        require((b >= 0 && c >= a) || (b < 0 && c < a));
        return c;
    }
    function abs(int256 a) internal pure returns (int256) {
        require(a != MIN_INT256);
        return a < 0 ? -a : a;
    }
}

interface IERC20Deflate {
    function totalSupply() external view returns (uint256);
    function balanceOf(address who) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    function approve(address spender, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

library SafeMathDeflate {
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a, "SafeMath: addition overflow");
        return c;
    }
    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        return sub(a, b, "SafeMath: subtraction overflow");
    }
    function sub(uint256 a, uint256 b, string memory errorMessage) internal pure returns (uint256) {
        require(b <= a, errorMessage);
        return a - b;
    }
    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a == 0) return 0;
        uint256 c = a * b;
        require(c / a == b, "SafeMath: multiplication overflow");
        return c;
    }
    function div(uint256 a, uint256 b) internal pure returns (uint256) {
        return div(a, b, "SafeMath: division by zero");
    }
    function div(uint256 a, uint256 b, string memory errorMessage) internal pure returns (uint256) {
        require(b > 0, errorMessage);
        return a / b;
    }
    function mod(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b != 0);
        return a % b;
    }
}

interface InterfaceLPDeflate {
    function sync() external;
}

abstract contract ERC20DetailedDeflate is IERC20Deflate {
    string private _name;
    string private _symbol;
    uint8 private _decimals;
    constructor(string memory _tokenName, string memory _tokenSymbol, uint8 _tokenDecimals) {
        _name = _tokenName;
        _symbol = _tokenSymbol;
        _decimals = _tokenDecimals;
    }
    function name() public view returns (string memory) { return _name; }
    function symbol() public view returns (string memory) { return _symbol; }
    function decimals() public view returns (uint8) { return _decimals; }
}

interface IDEXRouterDeflate {
    function factory() external pure returns (address);
    function WETH() external pure returns (address);
    function addLiquidity(address tokenA, address tokenB, uint256 amountADesired, uint256 amountBDesired, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)
        external returns (uint256 amountA, uint256 amountB, uint256 liquidity);
    function addLiquidityETH(address token, uint256 amountTokenDesired, uint256 amountTokenMin, uint256 amountETHMin, address to, uint256 deadline)
        external payable returns (uint256 amountToken, uint256 amountETH, uint256 liquidity);
    function swapExactTokensForTokensSupportingFeeOnTransferTokens(uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to, uint256 deadline) external;
    function swapExactETHForTokensSupportingFeeOnTransferTokens(uint256 amountOutMin, address[] calldata path, address to, uint256 deadline) external payable;
    function swapExactTokensForETHSupportingFeeOnTransferTokens(uint256 amountIn, uint256 amountOutMin, address[] calldata path, address to, uint256 deadline) external;
}

interface IDEXFactoryDeflate {
    function createPair(address tokenA, address tokenB) external returns (address pair);
}

contract OwnableDeflate {
    address private _owner;
    event OwnershipRenounced(address indexed previousOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    constructor() { _owner = msg.sender; }
    function owner() public view returns (address) { return _owner; }
    modifier onlyOwner() {
        require(msg.sender == _owner, "Not owner");
        _;
    }
    function renounceOwnership() public onlyOwner {
        emit OwnershipRenounced(_owner);
        _owner = address(0);
    }
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0));
        emit OwnershipTransferred(_owner, newOwner);
        _owner = newOwner;
    }
}

/// @title DAIODeflateToken
/// @notice DAIO deflationary rebase token: supply decreases (burn) on each rebase. Same ratios as DAIORebaseToken.
contract DAIODeflateToken is ERC20DetailedDeflate, OwnableDeflate {
    using SafeMathDeflate for uint256;
    using SafeMathIntDeflate for int256;

    bool public initialDistributionFinished = true;
    bool public swapEnabled = true;
    bool public autoRebase = true;
    bool public feesOnNormalTransfers = false;
    bool public isLiquidityInBnb = true;

    uint256 public rebaseFrequency = 120;
    uint256 public rewardYield = 1543701;
    uint256 public rewardYieldDenominator = 1 * 10**11;

    uint256 private deflateCounter = 0;
    uint256 internal inception = block.timestamp;
    uint256 internal deltaT = block.timestamp - inception;
    uint256 internal totalRewards = deltaT % rebaseFrequency;
    uint256 private epoch = deflateCounter;

    uint256 public maxSellTransactionAmount = 11 * 10**21;
    uint256 public maxBuyTransactionAmount = 22 * 10**21;

    mapping(address => bool) _isFeeExempt;
    address[] public _markerPairs;
    mapping (address => bool) public automatedMarketMakerPairs;

    uint256 public constant MAX_FEE_RATE = 23;
    uint256 private constant MAX_REBASE_FREQUENCY = 3600;
    uint256 private constant DECIMALS = 18;
    uint256 private constant MAX_UINT256 = ~uint256(0);
    uint256 private constant INITIAL_FRAGMENTS_SUPPLY = 22222222 * 10**DECIMALS;
    uint256 private constant TOTAL_GONS = MAX_UINT256 - (MAX_UINT256 % INITIAL_FRAGMENTS_SUPPLY);
    uint256 private constant MIN_SUPPLY = 1 * 10**DECIMALS;

    address DEAD = 0x000000000000000000000000000000000000dEaD;
    address ZERO = 0x0000000000000000000000000000000000000000;

    address public liquidityReceiver = 0xC75B704446D36d296C7138df969b4C1ba54D7326;
    address public treasuryReceiver = 0xa54B66632CFe3aD5C1520cB9a01666f0d76C79d4;
    address public riskFreeValueReceiver = 0xC75B704446D36d296C7138df969b4C1ba54D7326;
    address public busdToken = 0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56;

    IDEXRouterDeflate public router;
    address public pair;

    uint256 public liquidityFee = 33;
    uint256 public treasuryFee = 45;
    uint256 public burnFee = 11;
    uint256 public buyFeeRFV = 22;
    uint256 public sellFeeTreasuryAdded = 66;
    uint256 public sellFeeRFVAdded = 45;
    uint256 public totalBuyFee = liquidityFee.add(treasuryFee).add(buyFeeRFV).add(burnFee);
    uint256 public totalSellFee = totalBuyFee.add(sellFeeTreasuryAdded).add(sellFeeRFVAdded);
    uint256 public feeDenominator = 1000;
    uint256 targetLiquidity = 33;
    uint256 targetLiquidityDenominator = 100;

    bool inSwap;
    modifier swapping() {
        inSwap = true;
        _;
        inSwap = false;
    }
    modifier validRecipient(address to) {
        require(to != address(0x0));
        _;
    }

    uint256 private _totalSupply;
    uint256 private _gonsPerFragment;
    uint256 private gonSwapThreshold = (TOTAL_GONS * 10) / 10000;
    mapping(address => uint256) private _gonBalances;
    mapping(address => mapping(address => uint256)) private _allowedFragments;

    constructor() ERC20DetailedDeflate("DAIO", "DEFLATE", uint8(DECIMALS)) {
        router = IDEXRouterDeflate(0x10ED43C718714eb63d5aA57B78B54704E256024E);
        pair = IDEXFactoryDeflate(router.factory()).createPair(address(this), router.WETH());
        address pairBusd = IDEXFactoryDeflate(router.factory()).createPair(address(this), busdToken);
        _allowedFragments[address(this)][address(router)] = uint256(-1);
        _allowedFragments[address(this)][pair] = uint256(-1);
        _allowedFragments[address(this)][address(this)] = uint256(-1);
        _allowedFragments[address(this)][pairBusd] = uint256(-1);
        setAutomatedMarketMakerPair(pair, true);
        setAutomatedMarketMakerPair(pairBusd, true);
        _totalSupply = INITIAL_FRAGMENTS_SUPPLY;
        _gonBalances[msg.sender] = TOTAL_GONS;
        _gonsPerFragment = TOTAL_GONS.div(_totalSupply);
        _isFeeExempt[treasuryReceiver] = true;
        _isFeeExempt[riskFreeValueReceiver] = true;
        _isFeeExempt[address(this)] = true;
        _isFeeExempt[msg.sender] = true;
        IERC20Deflate(busdToken).approve(address(router), uint256(-1));
        IERC20Deflate(busdToken).approve(address(pairBusd), uint256(-1));
        IERC20Deflate(busdToken).approve(address(this), uint256(-1));
        emit Transfer(address(0x0), msg.sender, _totalSupply);
    }

    receive() external payable {}

    function totalSupply() external view override returns (uint256) { return _totalSupply; }
    function allowance(address owner_, address spender) external view override returns (uint256) {
        return _allowedFragments[owner_][spender];
    }

    function balanceOf(address who) public view override returns (uint256) {
        return _gonBalances[who].div(_gonsPerFragment);
    }

    function checkFeeExempt(address _addr) external view returns (bool) { return _isFeeExempt[_addr]; }
    function checkSwapThreshold() external view returns (uint256) { return gonSwapThreshold.div(_gonsPerFragment); }

    function shouldTakeFee(address from, address to) internal view returns (bool) {
        if (_isFeeExempt[from] || _isFeeExempt[to]) return false;
        if (feesOnNormalTransfers) return true;
        return (automatedMarketMakerPairs[from] || automatedMarketMakerPairs[to]);
    }

    function shouldSwapBack() public view returns (bool) {
        return !automatedMarketMakerPairs[msg.sender] && !inSwap && swapEnabled && totalBuyFee.add(totalSellFee) > 0 && _gonBalances[address(this)] >= gonSwapThreshold;
    }

    function getCirculatingSupply() public view returns (uint256) {
        return (TOTAL_GONS.sub(_gonBalances[DEAD]).sub(_gonBalances[ZERO])).div(_gonsPerFragment);
    }

    function getLiquidityBacking(uint256 accuracy) public view returns (uint256) {
        uint256 liquidityBalance = 0;
        for (uint i = 0; i < _markerPairs.length; i++) {
            liquidityBalance.add(balanceOf(_markerPairs[i]).div(10 ** 18));
        }
        return accuracy.mul(liquidityBalance.mul(2)).div(getCirculatingSupply().div(10 ** 18));
    }

    function isOverLiquified(uint256 target, uint256 accuracy) public view returns (bool) {
        return getLiquidityBacking(accuracy) > target;
    }

    function manualSync() public {
        for (uint i = 0; i < _markerPairs.length; i++) {
            InterfaceLPDeflate(_markerPairs[i]).sync();
        }
    }

    function shouldDeflate() private view returns (bool) {
        return epoch != block.timestamp;
    }

    /// @dev Negative rebase: burn supply by the same ratio as the inflationary token mints.
    function _rebase() private {
        if (!inSwap) {
            uint256 circulatingSupply = getCirculatingSupply();
            uint256 burnAmount = circulatingSupply.mul(rewardYield).div(rewardYieldDenominator);
            int256 supplyDelta = -int256(burnAmount);
            coreRebase(supplyDelta);
        }
    }

    /// @dev For negative supplyDelta: subtract from _totalSupply with floor MIN_SUPPLY.
    function coreRebase(int256 supplyDelta) private returns (uint256) {
        epoch = block.timestamp;
        if (supplyDelta == 0) {
            emit LogRebase(epoch, _totalSupply);
            return _totalSupply;
        }
        if (supplyDelta < 0) {
            uint256 burn = uint256(-supplyDelta);
            uint256 minSupply = MIN_SUPPLY;
            if (_totalSupply <= minSupply) {
                emit LogRebase(epoch, _totalSupply);
                return _totalSupply;
            }
            uint256 maxBurn = _totalSupply.sub(minSupply);
            if (burn > maxBurn) burn = maxBurn;
            _totalSupply = _totalSupply.sub(burn);
        } else {
            _totalSupply = _totalSupply.add(uint256(supplyDelta));
        }
        _gonsPerFragment = TOTAL_GONS.div(_totalSupply);
        emit LogRebase(epoch, _totalSupply);
        return _totalSupply;
    }

    function tickDeflate() internal returns (bool) {
        deltaT = block.timestamp - inception;
        totalRewards = deltaT / rebaseFrequency;
        if (deflateCounter <= totalRewards) {
            deflateCounter = deflateCounter + 1;
            return true;
        }
        return false;
    }

    function transfer(address to, uint256 value) external override validRecipient(to) returns (bool) {
        _transferFrom(msg.sender, to, value);
        return true;
    }

    function _basicTransfer(address from, address to, uint256 amount) internal returns (bool) {
        uint256 gonAmount = amount.mul(_gonsPerFragment);
        _gonBalances[from] = _gonBalances[from].sub(gonAmount);
        _gonBalances[to] = _gonBalances[to].add(gonAmount);
        emit Transfer(from, to, amount);
        return true;
    }

    function _transferFrom(address sender, address recipient, uint256 amount) internal returns (bool) {
        bool excludedAccount = _isFeeExempt[sender] || _isFeeExempt[recipient];
        require(initialDistributionFinished || excludedAccount, "LAUNCH INITIATED");
        if (automatedMarketMakerPairs[recipient] && !excludedAccount) {
            require(amount <= maxSellTransactionAmount, "MAX SELL EXCEED");
        }
        if (automatedMarketMakerPairs[sender] && !excludedAccount) {
            require(amount <= maxBuyTransactionAmount, "MAX BUY EXCEEDED");
        }
        if (tickDeflate() && autoRebase && shouldDeflate()) {
            _rebase();
            if (!automatedMarketMakerPairs[sender] && !automatedMarketMakerPairs[recipient]) {
                manualSync();
            }
        }
        if (inSwap) return _basicTransfer(sender, recipient, amount);
        uint256 gonAmount = amount.mul(_gonsPerFragment);
        if (shouldSwapBack() && recipient != DEAD) swapBack();
        _gonBalances[sender] = _gonBalances[sender].sub(gonAmount);
        uint256 gonAmountReceived = shouldTakeFee(sender, recipient) ? takeFee(sender, recipient, gonAmount) : gonAmount;
        _gonBalances[recipient] = _gonBalances[recipient].add(gonAmountReceived);
        emit Transfer(sender, recipient, gonAmountReceived.div(_gonsPerFragment));
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external override validRecipient(to) returns (bool) {
        if (_allowedFragments[from][msg.sender] != uint256(-1)) {
            _allowedFragments[from][msg.sender] = _allowedFragments[from][msg.sender].sub(value, "INSUFFICIENT ALLOWANCE");
        }
        _transferFrom(from, to, value);
        return true;
    }

    function _swapAndLiquify(uint256 contractTokenBalance) private {
        uint256 half = contractTokenBalance.div(2);
        uint256 otherHalf = contractTokenBalance.sub(half);
        if (isLiquidityInBnb) {
            uint256 initialBalance = address(this).balance;
            _swapTokensForBNB(half, address(this));
            uint256 newBalance = address(this).balance.sub(initialBalance);
            _addLiquidity(otherHalf, newBalance);
            emit SwapAndLiquify(half, newBalance, otherHalf);
        } else {
            uint256 initialBalance = IERC20Deflate(busdToken).balanceOf(address(this));
            _swapTokensForBusd(half, address(this));
            uint256 newBalance = IERC20Deflate(busdToken).balanceOf(address(this)).sub(initialBalance);
            _addLiquidityBusd(otherHalf, newBalance);
            emit SwapAndLiquifyBusd(half, newBalance, otherHalf);
        }
    }

    function _addLiquidity(uint256 tokenAmount, uint256 bnbAmount) private {
        router.addLiquidityETH{value: bnbAmount}(address(this), tokenAmount, 0, 0, liquidityReceiver, block.timestamp);
    }

    function _addLiquidityBusd(uint256 tokenAmount, uint256 busdAmount) private {
        router.addLiquidity(address(this), busdToken, tokenAmount, busdAmount, 0, 0, liquidityReceiver, block.timestamp);
    }

    function _swapTokensForBNB(uint256 tokenAmount, address receiver) private {
        address[] memory path = new address[](2);
        path[0] = address(this);
        path[1] = router.WETH();
        router.swapExactTokensForETHSupportingFeeOnTransferTokens(tokenAmount, 0, path, receiver, block.timestamp);
    }

    function _swapTokensForBusd(uint256 tokenAmount, address receiver) private {
        address[] memory path = new address[](3);
        path[0] = address(this);
        path[1] = router.WETH();
        path[2] = busdToken;
        router.swapExactTokensForTokensSupportingFeeOnTransferTokens(tokenAmount, 0, path, receiver, block.timestamp);
    }

    function swapBack() internal swapping {
        uint256 realTotalFee = totalBuyFee.add(totalSellFee);
        uint256 dynamicLiquidityFee = isOverLiquified(targetLiquidity, targetLiquidityDenominator) ? 0 : liquidityFee;
        uint256 contractTokenBalance = _gonBalances[address(this)].div(_gonsPerFragment);
        uint256 amountToLiquify = contractTokenBalance.mul(dynamicLiquidityFee.mul(2)).div(realTotalFee);
        uint256 amountToRFV = contractTokenBalance.mul(buyFeeRFV.mul(2).add(sellFeeRFVAdded)).div(realTotalFee);
        uint256 amountToTreasury = contractTokenBalance.sub(amountToLiquify).sub(amountToRFV);
        if (amountToLiquify > 0) _swapAndLiquify(amountToLiquify);
        if (amountToRFV > 0) _swapTokensForBusd(amountToRFV, riskFreeValueReceiver);
        if (amountToTreasury > 0) _swapTokensForBNB(amountToTreasury, treasuryReceiver);
        emit SwapBack(contractTokenBalance, amountToLiquify, amountToRFV, amountToTreasury);
    }

    function takeFee(address sender, address recipient, uint256 gonAmount) internal returns (uint256) {
        uint256 _realFee = totalBuyFee;
        if (automatedMarketMakerPairs[recipient]) _realFee = totalSellFee;
        uint256 feeAmount = gonAmount.mul(_realFee).div(feeDenominator);
        _gonBalances[address(this)] = _gonBalances[address(this)].add(feeAmount);
        _transferFrom(address(this), address(0x000000000000000000000000000000000000dEaD), (gonAmount.div(_gonsPerFragment)).mul(burnFee).div(1000));
        emit Transfer(sender, address(this), feeAmount.div(_gonsPerFragment));
        return gonAmount.sub(feeAmount);
    }

    function decreaseAllowance(address spender, uint256 subtractedValue) external returns (bool) {
        uint256 oldValue = _allowedFragments[msg.sender][spender];
        if (subtractedValue >= oldValue) {
            _allowedFragments[msg.sender][spender] = 0;
        } else {
            _allowedFragments[msg.sender][spender] = oldValue.sub(subtractedValue);
        }
        emit Approval(msg.sender, spender, _allowedFragments[msg.sender][spender]);
        return true;
    }

    function increaseAllowance(address spender, uint256 addedValue) external returns (bool) {
        _allowedFragments[msg.sender][spender] = _allowedFragments[msg.sender][spender].add(addedValue);
        emit Approval(msg.sender, spender, _allowedFragments[msg.sender][spender]);
        return true;
    }

    function approve(address spender, uint256 value) external override returns (bool) {
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

    function setInitialDistributionFinished(bool _value) external onlyOwner {
        require(initialDistributionFinished != _value, "unchanged");
        initialDistributionFinished = _value;
    }

    function setFeeExempt(address _addr, bool _value) external onlyOwner {
        require(_isFeeExempt[_addr] != _value, "unchanged");
        _isFeeExempt[_addr] = _value;
    }

    function setTargetLiquidity(uint256 target, uint256 accuracy) external onlyOwner {
        targetLiquidity = target;
        targetLiquidityDenominator = accuracy;
    }

    function setSwapBackSettings(bool _enabled, uint256 _num, uint256 _denom) external onlyOwner {
        swapEnabled = _enabled;
        gonSwapThreshold = TOTAL_GONS.div(_denom).mul(_num);
    }

    function setFeeReceivers(address _liquidityReceiver, address _treasuryReceiver, address _riskFreeValueReceiver) external onlyOwner {
        liquidityReceiver = _liquidityReceiver;
        treasuryReceiver = _treasuryReceiver;
        riskFreeValueReceiver = _riskFreeValueReceiver;
    }

    function clearStuckBalance(address _receiver) external onlyOwner {
        uint256 balance = address(this).balance;
        payable(_receiver).transfer(balance);
    }

    function rescueToken(address tokenAddress, uint256 tokens) external onlyOwner returns (bool success) {
        return ERC20DetailedDeflate(tokenAddress).transfer(msg.sender, tokens);
    }

    function setAutoRebase(bool _autoRebase) external onlyOwner {
        require(autoRebase != _autoRebase, "unchanged");
        autoRebase = _autoRebase;
    }

    function setRebaseFrequency(uint256 _rebaseFrequency) external onlyOwner {
        require(_rebaseFrequency <= MAX_REBASE_FREQUENCY, "MAXIMUM EXCEEDED");
        rebaseFrequency = _rebaseFrequency;
    }

    function setRewardYield(uint256 _rewardYield, uint256 _rewardYieldDenominator) external onlyOwner {
        rewardYield = _rewardYield;
        rewardYieldDenominator = _rewardYieldDenominator;
    }

    function setFeesOnNormalTransfers(bool _enabled) external onlyOwner {
        require(feesOnNormalTransfers != _enabled, "unchanged");
        feesOnNormalTransfers = _enabled;
    }

    function setIsLiquidityInBnb(bool _value) external onlyOwner {
        require(isLiquidityInBnb != _value, "unchanged");
        isLiquidityInBnb = _value;
    }

    function setMaxSellTransaction(uint256 _maxTxn) external onlyOwner { maxSellTransactionAmount = _maxTxn; }
    function setMaxBuyTransaction(uint256 _maxTxn) external onlyOwner { maxBuyTransactionAmount = _maxTxn; }

    function setFees(uint256 _liquidityFee, uint256 _treasuryFee, uint256 _burnFee, uint256 _buyFeeRFV, uint256 _sellFeeRFVAdded, uint256 _sellFeeTreasuryAdded, uint256 _feeDenominator) external onlyOwner {
        liquidityFee = _liquidityFee;
        treasuryFee = _treasuryFee;
        burnFee = _burnFee;
        buyFeeRFV = _buyFeeRFV;
        sellFeeRFVAdded = _sellFeeRFVAdded;
        sellFeeTreasuryAdded = _sellFeeTreasuryAdded;
        feeDenominator = _feeDenominator;
        totalBuyFee = liquidityFee.add(treasuryFee).add(buyFeeRFV).add(burnFee);
        totalSellFee = totalBuyFee.add(sellFeeTreasuryAdded).add(sellFeeRFVAdded);
    }

    function updateRouter(address _address) external onlyOwner {
        require(address(router) != _address, "Router address already set");
        router = IDEXRouterDeflate(_address);
    }

    event SwapBack(uint256 contractTokenBalance, uint256 amountToLiquify, uint256 amountToRFV, uint256 amountToTreasury);
    event SwapAndLiquify(uint256 tokensSwapped, uint256 bnbReceived, uint256 tokensIntoLiqudity);
    event SwapAndLiquifyBusd(uint256 tokensSwapped, uint256 busdReceived, uint256 tokensIntoLiqudity);
    event LogRebase(uint256 indexed epoch, uint256 totalSupply);
    event SetAutomatedMarketMakerPair(address indexed pair, bool indexed value);
}
