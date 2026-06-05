// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IDebtOracle } from "../interfaces/IDebtOracle.sol";

/// @dev Minimal subset of the Pyth `IPyth` interface needed here.
interface IPyth {
    struct PriceFeed {
        int64  price;
        uint64 conf;
        int32  expo;
        uint64 publishTime;
    }

    function getPriceUnsafe(bytes32 id) external view returns (PriceFeed memory);
    function getPriceNoOlderThan(bytes32 id, uint256 age) external view returns (PriceFeed memory);
    function updatePriceFeeds(bytes[] calldata updateData) external payable;
    function getUpdateFee(bytes[] calldata updateData) external view returns (uint256);
}

/// @title PythAdapter
/// @notice Pyth pull-oracle adapter. The contract supports both `view`
///         reads (no on-chain update) and `push` reads that call
///         `updatePriceFeeds` first using caller-supplied update blobs.
contract PythAdapter {
    IPyth   public immutable pyth;
    bytes32 public immutable priceId;
    bytes32 public immutable sourceId;
    uint256 public immutable maxAge;

    error StaleFeed();
    error InvalidPrice();
    error NotEnoughFee(uint256 required, uint256 provided);

    constructor(address pyth_, bytes32 priceId_, bytes32 sourceId_, uint256 maxAge_) {
        pyth = IPyth(pyth_);
        priceId = priceId_;
        sourceId = sourceId_;
        maxAge = maxAge_;
    }

    function latest() external view returns (IDebtOracle.Observation memory obs) {
        IPyth.PriceFeed memory pf = pyth.getPriceNoOlderThan(priceId, maxAge);
        obs = _toObservation(pf);
    }

    /// @notice Optional push-then-read flow; forward Pyth update data from off-chain.
    function pushAndRead(bytes[] calldata updateData)
        external
        payable
        returns (IDebtOracle.Observation memory obs)
    {
        uint256 fee = pyth.getUpdateFee(updateData);
        if (msg.value < fee) revert NotEnoughFee(fee, msg.value);
        pyth.updatePriceFeeds{ value: fee }(updateData);

        IPyth.PriceFeed memory pf = pyth.getPriceUnsafe(priceId);
        if (block.timestamp - pf.publishTime > maxAge) revert StaleFeed();
        obs = _toObservation(pf);

        // Refund any excess.
        if (msg.value > fee) {
            (bool ok,) = msg.sender.call{ value: msg.value - fee }("");
            require(ok, "refund failed");
        }
    }

    function _toObservation(IPyth.PriceFeed memory pf)
        internal
        view
        returns (IDebtOracle.Observation memory obs)
    {
        if (pf.price == 0) revert InvalidPrice();

        // Normalise to 1e18 using the Pyth `expo` (usually negative).
        int256 value;
        if (pf.expo >= 0) {
            value = int256(pf.price) * int256(10 ** uint32(pf.expo));
            value *= int256(1e18);
        } else {
            uint32 absExpo = uint32(-pf.expo);
            if (absExpo > 18) {
                value = int256(pf.price) / int256(10 ** (absExpo - 18));
            } else {
                value = int256(pf.price) * int256(10 ** (18 - absExpo));
            }
        }

        // Confidence ∝ price/conf ratio (1e18 when conf == 0, ~0 when conf >> price).
        uint256 conf;
        if (pf.conf == 0) {
            conf = 1e18;
        } else {
            uint256 ratio = (uint256(uint64(pf.price < 0 ? -pf.price : pf.price)) * 1e18)
                          / (uint256(pf.conf) + uint256(uint64(pf.price < 0 ? -pf.price : pf.price)));
            conf = ratio;
        }

        obs = IDebtOracle.Observation({
            value: value,
            timestamp: pf.publishTime,
            confidence: conf,
            source: sourceId
        });
    }
}
