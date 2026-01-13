// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title FractionalNFT
 * @notice Fractionalizes ERC721 NFTs into ERC20 tokens for governance
 * @dev Allows multiple holders to own fractions of an NFT for voting
 */
contract FractionalNFT is ERC20, Ownable {
    address public immutable nftAddress;
    uint256 public immutable nftId;
    uint256 public immutable totalFractions;
    bool public redeemed;

    event NFTFractionalized(
        address indexed nftAddress,
        uint256 indexed nftId,
        uint256 totalFractions
    );
    event NFTRedeemed(address indexed redeemer, uint256 indexed nftId);

    constructor(
        address _nftAddress,
        uint256 _nftId,
        uint256 _totalFractions,
        address _initialOwner
    ) ERC20("FractionalNFT", "F-NFT") Ownable(_initialOwner) {
        require(_nftAddress != address(0), "Invalid NFT address");
        require(_totalFractions > 0, "Invalid fraction count");
        
        nftAddress = _nftAddress;
        nftId = _nftId;
        totalFractions = _totalFractions;

        // Mint all fractions to contract creator
        _mint(_initialOwner, _totalFractions * 10**decimals());

        emit NFTFractionalized(_nftAddress, _nftId, _totalFractions);
    }

    /**
     * @notice Redeem all fractions to claim the full NFT
     * @dev Requires holding all fractions
     */
    function redeemNFT() external {
        require(!redeemed, "NFT already redeemed");
        require(
            balanceOf(msg.sender) == totalSupply(),
            "Need all fractions to redeem"
        );

        redeemed = true;

        // Transfer NFT to redeemer
        IERC721(nftAddress).transferFrom(address(this), msg.sender, nftId);

        emit NFTRedeemed(msg.sender, nftId);
    }

    /**
     * @notice Get fraction ownership percentage
     * @param holder Holder address
     * @return percentage Ownership percentage (basis points)
     */
    function getOwnershipPercentage(address holder) external view returns (uint256) {
        if (totalSupply() == 0) return 0;
        return (balanceOf(holder) * 10000) / totalSupply();
    }
}
