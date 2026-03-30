// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ERC777Extended.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title ERC777Compatible
 * @notice ERC777 token with full ERC20 backward compatibility
 * @dev Ensures seamless integration with existing ERC20 infrastructure while providing ERC777 benefits
 */
contract ERC777Compatible is ERC777Extended, IERC20 {

    // ERC20 events (ERC777 already includes these, but explicit for clarity)
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    // ERC20 compatibility tracking
    mapping(address => mapping(address => uint256)) private _allowances;

    // Configuration for ERC20 compatibility
    bool public erc20CompatibilityEnabled = true;

    /**
     * @notice Initialize ERC777 with ERC20 compatibility
     * @param name Token name
     * @param symbol Token symbol
     * @param defaultOperators Default operators
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        address[] memory defaultOperators,
        address admin
    ) ERC777Extended(name, symbol, defaultOperators, admin) {
        // ERC777 constructor handles everything
    }

    /**
     * @notice Enable or disable ERC20 compatibility
     * @param enabled Whether ERC20 compatibility is enabled
     */
    function setERC20Compatibility(bool enabled) external onlyRole(DEFAULT_ADMIN_ROLE) {
        erc20CompatibilityEnabled = enabled;
    }

    // ERC20 Interface Implementation

    /**
     * @notice Get total token supply (ERC20)
     * @return Total supply
     */
    function totalSupply() public view override returns (uint256) {
        return super.totalSupply();
    }

    /**
     * @notice Get account balance (ERC20)
     * @param account Account address
     * @return Account balance
     */
    function balanceOf(address account) public view override(ERC777, IERC20) returns (uint256) {
        return super.balanceOf(account);
    }

    /**
     * @notice Transfer tokens (ERC20)
     * @param to Recipient address
     * @param amount Amount to transfer
     * @return Success
     */
    function transfer(address to, uint256 amount) public override returns (bool) {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");

        // Use ERC777 send with empty data
        send(to, amount, "");
        return true;
    }

    /**
     * @notice Get allowance (ERC20)
     * @param owner Token owner
     * @param spender Spender address
     * @return Allowance amount
     */
    function allowance(address owner, address spender) public view override returns (uint256) {
        return _allowances[owner][spender];
    }

    /**
     * @notice Approve spender (ERC20)
     * @param spender Spender address
     * @param amount Amount to approve
     * @return Success
     */
    function approve(address spender, uint256 amount) public override returns (bool) {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");

        _approve(msg.sender, spender, amount);
        return true;
    }

    /**
     * @notice Transfer from allowance (ERC20)
     * @param from Token owner
     * @param to Recipient
     * @param amount Amount to transfer
     * @return Success
     */
    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");

        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= amount, "ERC20: transfer amount exceeds allowance");

        // Use ERC777 operatorSend
        operatorSend(from, to, amount, "", "");

        // Update allowance
        _approve(from, msg.sender, currentAllowance - amount);

        return true;
    }

    /**
     * @notice Increase allowance (ERC20 extension)
     * @param spender Spender address
     * @param addedValue Amount to add to allowance
     * @return Success
     */
    function increaseAllowance(address spender, uint256 addedValue) public returns (bool) {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");

        _approve(msg.sender, spender, _allowances[msg.sender][spender] + addedValue);
        return true;
    }

    /**
     * @notice Decrease allowance (ERC20 extension)
     * @param spender Spender address
     * @param subtractedValue Amount to subtract from allowance
     * @return Success
     */
    function decreaseAllowance(address spender, uint256 subtractedValue) public returns (bool) {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");

        uint256 currentAllowance = _allowances[msg.sender][spender];
        require(currentAllowance >= subtractedValue, "ERC20: decreased allowance below zero");

        _approve(msg.sender, spender, currentAllowance - subtractedValue);
        return true;
    }

    /**
     * @notice Mint tokens with ERC20 event emission
     * @param to Address to mint to
     * @param amount Amount to mint
     * @param userData Additional user data
     * @param operatorData Additional operator data
     */
    function mint(
        address to,
        uint256 amount,
        bytes memory userData,
        bytes memory operatorData
    ) public override {
        super.mint(to, amount, userData, operatorData);

        // Emit ERC20 Transfer event for compatibility
        if (erc20CompatibilityEnabled) {
            emit Transfer(address(0), to, amount);
        }
    }

    /**
     * @notice ERC20-style mint (simplified)
     * @param to Address to mint to
     * @param amount Amount to mint
     */
    function mintERC20(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        mint(to, amount, "", "");
    }

    /**
     * @notice ERC20-style burn (simplified)
     * @param from Address to burn from
     * @param amount Amount to burn
     */
    function burnERC20(address from, uint256 amount) external onlyRole(BURNER_ROLE) {
        burnFrom(from, amount, "", "");
    }

    /**
     * @notice Internal approve function
     * @param owner Token owner
     * @param spender Spender address
     * @param amount Allowance amount
     */
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");

        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }

    /**
     * @notice Override send to emit ERC20 Transfer event
     * @param recipient Recipient address
     * @param amount Amount to send
     * @param data Additional data
     */
    function send(
        address recipient,
        uint256 amount,
        bytes memory data
    ) public override {
        super.send(recipient, amount, data);

        // Emit ERC20 Transfer event for compatibility
        if (erc20CompatibilityEnabled) {
            emit Transfer(msg.sender, recipient, amount);
        }
    }

    /**
     * @notice Override operatorSend to emit ERC20 Transfer event
     * @param sender Sender address
     * @param recipient Recipient address
     * @param amount Amount to send
     * @param data Additional data
     * @param operatorData Operator data
     */
    function operatorSend(
        address sender,
        address recipient,
        uint256 amount,
        bytes memory data,
        bytes memory operatorData
    ) public override {
        super.operatorSend(sender, recipient, amount, data, operatorData);

        // Emit ERC20 Transfer event for compatibility
        if (erc20CompatibilityEnabled) {
            emit Transfer(sender, recipient, amount);
        }
    }

    /**
     * @notice Override burnFrom to emit ERC20 Transfer event
     * @param account Address to burn from
     * @param amount Amount to burn
     * @param userData Additional user data
     * @param operatorData Additional operator data
     */
    function burnFrom(
        address account,
        uint256 amount,
        bytes memory userData,
        bytes memory operatorData
    ) public override {
        super.burnFrom(account, amount, userData, operatorData);

        // Emit ERC20 Transfer event for compatibility
        if (erc20CompatibilityEnabled) {
            emit Transfer(account, address(0), amount);
        }
    }

    /**
     * @notice Check interface support
     * @param interfaceId Interface identifier
     * @return Whether interface is supported
     */
    function supportsInterface(bytes4 interfaceId) public view override returns (bool) {
        return
            interfaceId == type(IERC20).interfaceId ||
            super.supportsInterface(interfaceId);
    }

    /**
     * @notice Get token decimals (ERC20)
     * @return Number of decimals
     */
    function decimals() public pure returns (uint8) {
        return 18;
    }

    /**
     * @notice Batch approve multiple spenders (gas optimization)
     * @param spenders Array of spender addresses
     * @param amounts Array of amounts to approve
     */
    function batchApprove(
        address[] memory spenders,
        uint256[] memory amounts
    ) external {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");
        require(spenders.length == amounts.length, "Arrays length mismatch");
        require(spenders.length <= 50, "Too many spenders");

        for (uint256 i = 0; i < spenders.length; i++) {
            _approve(msg.sender, spenders[i], amounts[i]);
        }
    }

    /**
     * @notice Permit function for gasless approvals (ERC2612 style)
     * @param owner Token owner
     * @param spender Spender address
     * @param value Amount to approve
     * @param deadline Permit deadline
     * @param v Signature parameter
     * @param r Signature parameter
     * @param s Signature parameter
     */
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(erc20CompatibilityEnabled, "ERC20 compatibility disabled");
        require(block.timestamp <= deadline, "Permit expired");

        // Simple permit implementation (in production, use full ERC2612)
        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
                owner,
                spender,
                value,
                0, // nonce (simplified)
                deadline
            )
        );

        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", _domainSeparator(), structHash)
        );

        address recoveredAddress = ecrecover(digest, v, r, s);
        require(recoveredAddress == owner, "Invalid signature");

        _approve(owner, spender, value);
    }

    function _domainSeparator() internal view returns (bytes32) {
        return keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes(name())),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }
}