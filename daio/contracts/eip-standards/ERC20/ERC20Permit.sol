// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ERC20Permit
 * @notice ERC20 token with ERC2612 permit functionality for gasless approvals
 * @dev Focused implementation of permit functionality with examples
 */
contract ERC20PermitToken is ERC20, ERC20Permit, Ownable {

    // Events for permit usage tracking
    event PermitUsed(
        address indexed owner,
        address indexed spender,
        uint256 value,
        uint256 deadline,
        uint256 nonce
    );

    /**
     * @notice Initialize ERC20 with Permit functionality
     * @param name Token name
     * @param symbol Token symbol
     * @param initialSupply Initial token supply
     * @param owner Token owner
     */
    constructor(
        string memory name,
        string memory symbol,
        uint256 initialSupply,
        address owner
    ) ERC20(name, symbol) ERC20Permit(name) Ownable(owner) {
        if (initialSupply > 0) {
            _mint(owner, initialSupply);
        }
    }

    /**
     * @notice Mint tokens (only owner)
     * @param to Address to mint to
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    /**
     * @notice Permit with event emission for tracking
     * @param owner Token owner granting permission
     * @param spender Address receiving permission
     * @param value Amount of allowance
     * @param deadline Permit expiration time
     * @param v Recovery byte of signature
     * @param r Half of signature
     * @param s Half of signature
     */
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public override {
        super.permit(owner, spender, value, deadline, v, r, s);

        emit PermitUsed(owner, spender, value, deadline, nonces(owner) - 1);
    }

    /**
     * @notice Get current nonce for address (for permit signatures)
     * @param owner Address to get nonce for
     * @return Current nonce
     */
    function getCurrentNonce(address owner) external view returns (uint256) {
        return nonces(owner);
    }

    /**
     * @notice Get domain separator for permit signatures
     * @return Domain separator hash
     */
    function getDomainSeparator() external view returns (bytes32) {
        return DOMAIN_SEPARATOR();
    }

    /**
     * @notice Helper function to create permit signature hash
     * @param owner Token owner
     * @param spender Spender address
     * @param value Allowance amount
     * @param deadline Permit deadline
     * @param nonce Current nonce
     * @return Hash to be signed
     */
    function getPermitHash(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint256 nonce
    ) external view returns (bytes32) {
        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
                owner,
                spender,
                value,
                nonce,
                deadline
            )
        );

        return keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR(), structHash));
    }

    /**
     * @notice Verify permit signature without executing
     * @param owner Token owner
     * @param spender Spender address
     * @param value Allowance amount
     * @param deadline Permit deadline
     * @param v Recovery byte
     * @param r Signature half
     * @param s Signature half
     * @return Whether signature is valid
     */
    function verifyPermit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external view returns (bool) {
        if (deadline < block.timestamp) {
            return false;
        }

        bytes32 structHash = keccak256(
            abi.encode(
                keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
                owner,
                spender,
                value,
                nonces(owner),
                deadline
            )
        );

        bytes32 hash = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR(), structHash));
        address signer = ecrecover(hash, v, r, s);

        return signer == owner && signer != address(0);
    }

    /**
     * @notice Batch permit multiple approvals in one transaction
     * @param owners Array of token owners
     * @param spenders Array of spender addresses
     * @param values Array of allowance amounts
     * @param deadlines Array of permit deadlines
     * @param vs Array of recovery bytes
     * @param rs Array of signature halves
     * @param ss Array of signature halves
     */
    function batchPermit(
        address[] calldata owners,
        address[] calldata spenders,
        uint256[] calldata values,
        uint256[] calldata deadlines,
        uint8[] calldata vs,
        bytes32[] calldata rs,
        bytes32[] calldata ss
    ) external {
        require(owners.length == spenders.length, "Array length mismatch");
        require(owners.length == values.length, "Array length mismatch");
        require(owners.length == deadlines.length, "Array length mismatch");
        require(owners.length == vs.length, "Array length mismatch");
        require(owners.length == rs.length, "Array length mismatch");
        require(owners.length == ss.length, "Array length mismatch");

        for (uint256 i = 0; i < owners.length; i++) {
            permit(owners[i], spenders[i], values[i], deadlines[i], vs[i], rs[i], ss[i]);
        }
    }
}