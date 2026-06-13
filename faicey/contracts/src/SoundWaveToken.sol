// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * SoundWave — SND / WAV
 *
 * A capped ERC-20 carrying forensic-grade voiceprints. The supply is high and
 * realistic but NOT infinite: one quadrillion whole tokens (1e15 × 1e18 base units),
 * leaving immense headroom for per-voiceprint uniqueness while remaining a finite,
 * auditable cap (the old build used type(uint256).max — replaced here).
 *
 * Voiceprints are registered with 18 decimals of precision across six independent
 * acoustic measures (the SCIENTIFIC forensic measure: dominant frequency, amplitude,
 * spectral centroid, spectral rolloff, zero-crossing rate, harmonic-to-noise ratio),
 * each a fixed-point integer = real_value × 1e18. The on-chain record is therefore a
 * reproducible forensic measurement, not an opaque hash.
 *
 * © Professor Codephreak — rage.pythai.net
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

interface IERC20Metadata is IERC20 {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
}

contract SoundWaveToken is IERC20, IERC20Metadata {
    // ─────────────────────────── token identity ───────────────────────────
    string public constant name = "SND";
    string public constant symbol = "WAV";
    uint8 public constant decimals = 18;

    /// 18-decimal fixed-point scale: a real value v is stored as v × ONE.
    uint256 public constant ONE = 1e18;

    /// Capped supply: one quadrillion (1e15) whole tokens, each with 18 decimals.
    /// High and realistic, finite, far below type(uint256).max.
    uint256 public constant MAX_SUPPLY = 1_000_000_000_000_000 * ONE; // 1e33 base units

    /// Genesis mint to the deployer/treasury: one billion whole tokens.
    uint256 public constant INITIAL_SUPPLY = 1_000_000_000 * ONE;

    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    address public owner;

    // ─────────────────────────── forensic voiceprint ──────────────────────
    /// A forensic voiceprint. Each acoustic field is real_value × 1e18.
    struct VoicePrint {
        bytes32 hash;                 // sha256 of the canonical measurement payload
        uint64 timestamp;             // block time of registration
        uint64 sampleRate;            // Hz (integer)
        uint256 dominantFrequency;    // Hz × 1e18
        uint256 amplitude;            // 0..1 × 1e18 (RMS)
        uint256 spectralCentroid;     // Hz × 1e18
        uint256 spectralRolloff;      // Hz × 1e18
        uint256 zeroCrossingRate;     // 0..1 × 1e18
        uint256 harmonicNoiseRatio;   // × 1e18
        uint256 precisionScore;       // composite confidence, 0..1 × 1e18
        bool registered;
    }

    mapping(address => VoicePrint) public voicePrints;
    mapping(bytes32 => address) public voicePrintOwnerOf; // hash → first registrant (uniqueness)
    uint256 public voicePrintCount;

    /// Reward ceiling per registration: 1000 whole tokens, scaled by precisionScore.
    uint256 public constant MAX_VOICE_REWARD = 1000 * ONE;
    bool public voiceAnalysisEnabled = true;

    // ─────────────────────────── events ───────────────────────────────────
    event VoicePrintRegistered(address indexed account, bytes32 indexed hash, uint256 precisionScore, uint256 reward);
    event Minted(address indexed to, uint256 amount);
    event OwnershipTransferred(address indexed from, address indexed to);
    event VoiceAnalysisToggled(bool enabled);

    modifier onlyOwner() {
        require(msg.sender == owner, "WAV: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    // ─────────────────────────── ERC-20 ───────────────────────────────────
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function allowance(address owner_, address spender) external view override returns (uint256) {
        return _allowances[owner_][spender];
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        uint256 allowed = _allowances[from][msg.sender];
        if (allowed != type(uint256).max) {
            require(allowed >= amount, "WAV: insufficient allowance");
            _approve(from, msg.sender, allowed - amount);
        }
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0) && to != address(0), "WAV: zero address");
        uint256 bal = _balances[from];
        require(bal >= amount, "WAV: insufficient balance");
        unchecked {
            _balances[from] = bal - amount;
            _balances[to] += amount;
        }
        emit Transfer(from, to, amount);
    }

    function _approve(address owner_, address spender, uint256 amount) internal {
        require(owner_ != address(0) && spender != address(0), "WAV: zero address");
        _allowances[owner_][spender] = amount;
        emit Approval(owner_, spender, amount);
    }

    function _mint(address to, uint256 amount) internal {
        require(to != address(0), "WAV: zero address");
        require(_totalSupply + amount <= MAX_SUPPLY, "WAV: exceeds MAX_SUPPLY");
        unchecked {
            _totalSupply += amount;
            _balances[to] += amount;
        }
        emit Transfer(address(0), to, amount);
        emit Minted(to, amount);
    }

    // ─────────────────────────── minting (capped) ─────────────────────────
    /// Owner mint, strictly bounded by MAX_SUPPLY.
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    /// Remaining mintable headroom under the cap.
    function mintable() external view returns (uint256) {
        return MAX_SUPPLY - _totalSupply;
    }

    // ─────────────────────────── voiceprint API ───────────────────────────
    /**
     * Register a forensic voiceprint (18-decimal fixed point) and receive a
     * precision-weighted WAV reward (capped at MAX_VOICE_REWARD, never past MAX_SUPPLY).
     * @param hash sha256 of the canonical measurement payload (off-chain reproducible)
     * @param sampleRate integer Hz
     * @param m six acoustic measures, each real_value × 1e18, in the struct's field order:
     *          [dominantFrequency, amplitude, spectralCentroid, spectralRolloff,
     *           zeroCrossingRate, harmonicNoiseRatio]
     * @param precisionScore composite confidence in [0, 1e18]
     */
    function registerVoicePrint(
        bytes32 hash,
        uint64 sampleRate,
        uint256[6] calldata m,
        uint256 precisionScore
    ) external returns (uint256 reward) {
        require(voiceAnalysisEnabled, "WAV: voice analysis disabled");
        require(hash != bytes32(0), "WAV: empty hash");
        require(precisionScore <= ONE, "WAV: precision > 1.0");
        require(voicePrintOwnerOf[hash] == address(0), "WAV: voiceprint already registered");

        voicePrints[msg.sender] = VoicePrint({
            hash: hash,
            timestamp: uint64(block.timestamp),
            sampleRate: sampleRate,
            dominantFrequency: m[0],
            amplitude: m[1],
            spectralCentroid: m[2],
            spectralRolloff: m[3],
            zeroCrossingRate: m[4],
            harmonicNoiseRatio: m[5],
            precisionScore: precisionScore,
            registered: true
        });
        voicePrintOwnerOf[hash] = msg.sender;
        voicePrintCount += 1;

        // reward = MAX_VOICE_REWARD × precisionScore, both 18-dec → divide by ONE
        reward = (MAX_VOICE_REWARD * precisionScore) / ONE;
        if (reward > 0 && _totalSupply + reward <= MAX_SUPPLY) {
            _mint(msg.sender, reward);
        } else {
            reward = 0;
        }

        emit VoicePrintRegistered(msg.sender, hash, precisionScore, reward);
    }

    function getVoicePrint(address account) external view returns (VoicePrint memory) {
        return voicePrints[account];
    }

    // ─────────────────────────── admin ────────────────────────────────────
    function setVoiceAnalysisEnabled(bool enabled) external onlyOwner {
        voiceAnalysisEnabled = enabled;
        emit VoiceAnalysisToggled(enabled);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "WAV: zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ─────────────────────────── supply facts (UI helper) ─────────────────
    function supplyInfo()
        external
        view
        returns (uint256 cap, uint256 minted, uint256 remaining, uint8 dec)
    {
        return (MAX_SUPPLY, _totalSupply, MAX_SUPPLY - _totalSupply, decimals);
    }
}
